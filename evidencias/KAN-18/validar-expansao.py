"""Recalcula a expansão direta sobre a amostra DIRTS já definida."""
import csv
import hashlib
import json
import re
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

PROJECT_EDGE = re.compile(r"\s+(\S+)\s+->\s+(\S+)\s+(?:classes|test-classes)\s*")


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def expand(base, universe, graph, changed):
    touched = changed.copy()
    for line in graph.splitlines():
        edge = PROJECT_EDGE.fullmatch(line)
        if edge:
            source, target = (name.split("$")[0] for name in edge.groups())
            if target in changed:
                touched.add(source)
    return base | {test for test in universe if test.split("#")[0].split("$")[0] in touched}


def main(checkout, upstream):
    local = checkout / "evidencias/KAN-18/local"
    pilot = local / "starts-poc"
    study = pilot / "estudo-20261124-134619"
    dirts = pilot / "dirts-20261124-151151"
    reference = json.loads((checkout / "evidencias/KAN-18/comparacao-dirts.json").read_text(encoding="utf-8"))
    selections = {}
    report = []
    for entry in reference["revisoes"]:
        position, sha, parent = (entry[key] for key in ("posicao", "sha", "pai"))
        result = {"posicao": position, "sha": sha, "inventario": entry["candidatos"],
                  "t1_anterior": entry["t1_anterior"], "dirts": entry["dirts"]}
        report.append(result)
        inventory_home = study / str(position)
        if not inventory_home.exists():
            inventory_home = pilot / "linux-pares-20261124-131107" / str(position)
        universe = set((inventory_home / "ids-inventario.txt").read_text(encoding="utf-8-sig").splitlines())
        run = dirts if entry["rodada_dirts"] == "independente" else dirts / "estado-continuo"
        base_file = run / str(position) / "ids-finais.txt"
        base = set(base_file.read_text(encoding="utf-8-sig").splitlines())
        assert len(universe) == entry["candidatos"] and len(base) == entry["dirts"] and base <= universe, position
        integrated = local / "dirts/selecao" / sha / "rankings.csv"
        if integrated.exists():
            assert base == {row["test_id"] for row in csv_rows(integrated)}, position
        git = ["git", f"--git-dir={upstream.resolve()}"]
        assert subprocess.check_output([*git, "rev-parse", f"{sha}^1"], text=True).strip() == parent
        diff = subprocess.check_output([*git, "diff", "--name-only", parent, sha], text=True).splitlines()
        prefix = "src/main/java/"
        changed = {path[len(prefix):-5].replace("/", ".") for path in diff
                   if path.startswith(prefix) and path.endswith(".java")}
        graph_file = local / "dirts/entradas" / sha / "jdeps.txt"
        if not graph_file.exists():
            graph_file = inventory_home / "jdeps.txt"
        if changed and base != universe and not graph_file.exists():
            result["motivo"] = "jdeps_indisponivel"
            continue
        graph_bytes = graph_file.read_bytes() if changed and base != universe else b""
        graph = graph_bytes.decode("utf-8")
        timings = []
        for _ in range(7):
            start = time.perf_counter_ns()
            expanded = expand(base, universe, graph, changed) if graph else base
            timings.append((time.perf_counter_ns() - start) / 1e6)
        assert base <= expanded <= universe
        selections[sha] = (universe, base, expanded)
        result.update(expansao=len(expanded), incremento_mediano_ms=round(statistics.median(timings), 3),
                      sha256_jdeps=sha256(graph_bytes) if graph_bytes else None,
                      sha256_lista_expandida=sha256("".join(f"{test}\n" for test in sorted(expanded)).encode()))

    # Os rótulos são abertos somente depois de congelar todos os conjuntos.
    replay = checkout / "evidencias/MUTACAO/modelos/entrega-replay"
    observations = replay / "dados/observacoes.csv"
    expected = dict((name, digest) for digest, name in
                    (line.split() for line in (replay / "SHA256SUMS").read_text().splitlines()))
    for relative in ("dados/observacoes.csv", "dados/metodos.csv"):
        data = (replay / relative).read_bytes().replace(b"\r\n", b"\n")
        assert sha256(data) == expected[relative], relative
    detectors = defaultdict(lambda: defaultdict(set))
    seen = set()
    for row in csv_rows(observations):
        sha, mutation, test = (row[key] for key in ("sha", "mutation_id", "test_id"))
        if sha in selections:
            assert (sha, mutation, test) not in seen and test in selections[sha][0]
            seen.add((sha, mutation, test))
            detectors[sha][mutation]
            if row["label"] == "induced_failure":
                detectors[sha][mutation].add(test)
    for result in report:
        sha = result["sha"]
        if sha not in detectors:
            continue
        _, base, expanded = selections[sha]
        known = [tests for tests in detectors[sha].values() if tests]
        result["mutantes"] = {
            "total": len(detectors[sha]), "detectados_t0": len(known),
            "detectados_dirts": sum(bool(tests & base) for tests in known),
            "detectados_expansao": sum(bool(tests & expanded) for tests in known),
        }
    methods = defaultdict(dict)
    for row in csv_rows(replay / "dados/metodos.csv"):
        if row["sha"] in detectors:
            assert row["test_id"] not in methods[row["sha"]]
            methods[row["sha"]][row["test_id"]] = row["duracao_intacto_ms"]
    for result in report:
        sha = result["sha"]
        if sha not in methods:
            continue
        universe, base, expanded = selections[sha]
        assert methods[sha].keys() == universe
        result["soma_duracoes_intacto_ms"] = {
            name: sum(float(methods[sha][test]) for test in tests)
            if all(methods[sha][test] for test in tests) else None
            for name, tests in (("t0", universe), ("dirts", base), ("expansao", expanded))
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main(*(Path(arg) for arg in sys.argv[1:]))
