from pathlib import Path
import unittest

from simular import cronograma, simular


class ReplayTest(unittest.TestCase):
    def test_matches_kan24_table(self):
        resultado = simular(Path(__file__).with_name("fixtures"))
        self.assertEqual(resultado["data_kind"], "synthetic")
        cortes = resultado["cuts"]
        self.assertEqual(len(cortes), 24)
        for corte in cortes[:12]:
            self.assertEqual(corte["gap"]["reason"], "historical_reference_unavailable")
            self.assertIsNone(corte["prefix"])
        esperados = {
            "T0": ("A", "ABC", "ABC"), "T1": ("", "AB", "ABC"),
            "T2": ("C", "CB", "CBA"), "T3": ("", "BC", "BCA"),
        }
        for corte in cortes[12:]:
            indice = (25, 50, 75).index(corte["percent"])
            self.assertEqual(corte["budget_ms"], (25, 51, 77)[indice])
            self.assertEqual(corte["reference"]["commit_order"], 1)
            self.assertEqual(corte["status"], "available")
            testes = corte["prefix"]
            letras = "".join(t["test_id"].split("#test")[1][0] for t in testes)
            self.assertEqual(letras, esperados[corte["scenario"]][indice])
            self.assertEqual("".join(l for l, t in zip(letras, testes) if t["outcome"] == "fail"),
                             "".join(l for l in letras if l in "BC"))
            if indice == 0 and corte["scenario"] in {"T0", "T2"}:
                self.assertEqual(testes[-1]["completed_at_ms"], 25)
            if corte["scenario"] == "T2":
                self.assertEqual(corte["training"]["duration_ms"], "100")

    def test_skip_zero_and_missing_duration(self):
        resultados = {t: {"outcome": estado, "duration_ms": duracao, "source_ref": t}
                      for t, estado, duracao in (
                          ("skip", "skip", ""), ("zero", "pass", "0"),
                          ("fail", "fail", "30"), ("gap", "pass", ""))}
        eventos, _, lacuna = cronograma(
            list(resultados), resultados, [("startup", 5, "fixture")], 77)
        self.assertEqual([(e["test_id"], e["completed_at_ms"]) for e in eventos],
                         [("zero", 5), ("fail", 35)])
        self.assertEqual(lacuna["after_ms"], 35)
        self.assertEqual(lacuna["reason"], "duration_unavailable")

    def test_gap_and_overhead(self):
        _, _, lacuna = cronograma(None, {}, [("startup", 5, "fixture")], 25)
        self.assertEqual(lacuna["reason"], "order_unavailable")
        _, _, lacuna = cronograma(["missing"], {}, [("startup", 5, "fixture")], 25)
        self.assertEqual(lacuna["reason"], "result_unavailable")
        _, _, lacuna = cronograma([], {}, [("startup_unavailable", None, None)], 25)
        self.assertEqual(lacuna["reason"], "startup_unavailable")
        self.assertEqual(cronograma(None, {}, [("startup", 26, "fixture")], 25),
                         ([], 26, None))
