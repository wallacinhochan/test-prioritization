"""Freeze the ten filtered selections, then score them from the unchanged replay."""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Reuse the exact expansion and CSV/hash conventions from the preserved evidence.
from importlib import import_module

baseline = import_module("validar-expansao")

HERE = Path(__file__).resolve().parent
IMAGE = "sha256:fad87a144128c905f9ba915f61c03abe436372c2c6e26a02a18984369c42a4ea"
JAVA = re.compile(rb"src/(main|test)/java/[A-Za-z0-9_$/]+\.java")


def digest(tests):
    return baseline.sha256("".join(f"{test}\n" for test in sorted(tests)).encode())


def freeze(checkout, upstream, output):
    output.mkdir(parents=True)
    paths = []
    git = ["git", f"--git-dir={upstream.resolve()}"]

    def read_git(*args):
        return subprocess.check_output([*git, *args])

    def stage(before, after):
        n = len(paths) // 2
        for suffix, content in (("a", before), ("b", after)):
            path = f"{n}-{suffix}.java"
            (output / path).write_bytes(content)
            paths.append("/data/" + path)
        return n

    controls = [
        ("comentario", b"class T {/* x */ int x;}", b"class T {/* y */ int x;}", "equivalente"),
        ("espacos", b"class T{int x=1;}", b"class T { int x = 1; }", "equivalente"),
        ("literal", b'class T{String s="a  b";}', b'class T{String s="a b";}', "tokens_distintos"),
        ("operador", b"class T{int x=+ +1;}", b"class T{int x=++1;}", "tokens_distintos"),
        ("deprecated", b"/** x */ class T{}", b"/** @deprecated x */ class T{}", "tokens_distintos"),
        ("unicode", b"class T{/* x */}", rb"class T{/* \u000a */}", "incerto"),
        ("lexico", b"class T{}", b"class T{/*", "incerto"),
    ]
    for _, before, after, _ in controls:
        stage(before, after)
    local = checkout / "evidencias/KAN-18/local"
    pilot = local / "starts-poc"
    study = pilot / "estudo-20261124-134619"
    dirts = pilot / "dirts-20261124-151151"
    reference = json.loads((checkout / "evidencias/KAN-18/comparacao-dirts.json").read_text(encoding="utf-8"))
    previous = {r["posicao"]: r for r in json.loads((HERE / "validacao-expansao.json").read_text(encoding="utf-8-sig"))}
    work = []
    for entry in reference["revisoes"]:
        pos, sha, parent = (entry[key] for key in ("posicao", "sha", "pai"))
        assert read_git("rev-parse", f"{sha}^1").decode().strip() == parent
        fields = read_git("diff", "--raw", "-z", "--no-renames", "--abbrev=40", parent, sha).split(b"\0")
        assert fields.pop() == b""
        touched, pairs = set(), []
        eligible = True
        for header, path in zip(fields[::2], fields[1::2], strict=True):
            old_mode, new_mode, old_blob, new_blob, status = header[1:].split()
            if path == b"src/changes/changes.xml" and (old_mode, new_mode, status) == (b"100644", b"100644", b"M"):
                continue
            if path.startswith(b"src/main/java/") and path.endswith(b".java"):
                touched.add(path.decode()[len("src/main/java/"):-5].replace("/", "."))
            if JAVA.fullmatch(path) and (old_mode, new_mode, status) == (b"100644", b"100644", b"M"):
                pairs.append(stage(read_git("cat-file", "blob", old_blob.decode()),
                                   read_git("cat-file", "blob", new_blob.decode())))
            else:
                eligible = False
        inventory_home = study / str(pos)
        if not inventory_home.exists():
            inventory_home = pilot / "linux-pares-20261124-131107" / str(pos)
        universe = set((inventory_home / "ids-inventario.txt").read_text(encoding="utf-8-sig").splitlines())
        run = dirts if entry["rodada_dirts"] == "independente" else dirts / "estado-continuo"
        base = set((run / str(pos) / "ids-finais.txt").read_text(encoding="utf-8-sig").splitlines())
        assert len(universe) == entry["candidatos"] and len(base) == entry["dirts"] and base <= universe
        integrated = local / "dirts/selecao" / sha / "rankings.csv"
        if integrated.exists():
            assert base == {row["test_id"] for row in baseline.csv_rows(integrated)}
        graph_path = local / "dirts/entradas" / sha / "jdeps.txt"
        if not graph_path.exists():
            graph_path = inventory_home / "jdeps.txt"
        graph = graph_path.read_bytes() if touched and base != universe else b""
        expanded = baseline.expand(base, universe, graph.decode(), touched) if graph else base
        assert base <= expanded <= universe and digest(expanded) == previous[pos]["sha256_lista_expandida"]
        assert (baseline.sha256(graph) if graph else None) == previous[pos]["sha256_jdeps"]
        work.append((entry, eligible and bool(pairs), pairs, universe, base, expanded))

    source = HERE / "CompararTokensJava.java"
    (output / source.name).write_bytes(source.read_bytes())
    exports = ["--add-exports=jdk.compiler/com.sun.tools.javac." + package + "=ALL-UNNAMED"
               for package in ("parser", "util")]
    command = ["docker", "run", "--rm", "--pull", "never", "--platform", "linux/amd64",
               "--mount", f"type=bind,source={output.resolve()},target=/data,readonly",
               IMAGE, "java", *exports, "/data/" + source.name, *paths]
    decisions = subprocess.check_output(command, text=True).splitlines()
    assert len(decisions) == len(paths) // 2
    results = []
    for index, (name, _, _, expected) in enumerate(controls):
        assert decisions[index] == expected, (name, decisions[index])
        results.append({"controle": name, "resultado": decisions[index]})
    plans = []
    lists = {}
    for entry, eligible, pairs, universe, base, expanded in work:
        decisions_for_pair = [decisions[index] for index in pairs]
        suppress = eligible and all(value == "equivalente" for value in decisions_for_pair)
        filtered = base if suppress else expanded
        assert base <= filtered <= expanded <= universe
        plan = {"posicao": entry["posicao"], "sha": entry["sha"], "pai": entry["pai"],
                "fallback_integral": entry["fallback_integral"], "suprimir_expansao": suppress,
                "difflimitado_a_modificacoes_java": eligible, "comparacoes_java": decisions_for_pair}
        plans.append(plan)
        named = dict(t0=universe, dirts=base, expansao=expanded, filtro=filtered)
        plan["metodos"] = {name: len(values) for name, values in named.items()}
        plan["sha256"] = {name: digest(values) for name, values in named.items()}
        lists[entry["sha"]] = {name: sorted(values) for name, values in named.items()}
    manifest = {"controles": results, "revisoes": plans}
    (output / "congelado.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "listas.json").write_text(json.dumps(lists) + "\n", encoding="utf-8")


def score(checkout, output):
    manifest = json.loads((output / "congelado.json").read_text(encoding="utf-8"))
    lists = json.loads((output / "listas.json").read_text(encoding="utf-8"))
    sets = {sha: {name: set(values) for name, values in group.items()} for sha, group in lists.items()}
    for row in manifest["revisoes"]:
        for name, values in sets[row["sha"]].items():
            assert len(values) == row["metodos"][name] and digest(values) == row["sha256"][name]
    replay = checkout / "evidencias/MUTACAO/modelos/entrega-replay"
    expected = {name: sha for sha, name in
                (line.split() for line in (replay / "SHA256SUMS").read_text().splitlines())}
    for relative in ("dados/observacoes.csv", "dados/metodos.csv"):
        assert baseline.sha256((replay / relative).read_bytes().replace(b"\r\n", b"\n")) == expected[relative]
    detectors = defaultdict(lambda: defaultdict(set))
    keys = set()
    for row in baseline.csv_rows(replay / "dados/observacoes.csv"):
        sha, mutant, test = (row[key] for key in ("sha", "mutation_id", "test_id"))
        if sha in sets:
            assert test in sets[sha]["t0"] and (sha, mutant, test) not in keys
            keys.add((sha, mutant, test))
            tests = detectors[sha][mutant]
            if row["label"] == "induced_failure":
                tests.add(test)
    for row in manifest["revisoes"]:
        sha = row["sha"]
        if sha in detectors:
            detected = [tests for tests in detectors[sha].values() if tests]
            row["mutantes_rotulados"] = len(detectors[sha])
            row["mutantes_detectados"] = {name: sum(bool(values & tests) for tests in detected)
                                         for name, values in sets[sha].items()}
    manifest["sha256_csv_replay"] = {name: expected[name] for name in ("dados/observacoes.csv", "dados/metodos.csv")}
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    action, *paths = sys.argv[1:]
    {"congelar": freeze, "rotular": score}[action](*(Path(path) for path in paths))
