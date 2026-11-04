import unittest

from workloads.build_phase1_sweeps import build


class Phase1SweepTests(unittest.TestCase):
    def test_only_intended_length_changes(self):
        workloads = build()
        a, b = workloads["phase1_context_500"], workloads["phase1_context_2500"]
        self.assertEqual(len(a), 40)
        for shorter, longer in zip(a, b):
            self.assertEqual(shorter["task_id"], longer["task_id"])
            self.assertEqual(shorter["steps"][1:], longer["steps"][1:])
            self.assertEqual(shorter["steps"][0]["max_tokens"], longer["steps"][0]["max_tokens"])
            self.assertTrue(longer["steps"][0]["user"].startswith(shorter["steps"][0]["user"].split("\n\n")[0]))
            self.assertGreater(longer["est_peak_context"], shorter["est_peak_context"])
        a, b = workloads["phase1_output_32"], workloads["phase1_output_512"]
        for shorter, longer in zip(a, b):
            self.assertEqual(shorter["task_id"], longer["task_id"])
            self.assertEqual(shorter["steps"][0]["user"], longer["steps"][0]["user"])
            self.assertEqual((shorter["steps"][0]["max_tokens"], longer["steps"][0]["max_tokens"]), (32, 512))


if __name__ == "__main__":
    unittest.main()
