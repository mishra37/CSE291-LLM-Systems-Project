import copy
import json
from pathlib import Path
import unittest

from runner.fixed import load_tasks
from workloads.build_v2 import digest
from workloads.multistep import validate_multistep

ROOT = Path(__file__).resolve().parents[1] / "workloads/tasks"


def read(version, name):
    return [json.loads(line) for line in (ROOT / version / name).read_text(encoding="utf-8").splitlines()]


class TaskRevisionTests(unittest.TestCase):
    def test_references_fixtures_and_scoring_preserved(self):
        for filename in ("short_qa.jsonl", "long_context.jsonl", "long_generation.jsonl", "multistep.jsonl"):
            for old, new in zip(read("v1", filename), read("v2", filename)):
                self.assertEqual(new["revision"]["parent_sha256"], digest(old))
                self.assertEqual(new["revision"]["parent_task_id"], old["task_id"])
                self.assertEqual(new["evaluation"], old["evaluation"])
                self.assertEqual(new["execution"], old["execution"])
                self.assertEqual(new["generation"], old["generation"])
                if old["type"] == "multistep":
                    self.assertEqual(new["tool_fixtures"], old["tool_fixtures"])
                    self.assertEqual([s.get("tool_after") for s in new["model_steps"]],
                                     [s.get("tool_after") for s in old["model_steps"]])
                elif old["type"] != "long_gen":
                    for key in ("system", "context", "question"):
                        self.assertEqual(new[key], old[key])

    def test_public_schema_and_budget_validation(self):
        for task in read("v2", "multistep.jsonl"):
            validate_multistep(task)
            self.assertEqual(task["model_steps"][-1]["max_tokens"], 256)
            self.assertLessEqual(task["length"]["peak_budget_tokens"], 4096)
        task = copy.deepcopy(read("v2", "multistep.jsonl")[10])
        task["initial_prompt"] = task["initial_prompt"].replace("- event_chain: array_of_strings", "- event_chain: array_of_objects")
        with self.assertRaises(ValueError):
            validate_multistep(task)
        task = copy.deepcopy(read("v2", "multistep.jsonl")[0])
        task["model_steps"][-1]["max_tokens"] = 1024
        with self.assertRaises(ValueError):
            validate_multistep(task)

    def test_adapter_uses_final_budget_without_exposing_answers(self):
        tasks, records = load_tasks(ROOT / "v2")
        for task, record in zip(tasks, records):
            self.assertNotIn("evaluation", task)
            if record["type"] == "multistep":
                self.assertEqual([s["max_tokens"] for s in task["steps"]],
                                 [128] * (len(task["steps"]) - 1) + [256])
                self.assertNotIn(json.dumps(record["evaluation"]["expected"]), task["steps"][0]["user"])
                self.assertNotIn("fixtures", task["steps"][0])
        self.assertIn("only event ID strings", records[50]["model_steps"][-1]["instruction"])

    def test_writing_length_contract_is_public_and_rubric_unchanged(self):
        for task in read("v2", "long_generation.jsonl"):
            bounds = task["evaluation"]["word_count"]
            self.assertIn(f"{bounds['min']}-{bounds['max']} words TOTAL", task["prompt"])
            self.assertLessEqual(task["length"]["prompt_tokens"], 512)
            self.assertIn("word range", task["system"])
