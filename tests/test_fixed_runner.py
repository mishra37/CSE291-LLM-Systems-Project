import argparse
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aiohttp import web

from runner.fixed import load_tasks, typed_equal
from runner.llama_client import LlamaClient
from runner.run import main


ROOT = Path(__file__).resolve().parents[1]


class FixedRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.payloads = []
        self.mode = 'ok'
        async def props(request):
            return web.json_response({'total_slots': 4})
        async def metrics(request):
            return web.Response(text='')
        async def completion(request):
            payload = await request.json()
            self.payloads.append(payload)
            if self.mode == 'http_error':
                return web.Response(status=400, text='too large')
            messages = [{'content': '' if self.mode == 'empty' else 'test reply'}]
            if self.mode != 'incomplete':
                messages.append({'stop': True, 'truncated': self.mode == 'truncated',
                                 'id_slot': payload['id_slot'], 'stop_type': 'eos',
                                 'timings': {'predicted_n': 2, 'prompt_n': 10, 'cache_n': 0}})
            return web.Response(text=''.join('data: ' + json.dumps(m) + '\n\n' for m in messages),
                                content_type='text/event-stream')
        app = web.Application()
        app.router.add_get('/props', props)
        app.router.add_get('/metrics', metrics)
        app.router.add_post('/completion', completion)
        self.server = web.AppRunner(app)
        await self.server.setup()
        site = web.TCPSite(self.server, '127.0.0.1', 0)
        await site.start()
        self.url = f'http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}'

    async def asyncTearDown(self):
        await self.server.cleanup()

    async def test_all_80_through_both_fifos_over_http(self):
        for policy in ('fifo_request', 'fifo_task'):
            self.payloads.clear()
            with tempfile.TemporaryDirectory() as directory:
                args = argparse.Namespace(workload=str(ROOT / 'workloads/tasks/v1'), arrival='batch',
                    rate=1., tool_delay=0., max_tasks=None, k=4, sample_ms=100,
                    out_dir=directory, name=policy, url=self.url, req_timeout=10,
                    sched=policy, no_warmup=True, server_args='mock server')
                with patch('runner.run.MemorySampler') as sampler, contextlib.redirect_stdout(io.StringIO()):
                    sampler.return_value.rows = []
                    await main(args)
                out = Path(directory) / policy
                read = lambda name: [json.loads(line) for line in (out / name).read_text(encoding='utf-8').splitlines()]
                predictions = read('predictions.jsonl')
                self.assertEqual(len(predictions), 80)
                self.assertTrue(all(p['status'] == 'ok' and p['response_complete'] for p in predictions))
                self.assertEqual(len(self.payloads), 252)
                self.assertEqual(len(read('tools.jsonl')), 172)
                self.assertTrue(all(p['ignore_eos'] is False for p in self.payloads))
                self.assertTrue(all(p['temperature'] == 0 for p in self.payloads))
                self.assertEqual({p['id_slot'] for p in self.payloads}, {-1} if policy == 'fifo_request' else {0, 1, 2, 3})
                responses = read('responses.jsonl')
                sales = [r for r in responses if r['task_id'] == 'multistep-sales-v1-001']
                self.assertNotIn('gross_sales_usd', sales[0]['prompt'])
                self.assertIn('test reply', sales[1]['prompt'])
                self.assertIn('[tool:get_region_sales]', sales[1]['prompt'])
                self.assertNotIn('"region":"South"', sales[1]['prompt'])
                self.assertIn('"region":"East"', sales[-1]['prompt'])
                quality = read('quality.jsonl')
                self.assertEqual(sum(r['correct'] is None for r in quality), 10)
                self.assertFalse(any(r['correct'] for r in quality))

    async def test_failure_detection(self):
        async with LlamaClient(self.url) as client:
            for mode, expected in [('incomplete', 'incomplete'), ('empty', 'empty_output'),
                                   ('truncated', 'truncated'), ('http_error', 'http_400')]:
                self.mode = mode
                result = await client.complete('prompt', 32, ignore_eos=False)
                self.assertEqual(result['status'], expected)

    async def test_v2_final_cap_sent_to_server(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(workload=str(ROOT / 'workloads/tasks/v2/multistep.jsonl'),
                arrival='batch', rate=1., tool_delay=0., max_tasks=1, k=1, sample_ms=100,
                out_dir=directory, name='v2_caps', url=self.url, req_timeout=10,
                sched='fifo_request', no_warmup=True, server_args='mock server')
            with patch('runner.run.MemorySampler') as sampler, contextlib.redirect_stdout(io.StringIO()):
                sampler.return_value.rows = []
                await main(args)
            self.assertEqual([p['n_predict'] for p in self.payloads], [128, 128, 128, 128, 256])
            self.assertTrue(all(p['ignore_eos'] is False for p in self.payloads))

    async def test_exported_v1_keeps_natural_eos_and_legacy_outputs(self):
        from workloads.export_v1 import load_tasks as load_v1, model_steps
        original = load_v1(ROOT / 'workloads/tasks/v1', ['short_qa'])[0]
        record = {'task_id': original['task_id'], 'type': original['type'],
                  'system': original['system'], 'arrival_s': 0, 'prefix_group': 'fixed',
                  'steps': model_steps(original, None), 'est_peak_context': 256}
        with tempfile.TemporaryDirectory() as directory:
            workload = Path(directory) / 'exported.jsonl'
            workload.write_text(json.dumps(record) + '\n')
            args = argparse.Namespace(workload=str(workload), arrival='batch', rate=1.,
                tool_delay=None, max_tasks=None, k=1, sample_ms=100, out_dir=directory,
                name='v1', url=self.url, req_timeout=10, sched='fifo_request',
                no_warmup=True, server_args='mock server')
            with patch('runner.run.MemorySampler') as sampler, contextlib.redirect_stdout(io.StringIO()):
                sampler.return_value.rows = []
                await main(args)
            self.assertFalse(self.payloads[0]['ignore_eos'])
            out = Path(directory) / 'v1'
            self.assertEqual(len((out / 'outputs.jsonl').read_text().splitlines()), 1)
            self.assertIn('ignore_eos', (out / 'requests.csv').read_text().splitlines()[0])

    def test_adapter_and_strict_json_types(self):
        tasks, records = load_tasks(ROOT / 'workloads/tasks/v1', arrival='steady', rate=2, tool_delay=0)
        self.assertEqual(tasks[1]['arrival_s'], .5)
        self.assertNotIn('evaluation', tasks[0])
        self.assertNotIn('source', tasks[0])
        self.assertFalse(typed_equal({'x': True}, {'x': 1}))
        self.assertFalse(typed_equal({'x': 1.0}, {'x': 1}))
        self.assertFalse(typed_equal({'x': 1, 'extra': 0}, {'x': 1}))
        self.assertTrue(typed_equal({'x': [1, 'a']}, {'x': [1, 'a']}))
