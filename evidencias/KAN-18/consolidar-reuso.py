"""Summarize measured stages, validate method sets, and read Surefire XML counts."""
import csv
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_lines(path):
    return path.read_text(encoding="utf-8-sig").splitlines()


def collect_xml(folder):
    files = sorted(folder.glob("TEST-*.xml"))
    assert files, folder
    totals = dict.fromkeys(("tests", "skipped", "failures", "errors"), 0)
    roots = set()
    hashes = {}
    for file in files:
        data = file.read_bytes()
        suite = ET.fromstring(data)
        assert suite.tag == "testsuite", file
        roots.add(suite.attrib["name"].split("$", 1)[0])
        for key in totals:
            totals[key] += int(suite.attrib[key])
        assert len(suite.findall("testcase")) == int(suite.attrib["tests"]), file
        hashes[file.name] = sha256(data)
    assert totals["failures"] == totals["errors"] == 0, folder
    return dict(**totals, relatorios=len(files), raizes=sorted(roots), sha256_xml=hashes)


def main(out, checkout):
    parser = """
import { readFileSync } from 'node:fs';
import { inventario } from '../MUTACAO/t1/selecionar.mjs';
const items = inventario(readFileSync(process.argv[1], 'utf8'));
console.log(JSON.stringify([...items].map(([id, row]) => [id, row.classe])));
"""
    with (out / "tempos.csv").open(newline="") as stream:
        records = list(csv.DictReader(stream))
    timings = {r["fase"]: {"ns": int(r["ns"]), "rc": int(r["rc"])} for r in records}
    assert len(records) == len(timings) and all(row["rc"] == 0 for row in timings.values()), timings
    results = []
    for pos in (49, 50):
        directory = out / str(pos)
        sha = read_lines(directory / "sha")[0]
        parent = read_lines(out / f"{pos}.parent")[0]
        assert not any(read_lines(directory / "fallback")), pos
        raw = subprocess.check_output(["node", "--input-type=module", "-e", parser,
                                       str((directory / "metodos.tsv").resolve())], cwd=HERE)
        inventory = dict(json.loads(raw))
        roots = {name: set(read_lines(directory / path)) for name, path in
                 (("dirts", "dirts-roots.txt"), ("expansao", "expanded-roots.txt"),
                  ("isolado", "isolado/dirts-roots.txt"))}
        assert roots["dirts"] == roots["isolado"] <= roots["expansao"] <= set(inventory.values()), pos
        selection = {"t0": sorted(inventory)}
        for name, group in roots.items():
            selection[name] = sorted(test for test, root in inventory.items() if root in group)
        if pos == 50:
            local = checkout / "evidencias/KAN-18/local"
            ranking = local / "dirts/selecao" / sha / "rankings.csv"
            with ranking.open(newline="", encoding="utf-8-sig") as stream:
                assert selection["dirts"] == sorted(row["test_id"] for row in csv.DictReader(stream))
            previous = json.loads((HERE / "validacao-expansao.json").read_text(encoding="utf-8-sig"))
            expected = next(row for row in previous if row["posicao"] == 50)["sha256_lista_expandida"]
            assert sha256("".join(test + "\n" for test in selection["expansao"]).encode()) == expected
        execution = {mode: collect_xml(directory / f"{mode}-xml") for mode in ("reuso", "t0")}
        assert set(execution["reuso"]["raizes"]) == roots["expansao"], pos
        reports = {}
        for name, tests in selection.items():
            data = "".join(test + "\n" for test in tests).encode()
            (directory / f"ids-{name}.txt").write_bytes(data)
            reports[name] = {"metodos": len(tests), "sha256": sha256(data)}
        prod = ("arvore_reuso", "dirts", "selo", "inventario_jdeps", "selecao", "expansao", "reuso_test")
        incremental_ns = sum(timings[f"{name}_{pos}"]["ns"] for name in prod)
        t0_ns = sum(timings[f"{name}_{pos}"]["ns"] for name in ("arvore_t0", "t0_test"))
        evidence = ("metodos.tsv", "jdeps.txt", "continuo.hashes", "continuo.log", "continuo.excludes",
                    "isolado/pai.log", "isolado/controle.log", "isolado/alvo.log", "isolado/alvo.excludes",
                    "reuso.log", "t0.log")
        for name in ("continuo.log", "isolado/alvo.log"):
            assert "Exporting graph of the new revision" in (directory / name).read_text(encoding="utf-8")
        results.append({"posicao": pos, "sha": sha, "pai": parent, "selecoes": reports,
                        "ns_reuso_regime": incremental_ns, "ns_t0": t0_ns, "surefire": execution,
                        "sha256_evidencias": {name: sha256((directory / name).read_bytes()) for name in evidence}})
    faults = read_lines(out / "falhas.csv")
    assert faults == ["parent_divergente,rejeitado", "estado_ausente,rejeitado",
                      "estado_adulterado,rejeitado", "reconstrucao,validada"], faults
    cold = timings["inicializacao"]["ns"]
    regime = sum(row["ns_reuso_regime"] for row in results)
    t0 = sum(row["ns_t0"] for row in results)
    integrity = {str(path.relative_to(out)): sha256(path.read_bytes()) for path in
                 (*sorted(out.glob("*.tar")), out / "medir-reuso.sh", out / "DescobertaT0.java",
                  out / "inicializacao.hashes", out / "falhas.csv", out / "tempos.csv")}
    print(json.dumps({"revisoes": results, "falhas_injetadas": faults, "fases": timings,
                      "ns_inicio": cold, "ns_regime": regime, "ns_com_inicio": cold + regime,
                      "ns_t0": t0, "sha256_entradas_e_controles": integrity}, indent=2))


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
