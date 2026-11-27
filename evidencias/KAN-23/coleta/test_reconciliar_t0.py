from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from reconciliar_t0 import alinhar, descritor, exportar_kan15


class ColetaTest(unittest.TestCase):
    def test_intersecta_ancoras_e_rejeita_deriva(self):
        with TemporaryDirectory() as temp:
            ancoras = Path(temp) / "ancoras.tsv"
            marcos = Path(temp) / "marcos.tsv"
            marcos.write_text(
                "prepare_start\t9.00\nrunner_start\t10.00\n"
                "reports_start\t11.10\nreports_finish\t11.11\n", encoding="utf-8")
            ancoras.write_text("start\t0\t10.01\t1000000\n"
                               "finish\t1000000000\t11.01\t1001000000\n", encoding="utf-8")
            resultado = alinhar(ancoras, marcos, 999000000)
            self.assertEqual(resultado["wall_ms"], 2110)
            self.assertEqual(resultado["plan_origin_lower_ns"], 999000000)
            self.assertEqual(resultado["plan_origin_upper_ns"], 1020000000)
            ancoras.write_text(ancoras.read_text().replace("11.01", "11.08"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "relógios incompatíveis"):
                alinhar(ancoras, marcos, 999000000)

    def test_preserva_classe_executora_e_assinatura(self):
        uid = "[engine:junit-jupiter]/[class:p.T]/[nested-class:N]"
        self.assertEqual(descritor(uid + "/[method:x()]", "p.Base#x()"),
                         (("p.T$N", "x"), "p.T$N#x()"))
        template = uid + "/[test-template:x(java.lang.String)]"
        self.assertIsNone(descritor(template, "p.Base#x(java.lang.String)"))
        self.assertEqual(descritor(template + "/[test-template-invocation:#2]",
                                   "p.Base#x(java.lang.String)"),
                         (("p.T$N", "x(String)[2]"), "p.T$N#x(java.lang.String)"))
        self.assertEqual(descritor(uid + "/[test-factory:x()]/[dynamic-test:#2]", "p.Base#x()"),
                         (("p.T$N", "x()[2]"), "p.T$N#x()"))
        self.assertEqual(descritor(template, "p.Base#x(java.lang.String)", ignorado=True),
                         (("p.T$N", "x(String)"), "p.T$N#x(java.lang.String)"))
        multi = uid + "/[test-template:x(java.lang.String, int)]/[test-template-invocation:#2]"
        self.assertEqual(descritor(multi, "p.Base#x(java.lang.String, int)"),
                         (("p.T$N", "x(String, int)[2]"), "p.T$N#x(java.lang.String,int)"))

    def test_exportacao_exige_cobertura_completa(self):
        with TemporaryDirectory() as temp:
            pasta = Path(temp)
            resumo = {"gaps": {"unmatched_xml_cases": 1}, "matched_cases": 0, "xml_cases": 1,
                      "xml_outcomes": {"pass": 1}}
            with self.assertRaisesRegex(ValueError, "T0 incompleto"):
                exportar_kan15(pasta, resumo, [], "a" * 40, "evidencia")
            self.assertEqual(list(pasta.iterdir()), [])
