"""Valida as cinco publicacoes imutaveis de T1 (v1 + lotes 02..05) e a disponibilidade acumulada."""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

PUBLICATIONS = (
    "congelado-expansao-v1",
    "congelado-expansao-lote-02",
    "congelado-expansao-lote-03",
    "congelado-expansao-lote-04",
    "congelado-expansao-lote-05",
)


def table(path):
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        return reader.fieldnames, list(reader)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root):
    visible = {}
    schemas = {}
    keys = defaultdict(set)
    for name in PUBLICATIONS:
        folder = root / name
        document = json.loads((folder / "manifesto.json").read_text(encoding="utf-8"))
        assert document["contrato"] == "0.1.0" and document["holdout"]["rotulos_lidos"] is False
        for file, digest in document["saidas_sha256"].items():
            assert sha256(folder / file) == digest, f"{name}/{file}"
        selected = defaultdict(list)
        populations = defaultdict(set)
        ranking = defaultdict(list)
        cost = {}
        for file, id_field in (("selection.csv", "test_id"), ("rankings.csv", "test_id"), ("overhead.csv", "phase")):
            header, rows = table(folder / file)
            assert header == schemas.setdefault(file, header)
            for row in rows:
                sha, scenario = row["commit_sha"], row["scenario"]
                key = (sha, scenario, row[id_field])
                assert scenario == "T1" and key not in keys[file]
                keys[file].add(key)
                if file == "selection.csv":
                    populations[sha].add(row[id_field])
                    if row["selected"] == "true":
                        assert row["selection_reason"] in {"dependency", "fallback"}
                        selected[sha].append(row[id_field])
                    else:
                        assert (row["selected"], row["selection_reason"]) == ("false", "no_dependency")
                elif file == "rankings.csv":
                    assert int(row["rank"]) == len(ranking[sha]) + 1 and row["score"] == ""
                    ranking[sha].append(row[id_field])
                else:
                    assert row["phase"] == "selection" and sha not in cost
                    status, duration = row["measurement_status"], row["duration_ms"]
                    assert status in {"measured", "unknown"}
                    assert duration.isdecimal() if status == "measured" else duration == ""
                    cost[sha] = (status, duration)
        assert set(populations) == set(cost)
        for sha in populations:
            assert selected[sha] == ranking[sha] == sorted(ranking[sha])
            visible[sha] = (len(populations[sha]), len(ranking[sha]), *cost[sha])

    manifests = [root / name / "manifesto.json" for name in PUBLICATIONS]
    assert document["manifesto_base_sha256"] == sha256(manifests[0])
    assert set(document["manifestos_lotes_anteriores_sha256"].values()) == {sha256(f) for f in manifests[1:4]}
    revisions = list(document["revisoes"].values())
    assert [item["posicao"] for item in revisions] == [61, 62, 63]
    for parent, child in zip(revisions, revisions[1:]):
        assert child["pai"] == parent["sha"]
        if child["continuidade"] == "incremental":
            assert child["selos_estado_sha256"]["pai"] == parent["selos_estado_sha256"]["alvo"]
    if checkpoint := document.get("checkpoint_local"):
        assert checkpoint["sha"] == revisions[-1]["sha"]
        assert checkpoint["selo_sha256"] == revisions[-1]["selos_estado_sha256"]["alvo"]

    availability = table(root / PUBLICATIONS[-1] / "disponibilidade.csv")[1]
    historical = table(root / PUBLICATIONS[0] / "cobertura.csv")[1]
    assert len(availability) == len(historical) == 100
    assert [row["sha"] for row in availability if row["holdout"] == "true"] == [availability[95]["sha"]]
    for i, (row, old) in enumerate(zip(availability, historical, strict=True), 1):
        assert row["posicao"] == str(i)
        assert all(row[k] == old[k] for k in ("posicao", "sha", "pai", "particao", "holdout"))
        assert i == 1 or row["pai"] == availability[i - 2]["sha"]
        if row["sha"] in visible:
            assert row["estado_selecao"] == "congelado" and row["lote"]
            assert (int(row["candidatos"]), int(row["selecionados"]), row["estado_custo_t1"],
                    row["custo_selecao_ms"]) == visible[row["sha"]]
        else:
            assert row["estado_selecao"] == "indisponivel"
            assert all(row[k] == "" for k in ("lote", "continuidade", "candidatos", "selecionados",
                                              "fallback", "estado_custo_t1", "custo_selecao_ms"))
    assert len(visible) == 21
    print(json.dumps({
        "revisoes": len(availability),
        "disponiveis": len(visible),
        "lacunas": 100 - len(visible),
        "linhas": {name: len(group) for name, group in keys.items()},
        "custo_medido": sum(row[2] == "measured" for row in visible.values()),
    }, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
