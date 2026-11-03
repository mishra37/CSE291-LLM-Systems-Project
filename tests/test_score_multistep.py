import json
import unittest
from pathlib import Path

from evaluation import score_multistep

TASK = json.loads((Path(__file__).parents[1] / "workloads/tasks/v1/multistep.jsonl").read_text().splitlines()[0])
EXPECTED = json.dumps(TASK["evaluation"]["expected"])


def prediction(text, **overrides):
    p = {"task_id": TASK["task_id"], "status": "ok", "steps_done": TASK["execution"]["model_calls"],
         "response_complete": True, "truncated": False, "text": text}
    p.update(overrides)
    return p


def first_row(*predictions):
    rows, _ = score_multistep.score([TASK], list(predictions))
    return rows[0]


class ScoreMultistepTest(unittest.TestCase):
    def test_exact_answer_is_correct(self):
        row = first_row(prediction(EXPECTED))
        self.assertEqual((row["correct"], row["field_fraction"]), (1, 1.0))

    def test_key_order_and_whitespace_do_not_matter(self):
        reordered = json.dumps(dict(reversed(list(TASK["evaluation"]["expected"].items()))), indent=2)
        self.assertEqual(first_row(prediction(reordered))["correct"], 1)

    def test_markdown_fence_is_not_stripped(self):
        self.assertEqual(first_row(prediction("```json\n" + EXPECTED + "\n```"))["error"], "not_json")

    def test_extra_field_fails(self):
        self.assertEqual(first_row(prediction(EXPECTED[:-1] + ', "note": "x"}'))["error"], "extra_fields")

    def test_integer_as_string_fails(self):
        answer = {k: str(v) if type(v) is int else v for k, v in TASK["evaluation"]["expected"].items()}
        self.assertEqual(first_row(prediction(json.dumps(answer)))["correct"], 0)

    def test_incomplete_execution_gets_no_credit(self):
        row = first_row(prediction(EXPECTED, steps_done=1))
        self.assertEqual((row["completed"], row["correct"]), (False, 0))

    def test_missing_prediction_counts_in_denominator(self):
        rows, summary = score_multistep.score([TASK], [])
        self.assertEqual((rows[0]["status"], summary["success_rate_all_offered"]), ("missing", 0.0))


if __name__ == "__main__":
    unittest.main()
