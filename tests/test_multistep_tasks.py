import copy
import json
from pathlib import Path
import unittest
from collections import Counter

from workloads.multistep import reference_answer, validate_multistep


class MultistepFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "workloads/tasks/v1/multistep.jsonl"
        cls.tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def test_collection_and_call_count_diversity(self):
        self.assertEqual(len(self.tasks), 20)
        self.assertEqual(len({task["task_id"] for task in self.tasks}), 20)
        for subtype in ("sales_analysis", "log_investigation"):
            subset = [task for task in self.tasks if task["subtype"] == subtype]
            self.assertEqual(Counter(t["execution"]["tool_calls"] for t in subset), {2: 3, 4: 4, 7: 3})
            for task in subset:
                validate_multistep(task)

    def test_sales_ties_negative_values_and_shortfall_rule(self):
        self.assertEqual(reference_answer(self.tasks[0]), {
            "total_net_sales_usd": 540, "largest_region": "South", "largest_region_net_sales_usd": 180})
        self.assertEqual(reference_answer(self.tasks[1]), {
            "total_net_sales_usd": 400, "largest_region": "North", "largest_region_net_sales_usd": 200})
        self.assertEqual(reference_answer(self.tasks[2]), {
            "total_net_sales_usd": -70, "largest_region": "South", "largest_region_net_sales_usd": -20})
        self.assertEqual(reference_answer(self.tasks[3])["total_shortfall_usd"], 80)
        self.assertEqual(reference_answer(self.tasks[3])["regions_below_target"], ["North"])
        self.assertEqual(reference_answer(self.tasks[9]), {
            "total_net_change_usd": -910, "largest_increase_region": "North", "largest_net_increase_usd": -100})

    def test_original_log_chain_and_distractors(self):
        task = copy.deepcopy(self.tasks[10])
        expected = {"origin_component": "database", "origin_error_code": "POOL_EXHAUSTED", "event_chain": ["E-201", "E-202", "D-301"]}
        self.assertEqual(reference_answer(task), expected)
        task["tool_fixtures"]["application"]["events"].reverse()
        task["tool_fixtures"]["database"]["events"].reverse()
        self.assertEqual(reference_answer(task), expected)

    def test_cycle_and_wrong_request_cause_are_rejected(self):
        for mutation in ("cycle", "request"):
            task = copy.deepcopy(self.tasks[10])
            origin = next(e for e in task["tool_fixtures"]["database"]["events"] if e["event_id"] == "D-301")
            if mutation == "cycle":
                origin["cause_event_id"] = "E-201"
            else:
                origin["request_id"] = "different-request"
            with self.assertRaises(ValueError):
                reference_answer(task)

    def test_bad_reference_or_tool_arguments_are_rejected(self):
        task = copy.deepcopy(self.tasks[0])
        task["evaluation"]["expected"]["total_net_sales_usd"] = 999
        with self.assertRaises(ValueError):
            validate_multistep(task)
        task = copy.deepcopy(self.tasks[0])
        task["model_steps"][0]["tool_after"]["arguments"]["region"] = "Unknown"
        with self.assertRaises(ValueError):
            validate_multistep(task)


if __name__ == "__main__":
    unittest.main()
