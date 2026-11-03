import unittest

from evaluation.score_qa import answer_scores, score


def task(task_id, answer="WH-123", kind="long_context"):
    return {"task_id": task_id, "type": kind, "execution": {"model_calls": 1},
            "evaluation": {"normalization": "squad_v1" if kind == "short_qa" else "strip_whitespace",
                           "answers": [{"text": answer}]}}


def prediction(task_id, text="WH-123", **overrides):
    return {"task_id": task_id, "text": text, "status": "ok", "steps_done": 1,
            "response_complete": True, "truncated": False, **overrides}


class QualityScoringTests(unittest.TestCase):
    def test_failed_and_missing_remain_in_denominator(self):
        tasks = [task(str(i)) for i in range(4)]
        _, result = score(tasks, [prediction("0"), prediction("1", "wrong"),
                                  prediction("2", status="timeout")])
        self.assertEqual(result["offered"], 4)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["missing"], 1)
        self.assertEqual(result["completion_rate"], 0.5)
        self.assertEqual(result["accuracy_among_completed"], 0.5)
        self.assertEqual(result["success_rate_all_offered"], 0.25)

    def test_incomplete_or_truncated_output_is_not_success(self):
        for overrides in ({"response_complete": False}, {"truncated": True},
                          {"steps_done": 0}, {"text": ""}):
            with self.subTest(overrides=overrides):
                _, result = score([task("a")], [prediction("a", **overrides)])
                self.assertEqual(result["completed"], 0)
                self.assertEqual(result["correct"], 0)
                self.assertIsNone(result["accuracy_among_completed"])

    def test_identifier_matching_preserves_punctuation_and_case(self):
        self.assertEqual(answer_scores(" WH-123\n", task("a")), (1, None))
        for text in ["WH123", "wh-123", "WH-123 or WH-456", "The answer is WH-123."]:
            self.assertEqual(answer_scores(text, task("a")), (0, None))

    def test_squad_matching_and_partial_credit(self):
        qa = task("a", "Denver Broncos", "short_qa")
        self.assertEqual(answer_scores("The Denver Broncos.", qa), (1, 1.0))
        exact, f1 = answer_scores("Denver", qa)
        self.assertEqual(exact, 0)
        self.assertAlmostEqual(f1, 2 / 3)

    def test_duplicate_and_unknown_predictions_rejected(self):
        for predictions in ([prediction("a"), prediction("a")], [prediction("unknown")]):
            with self.assertRaises(ValueError):
                score([task("a")], predictions)
        with self.assertRaises(ValueError):
            score([task("a"), task("a")], [])

    def test_all_missing_is_zero_success_not_perfect_accuracy(self):
        _, result = score([task("a"), task("b", "Denver", "short_qa")], [])
        self.assertEqual(result["success_rate_all_offered"], 0)
        self.assertIsNone(result["accuracy_among_completed"])
        self.assertEqual(result["mean_token_f1_all_offered_squad"], 0)


if __name__ == "__main__":
    unittest.main()
