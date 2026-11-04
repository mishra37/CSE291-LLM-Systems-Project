"""Adapt fixed definitions without putting evaluator metadata into model prompts."""
import json
from pathlib import Path

from evaluation.score_qa import score as score_qa
from workloads.multistep import validate_multistep


def load_tasks(path, arrival="batch", rate=1.0, tool_delay=None, limit=None):
    path = Path(path)
    files = ([path / name for name in ("short_qa.jsonl", "long_context.jsonl",
              "long_generation.jsonl", "multistep.jsonl")] if path.is_dir() else [path])
    records = [json.loads(line) for file in files for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit is not None:
        records = records[:limit]
    if not records or len({t['task_id'] for t in records}) != len(records):
        raise ValueError("Workload must contain tasks with unique IDs")
    tasks = []
    for i, record in enumerate(records):
        if "execution" not in record:
            tasks.append(record)  # Existing synthetic format retains its schedule.
            continue
        kind = record['type']
        generation = record['generation']
        steps = []
        if kind == 'multistep':
            validate_multistep(record)
            for j, step in enumerate(record['model_steps']):
                item = {'user': record['initial_prompt'] + '\n\n' + step['instruction'] if j == 0 else step['instruction'],
                        'tool_delay_s': 0, 'max_tokens': step.get('max_tokens', generation['max_tokens'])}
                if j:
                    item['tool_before'] = record['model_steps'][j-1]['tool_after']
                    item['tool_delay_s'] = (record['experiment_defaults']['tool_delay_s'] if tool_delay is None else tool_delay)
                steps.append(item)
        else:
            if kind in ('short_qa', 'long_context'):
                label = 'Passage' if kind == 'short_qa' else 'Document'
                user = f"{label}:\n{record['context']}\n\nQuestion: {record['question']}\nAnswer:"
            elif kind == 'long_gen':
                user = record['prompt']
            else:
                raise ValueError(f'Unsupported fixed task type: {kind}')
            steps = [{'user': user, 'max_tokens': generation['max_tokens'], 'tool_delay_s': 0}]
        tasks.append({'task_id': record['task_id'], 'type': kind, 'system': record['system'],
                      'arrival_s': 0 if arrival == 'batch' else i / rate,
                      'prefix_group': 'fixed', 'steps': steps, 'generation': generation,
                      'fixtures': record.get('tool_fixtures', {}),
                      'est_peak_context': record.get('length', {}).get('peak_budget_tokens',
                          record.get('length', {}).get('prompt_tokens')), 'canonical': True})
    return tasks, records


def typed_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(typed_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(typed_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def evaluate(records, predictions):
    """Offline scoring, after the timed replay. Writing semantics remain pending."""
    predictions = {p['task_id']: p for p in predictions}
    rows = []
    for task in records:
        if 'execution' not in task:
            continue
        p = predictions[task['task_id']]
        complete = (p['status'] == 'ok' and p['response_complete'] and not p['truncated']
                    and p['steps_done'] == task['execution']['model_calls'] and bool(p['text'].strip()))
        row = {'task_id': task['task_id'], 'type': task['type'], 'completed': complete, 'correct': False}
        if task['type'] in ('short_qa', 'long_context'):
            scored, _ = score_qa([task], [p])
            row.update(correct=bool(scored[0]['correct']), token_f1=scored[0]['token_f1'])
        elif task['type'] == 'multistep':
            try:
                answer = json.loads(p['text'], object_pairs_hook=strict_object)
                row['correct'] = complete and typed_equal(answer, task['evaluation']['expected'])
            except (ValueError, TypeError):
                pass
        else:
            words = len(p['text'].split())
            bounds = task['evaluation']['word_count']
            row.update(word_count=words, length_ok=bounds['min'] <= words <= bounds['max'],
                       correct=None if complete else False, judgment='pending' if complete else 'execution_failed')
        rows.append(row)
    return rows
