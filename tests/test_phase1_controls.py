import argparse
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.phase1_report import report_run
from scripts.phase1_fifo import plan, run


class Phase1ControlsTests(unittest.TestCase):
    def test_each_policy_and_repeat_has_own_server_run(self):
        planned = plan("comparison", [1, 2, 4], 3, ("fifo_request", "fifo_task"))
        self.assertEqual(len(planned), 18)
        self.assertEqual(len({entry[0] for entry in planned}), 18)
        self.assertEqual(sum(entry[3] == "fifo_task" for entry in planned), 9)

    def test_driver_restarts_before_each_policy_with_same_server_slots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload, model = root / "tasks.jsonl", root / "model.gguf"
            workload.write_text('{}\n')
            model.write_bytes(b"model")
            out = root / "results"
            args = argparse.Namespace(workload=str(workload), prefix="paired", k=[1], repeats=1,
                np=4, ctx=16384, cache_ram=0, arrival="batch", rate=1., tool_delay=None,
                sample_ms=100, port=8080, out_dir=str(out), llama_root=str(root / "llama.cpp"),
                model=str(model), dry_run=False)
            commands = []
            def fake_run(cmd, **kwargs):
                commands.append(cmd)
                if cmd[0] != "bash":
                    (out / cmd[cmd.index("--name") + 1]).mkdir(parents=True)
            with patch("scripts.phase1_fifo.subprocess.run", side_effect=fake_run), \
                 patch("scripts.phase1_fifo.subprocess.check_output", return_value="revision\n"):
                run(args)
            self.assertEqual([cmd[0] == "bash" for cmd in commands], [True, False, True, False])
            runner_commands = [cmd for cmd in commands if cmd[0] != "bash"]
            self.assertTrue(all(cmd[cmd.index("--server-args") + 1] == "-c 16384 -np 4 --cache-ram 0"
                                for cmd in runner_commands))
            self.assertTrue(all("--no-warmup" not in cmd for cmd in runner_commands))
            self.assertEqual(len(list(out.glob("*/deployment.json"))), 2)

    def test_report_preserves_failed_and_unjudged_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "deployment.json").write_text(json.dumps({"repeat": 1, "policy": "fifo_request",
                "k": 2, "np": 4, "ctx": 16384, "cache_ram_mib": 0, "arrival": "batch",
                "workload_sha256": "w", "model_sha256": "m", "llama_commit": "c"}))
            (path / "summary.json").write_text(json.dumps({"makespan_s": 10}))
            for name, data in (("offered_tasks.jsonl", [{"task_id": "a"}, {"task_id": "b"}]),
                               ("predictions.jsonl", [{"task_id": "a", "status": "ok", "response_complete": True, "truncated": False, "steps_done": 1, "text": "story"},
                                                      {"task_id": "b", "status": "timeout", "response_complete": False, "truncated": False, "steps_done": 0, "text": ""}]),
                               ("quality.jsonl", [{"task_id": "a", "correct": None, "completed": True, "length_ok": True},
                                                 {"task_id": "b", "correct": False, "completed": False}])):
                (path / name).write_text("".join(json.dumps(row) + "\n" for row in data))
            def write_csv(name, fields, data):
                with (path / name).open("w", newline="") as sink:
                    writer = csv.DictWriter(sink, fields)
                    writer.writeheader()
                    writer.writerows(data)
            write_csv("tasks.csv", ["task_id", "type", "status", "n_steps", "latency_s", "queue_s", "admit_wait_s", "gen_tokens"],
                      [{"task_id": "a", "type": "long_gen", "status": "ok", "n_steps": 1, "latency_s": 8, "queue_s": 2, "admit_wait_s": 1, "gen_tokens": 100},
                       {"task_id": "b", "type": "short_qa", "status": "timeout", "n_steps": 1, "latency_s": 9, "queue_s": 7, "admit_wait_s": 3, "gen_tokens": 0}])
            write_csv("requests.csv", ["status", "queue_s", "latency_s", "ttft_s", "step", "n_steps", "stop_type", "truncated", "prompt_tokens", "cached_tokens"],
                      [{"status": "ok", "queue_s": 2, "latency_s": 6, "ttft_s": 1, "step": 0, "n_steps": 1, "stop_type": "limit", "truncated": "False", "prompt_tokens": 50, "cached_tokens": 0},
                       {"status": "timeout", "queue_s": 7, "latency_s": 9, "ttft_s": "", "step": 0, "n_steps": 1, "stop_type": "", "truncated": "False", "prompt_tokens": "", "cached_tokens": ""}])
            write_csv("memory.csv", ["gpu_mem_mb", "server_rss_mb"], [{"gpu_mem_mb": 1000, "server_rss_mb": 500}])
            run, by_type = report_run(path)
            self.assertEqual((run["offered"], run["completed"], run["failed_or_incomplete"]), (2, 1, 1))
            self.assertEqual((run["judged"], run["unjudged"], run["length_ok"]), (1, 1, 1))
            self.assertEqual(run["model_request_failures"], 1)
            self.assertEqual(run["output_limit_final"], 1)
            self.assertEqual(len(by_type), 2)

            (path / "quality.jsonl").write_text("")
            synthetic, _ = report_run(path)
            self.assertEqual(synthetic["quality_scope"], "not_applicable")
            self.assertEqual((synthetic["completed"], synthetic["judged"], synthetic["unjudged"]), (1, 0, 2))


if __name__ == "__main__":
    unittest.main()
