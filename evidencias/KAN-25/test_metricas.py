import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from metricas import EVIDENCIAS, apfdc, avaliar, deteccao, tradeoff


class Metricas(unittest.TestCase):
    def test_rq1_tempo_reducao_deteccao_e_treino(self):
        resultados = {"A": ("pass", 20), "B": ("fail", 15),
                      "C": ("fail", 10), "D": ("pass", 36), "E": ("skip", None)}
        t0 = {"suite_duration_ms": "99"}
        custos = [{"phase": fase, "duration_ms": duracao, "source_ref": "fixture"}
                  for fase, duracao in (("startup", 5), ("selection", 5),
                                       ("features", 4), ("inference", 0))]
        corte = {"costs": custos,
                 "training": {"measurement_status": "measured", "duration_ms": "100"}}
        linha = tradeoff("T2", {"B", "E"}, resultados, {"B", "C"}, t0, corte)
        self.assertEqual(linha["tempo_total_ms"], 29)
        self.assertEqual(linha["treinamento_ms"], 100)
        self.assertEqual(linha["reducao"], 0.75)
        self.assertEqual(linha["proporcao"], 0.5)
        self.assertEqual(linha["testes_selecionados_brutos"], 2)
        custos[-1]["duration_ms"] = None
        linha = tradeoff("T2", {"B"}, resultados, {"B", "C"}, t0, corte)
        self.assertIsNone(linha["tempo_total_ms"])
        self.assertEqual(linha["detectadas"], 1)

    def test_rq1_populacao_vazia_ou_incompativel(self):
        corte = {"costs": [], "training": None}
        linha = tradeoff("T0", {"E"}, {"E": ("skip", None)}, set(),
                         {"suite_duration_ms": "0"}, corte)
        self.assertEqual(linha["tempo_total_ms"], 0)
        self.assertEqual(linha["detectadas"], 0)
        self.assertIsNone(linha["proporcao"])
        self.assertIsNone(linha["reducao"])
        linha = tradeoff("T1", {"ausente"}, {"A": ("pass", 0)}, set(), {}, corte)
        self.assertEqual(linha["motivo_populacao"], "populacao_nao_comparavel")

    def test_rq2_zero_empates_limites_e_sem_falhas(self):
        eventos = [{"test_id": t, "completed_at_ms": tempo, "outcome": "fail"}
                   for t, tempo in (("A", 0), ("B", 25), ("C", 25))]
        corte = {"status": "available", "budget_ms": 25, "prefix": eventos}
        linha = deteccao(corte, {"A", "B", "C", "D"})
        self.assertEqual(linha["primeira_falha_ms"], 0)
        self.assertEqual(linha["proporcao"], 0.75)
        self.assertEqual([p["detectadas"] for p in linha["curva"]], [1, 3])
        corte.update(prefix=[], budget_ms=0)
        linha = deteccao(corte, set())
        self.assertEqual(linha["detectadas"], 0)
        self.assertIsNone(linha["proporcao"])
        self.assertEqual(linha["estado_primeira_falha"], "nao_observada")
        self.assertEqual(len(linha["curva"]), 1)
        self.assertIsNone(deteccao(corte, None)["detectadas"])

    def test_rq2_indisponivel_e_fora_do_limite(self):
        corte = {"status": "unavailable", "gap": {"reason": "order_unavailable"}}
        linha = deteccao(corte, set())
        self.assertIsNone(linha["curva"])
        self.assertEqual(linha["estado_primeira_falha"], "indisponivel")
        corte.update(status="available", budget_ms=25, prefix=[
            {"test_id": "A", "completed_at_ms": 26, "outcome": "fail"},
        ])
        with self.assertRaises(ValueError):
            deteccao(corte, {"A"})

    def test_apfdc_conta_conhecida_igualdade_e_perda(self):
        a, b, c = ["A", "B", "C"]
        resultados = {a: ("pass", 20), b: ("fail", 15), c: ("fail", 10),
                      "D": ("fail", 36)}
        ordens = {"T1": [a, b, c], "T2": [c, b, a], "T3": [b, c, a]}
        linha = apfdc(ordens, {a, b, c}, resultados, {b, c, "D"})
        self.assertEqual(linha["apfdc"], {"T1": 22.5/90, "T2": 67.5/90, "T3": 62.5/90})
        empate = apfdc(dict(ordens, T3=ordens["T2"]), {a, b, c}, resultados, {b, c})
        self.assertEqual(empate["apfdc"]["T2"], empate["apfdc"]["T3"])
        self.assertEqual(linha["falhas_excluidas"], 1)

    def test_apfdc_indisponibilidade_e_limites(self):
        ordens = {"T1": ["A", "B"], "T2": ["B", "A"], "T3": ["A", "B"]}
        resultados = {"A": ("fail", 0), "B": ("pass", 10)}
        linha = apfdc(ordens, {"A", "B"}, resultados, {"A"})
        self.assertEqual(linha["apfdc"], {"T1": 1, "T2": 0, "T3": 1})
        for dados, rankings, falhas, motivo in (
            (resultados, dict(ordens, T2=None), {"A"}, "ordem_indisponivel"),
            (resultados, ordens, set(), "sem_falhas_na_populacao"),
            ({"A": ("fail", 0)}, ordens, {"A"}, "populacao_nao_comparavel"),
            (dict(resultados, B=("pass", None)), ordens, {"A"}, "duracao_indisponivel"),
            (dict(resultados, B=("pass", 0)), ordens, {"A"}, "custo_total_zero"),
        ):
            with self.subTest(motivo=motivo):
                self.assertEqual(apfdc(rankings, {"A", "B"}, dados, falhas)["motivo"], motivo)

    def test_integracao_commit_kan23(self):
        repo = EVIDENCIAS.parents[1] / "KAN-23-24-checkout"
        if not repo.is_dir():
            self.skipTest("checkout irmão KAN-23-24 necessário para a integração")
        artefato = subprocess.check_output([
            "git", "-C", str(repo), "archive", "--format=zip", "c6e1ca1", "evidencias/KAN-23",
        ])
        with tempfile.TemporaryDirectory() as temporario:
            with zipfile.ZipFile(io.BytesIO(artefato)) as arquivo:
                arquivo.extractall(temporario)
            base = Path(temporario) / "evidencias" / "KAN-23"
            fixture = base / "fixtures"
            replay = json.loads(subprocess.check_output(
                ["python", "-B", str(base / "simular.py"), str(fixture)]))
            saida = avaliar(fixture, replay)
            replay_json = base / "replay.json"
            replay_json.write_text(json.dumps(replay), encoding="utf-8")
            cli = json.loads(subprocess.check_output([
                "python", "-B", str(EVIDENCIAS / "KAN-25" / "metricas.py"),
                str(fixture), str(replay_json),
            ]))
            self.assertEqual(cli, json.loads(json.dumps(saida)))
        self.assertEqual(saida["data_kind"], "synthetic")
        primeiro, segundo = saida["revisoes"]
        self.assertTrue(all(c["motivo"] == "historical_reference_unavailable" for c in primeiro["rq2"]))
        self.assertEqual([r["tempo_total_ms"] for r in segundo["rq1"]], [99, 55, 60, 71])
        self.assertEqual([r["reducao"] for r in segundo["rq1"]], [0, 0.25, 0.25, 0.25])
        self.assertEqual([r["detectadas"] for r in segundo["rq2"]],
                         [0, 0, 1, 0, 2, 1, 2, 2, 2, 2, 2, 2])
        self.assertEqual(segundo["rq2"][2]["primeira_falha_ms"], 25)
        self.assertEqual(segundo["apfdc"]["apfdc"], {"T1": 22.5/90, "T2": 67.5/90, "T3": 62.5/90})
        for p in (25, 50, 75):
            self.assertEqual(saida["cobertura_rq2"][p]["comuns"], [segundo["commit_sha"]])


if __name__ == "__main__":
    unittest.main()
