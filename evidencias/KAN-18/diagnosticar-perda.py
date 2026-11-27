"""Cruza seleções pré-execução com o replay publicado da posição 50."""

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


SHA = "f24c027ff83b90beab2ec28696721200abb4f9e9"
BASE = "f4a25e96e7f2a6d74171ecbb80e8fd29863196e8"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def git(*args):
    return subprocess.check_output(["git", *args])


def main(local, upstream):
    replay = Path(__file__).resolve().parents[1] / "MUTACAO"
    selection = local / "selecao" / SHA
    inputs = local / "entradas" / SHA
    frozen = replay / "t1" / "congelado" / "50"
    manifest = json.loads((selection / "manifesto.json").read_text(encoding="utf-8"))
    old_manifest = json.loads((frozen / "manifesto.json").read_text(encoding="utf-8"))
    parent = manifest["pai"]
    hashes = {}
    for root, documented, files in (
        (selection, manifest["saidas_sha256"], ("rankings.csv", "selection.csv", "diff.patch")),
        (inputs, manifest["entradas_sha256"], ("jdeps.txt", "alvo.log", "alvo.excludes", "controle.log")),
        (frozen, old_manifest["saidas_sha256"], ("rankings.csv",)),
    ):
        for name in files:
            actual = digest(root / name)
            assert actual == documented[name], (root, name, actual)
            hashes[f"{root.parent.name}/{name}"] = actual

    upstream_arg = f"--git-dir={upstream.resolve()}"
    assert git(upstream_arg, "rev-parse", SHA + "^").decode().strip() == parent
    diff = git(upstream_arg, "diff", "--name-only", parent, SHA).decode().splitlines()
    prefix = "src/main/java/"
    changed = {
        name[len(prefix):-5].replace("/", ".")
        for name in diff if name.startswith(prefix) and name.endswith(".java")
    }
    reverse = defaultdict(set)
    for line in (inputs / "jdeps.txt").read_text(encoding="utf-8").splitlines():
        edge = re.fullmatch(r"\s+(\S+)\s+->\s+(\S+)\s+(?:classes|test-classes)\s*", line)
        if edge:
            source, target = (name.split("$")[0] for name in edge.groups())
            reverse[target].add(source)
    direct = set().union(*(reverse[name] for name in changed))
    closure = changed | direct
    frontier = direct
    while frontier:
        frontier = set().union(*(reverse[name] for name in frontier)) - closure
        closure |= frontier

    def ranks(path):
        data = rows(path)
        assert all(row["commit_sha"] == SHA and row["scenario"] == "T1" for row in data)
        assert [int(row["rank"]) for row in data] == list(range(1, len(data) + 1))
        result = {row["test_id"]: int(row["rank"]) for row in data}
        assert len(result) == len(data)
        return result

    dirts = ranks(selection / "rankings.csv")
    old = ranks(frozen / "rankings.csv")
    decisions = rows(selection / "selection.csv")
    universe = {row["test_id"] for row in decisions}
    assert len(universe) == len(decisions) == manifest["candidatos"]
    assert all(row["commit_sha"] == SHA for row in decisions)
    assert set(dirts) == {row["test_id"] for row in decisions if row["selected"] == "true"}
    assert len(dirts) == manifest["selecionados"] and set(old) <= universe

    def expand(classes):
        return set(dirts) | {test for test in universe if test.split("#")[0].split("$")[0] in classes}

    def ordinal_ranks(tests):
        return {test: rank for rank, test in enumerate(
            sorted(tests, key=lambda test: test.encode("utf-16-be")), 1
        )}

    variants = {
        "dirts": dirts,
        "t1_piloto": old,
        "dirts_jdeps_direto": ordinal_ranks(expand(changed | direct)),
        "dirts_jdeps_transitivo": ordinal_ranks(expand(closure)),
        "fallback_integral": ordinal_ranks(universe),
    }

    published = replay / "modelos" / "entrega-replay"
    relative = "dados/observacoes.csv"
    git_path = f"evidencias/MUTACAO/modelos/entrega-replay/{relative}"
    csv_hash = hashlib.sha256(git("show", f"{BASE}:{git_path}")).hexdigest()
    expected = {path: checksum for checksum, path in
                (line.split() for line in (published / "SHA256SUMS").read_text().splitlines())}
    assert csv_hash == expected[relative]
    observations = published / relative
    normalized = observations.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == csv_hash
    hashes["PR2/dados/observacoes.csv"] = csv_hash
    hashes["checkout/dados/observacoes.csv"] = digest(observations)
    variants_manifest = json.loads((replay / "mutantes" / "pos-50" / "manifesto.json").read_text(encoding="utf-8"))
    detectors = defaultdict(set)
    labels = defaultdict(lambda: defaultdict(int))
    seen = set()
    for row in rows(observations):
        if row["sha"] != SHA:
            continue
        mutation, test, label = (row[key] for key in ("mutation_id", "test_id", "label"))
        assert test in universe and (mutation, test) not in seen
        seen.add((mutation, test))
        labels[mutation][label] += 1
        if label == "induced_failure":
            detectors[mutation].add(test)
    assert len(detectors) == 3 and all(tests & old.keys() for tests in detectors.values()), labels
    assert all(sum(counts.values()) == len(universe) for counts in labels.values())
    raw_excludes = set((inputs / "alvo.excludes").read_text().splitlines())
    result = {
        "sha": SHA, "pai": parent, "merge_pr2": BASE, "hashes": hashes,
        "diff": diff, "classes_producao": sorted(changed), "custo_dirts_original": manifest["custo"],
        "rotulos": labels,
        "manifesto_mutantes": variants_manifest,
        "detectores": {
            mutation: {
                test: {
                    "exclusao_bruta": test.split("#")[0].replace(".", "/") + ".java" in raw_excludes,
                    "postos": {name: ranking.get(test) for name, ranking in variants.items()},
                } for test in sorted(tests)
            } for mutation, tests in sorted(detectors.items())
        },
        "variantes": {
            name: {
                "metodos": len(ranking),
                "adicionais_vs_dirts": len(ranking.keys() - dirts.keys()),
                "fracao_inventario": round(len(ranking) / len(universe), 6),
                "mutantes_preservados": sum(bool(tests & ranking.keys()) for tests in detectors.values()),
                "sha256_ids_em_ordem_lf": hashlib.sha256(
                    "".join(f"{test}\n" for test in ranking).encode()
                ).hexdigest(),
            } for name, ranking in variants.items()
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main(*(Path(arg) for arg in sys.argv[1:]))
