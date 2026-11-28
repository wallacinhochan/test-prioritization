import unittest

import comparar as c


class CompararKan28Test(unittest.TestCase):
    def test_correlations_and_percentiles(self):
        self.assertAlmostEqual(c.pearson([1, 2, 3, 4], [2, 4, 6, 8]), 1.0, places=6)
        self.assertAlmostEqual(c.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0, places=6)
        self.assertAlmostEqual(c.spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0, places=6)
        self.assertIsNone(c.pearson([5, 5, 5], [1, 2, 3]))
        self.assertAlmostEqual(c.percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5), 3.0)
        self.assertAlmostEqual(c.percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.9), 4.6)

    def test_compare_method_durations_detects_mismatches_and_ignores_skips(self):
        t0 = {
            "A": {"outcome": "pass", "invocations": 1, "duration_ns": 10_000_000},
            "B": {"outcome": "pass", "invocations": 3, "duration_ns": 20_000_000},
            "C": {"outcome": "skip", "invocations": 1, "duration_ns": None},
        }
        phys = {
            "A": {"outcome": "pass", "invocations": 1, "duration_ns": 12_000_000},
            "B": {"outcome": "pass", "invocations": 3, "duration_ns": 18_000_000},
            "C": {"outcome": "skip", "invocations": 1, "duration_ns": None},
        }
        res = c.compare_method_durations(t0, phys)
        self.assertEqual(res["common_methods"], 3)
        self.assertEqual(res["executed_compared"], 2)
        self.assertEqual(res["outcome_mismatches"], [])
        self.assertEqual(res["invocation_count_mismatches"], [])
        self.assertAlmostEqual(res["t0_sum_ms"], 30.0)
        self.assertAlmostEqual(res["physical_sum_ms"], 30.0)
        self.assertAlmostEqual(res["sum_diff_ms"], 0.0)
        self.assertAlmostEqual(res["per_method_diff_ms"]["median_abs"], 2.0)

        phys_bad = dict(phys, A={"outcome": "fail", "invocations": 2, "duration_ns": 12_000_000})
        res_bad = c.compare_method_durations(t0, phys_bad)
        self.assertEqual(len(res_bad["outcome_mismatches"]), 1)
        self.assertEqual(len(res_bad["invocation_count_mismatches"]), 1)

    def test_physical_prefix_count_tracks_clock_uncertainty_at_boundary(self):
        # origin in [100ms, 120ms], overhead=10ms, budget=150ms
        # method 1 ends at 15ms -> [125, 145] <= 150 (guaranteed)
        # method 2 ends at 30ms -> [140, 160] crosses 150 (uncertain)
        # method 3 ends at 45ms -> [155, 175] > 150 (excluded)
        res = c.physical_prefix_count(
            [15_000_000, 30_000_000, 45_000_000],
            plan_origin_lower_ns=100_000_000,
            plan_origin_upper_ns=120_000_000,
            pre_execution_overhead_ms=10,
            budget_ms=150,
        )
        self.assertEqual(res["completed_guaranteed"], 1)
        self.assertEqual(res["completed_optimistic"], 2)
        self.assertEqual(res["boundary_uncertain_methods"], 1)

    def test_versioned_physical_validation_report_invariants(self):
        import json
        report_path = c.BASE / "validacao-fisica-50.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(data["ticket"], "KAN-28")
        self.assertFalse(data["official_budget_evaluation"])
        self.assertEqual(data["physical_runs"]["t0_49"]["matched_cases"], 59953)
        self.assertEqual(data["physical_runs"]["t0_50"]["matched_cases"], 59953)
        self.assertEqual(data["physical_runs"]["t1_surefire_50"]["matched_cases"], 51172)
        for key in ("t1_ordenado_50", "t2_ordenado_50", "t3_ordenado_50"):
            run = data["physical_runs"][key]
            self.assertEqual(run["methods_total"], 416)
            self.assertEqual(run["methods_discovered"], 416)
            self.assertEqual(run["total_invocations"], 51172)
            self.assertEqual(run["order_exact_match_pct"], 100.0)
        for comp in data["method_duration_comparisons"].values():
            self.assertEqual(comp["common_methods"], 416)
            self.assertEqual(comp["executed_compared"], 412)
            self.assertEqual(comp["outcome_mismatches"], [])
            self.assertEqual(comp["invocation_count_mismatches"], [])
        self.assertEqual(data["decision_adequacy"]["status"], "adequada_com_restricoes_explicitas")
        self.assertGreaterEqual(len(data["decision_adequacy"]["conditions"]), 5)


if __name__ == "__main__":
    unittest.main()
