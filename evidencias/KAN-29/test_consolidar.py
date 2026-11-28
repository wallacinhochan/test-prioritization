import json
import unittest
from pathlib import Path

import consolidar as c


class ConsolidarKan29Test(unittest.TestCase):
    def test_signature_and_rounding(self):
        self.assertEqual(c.signature("org.a.B#foo()"), (3, 0, 0))
        self.assertEqual(c.signature("org.a.B$Inner#bar(int,java.lang.String)"), (3, 2, 1))
        self.assertEqual(c.round_ms("1.8575"), "2")
        self.assertEqual(c.round_ms(""), "")

    def test_versioned_consolidated_report_invariants(self):
        report_path = c.BASE / "consolidado-58-60.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(data["ticket"], "KAN-29")
        self.assertEqual(data["contract_version"], "0.1.0")
        self.assertFalse(data["official_full_100_campaign"])
        self.assertEqual(data["holdout"], {"position": 96, "labels_read": False, "excluded_from_pack": True})
        self.assertEqual(data["sources"]["kan22_historical_ranking_rows"], 0)

        cov = data["coverage_100_commits"]
        self.assertEqual(sum(cov["counts"].values()), 100)
        self.assertEqual(cov["evaluated_main_consecutive_positions"], [58, 59, 60])
        self.assertEqual(len(data["main_consecutive_results"]), 3)

        # Strict chronological reference: 57->58, 58->59, 59->60
        expected_refs = {58: 57, 59: 58, 60: 59}
        for item in data["main_consecutive_results"]:
            pos = item["position"]
            self.assertEqual(item["reference_t0_position"], expected_refs[pos])
            self.assertEqual(len(item["rq1"]), 4)
            self.assertEqual({r["cenario"] for r in item["rq1"]}, {"T0", "T1", "T2", "T3"})
            # Zero natural failures -> APFDc explicitly unavailable with reason
            self.assertEqual(item["apfdc"]["motivo"], "sem_falhas_na_populacao")
            # Every budget 25/50/75 available across all 4 scenarios
            for p in ("25", "50", "75"):
                for sc in ("T0", "T1", "T2", "T3"):
                    self.assertEqual(item["rq2_by_budget"][p]["scenarios"][sc]["status"], "available")

        # Training attributed once per scenario at position 58 (first served by janela-50)
        pos58_rq1 = {r["cenario"]: r for r in data["main_consecutive_results"][0]["rq1"]}
        self.assertEqual(pos58_rq1["T2"]["estado_treinamento"], "measured")
        self.assertEqual(pos58_rq1["T3"]["estado_treinamento"], "measured")
        for item in data["main_consecutive_results"][1:]:
            rq1 = {r["cenario"]: r for r in item["rq1"]}
            self.assertEqual(rq1["T2"]["estado_treinamento"], "sem_evento_registrado")
            self.assertEqual(rq1["T3"]["estado_treinamento"], "sem_evento_registrado")

        # Auxiliary synthetic evidence kept strictly separate
        aux = data["auxiliary_synthetic_evidence_separate"]
        self.assertEqual(aux["position"], 50)
        self.assertEqual(aux["mutants_total"], 4)


if __name__ == "__main__":
    unittest.main()
