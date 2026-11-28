"""Exporta o Lote 05 (posicoes 61, 62 e 63) preservando os quatro lotes anteriores intactos."""
import csv
import json
import re
import subprocess
import sys
import tarfile
from collections import defaultdict
from importlib import import_module
from pathlib import Path

common = import_module("congelar-expansao")
baseline = import_module("validar-expansao")
HERE = Path(__file__).resolve().parent
OLD = HERE / "congelado-expansao-v1"
PREVIOUS = "ef577158bc012d87784bbfab1b9ccb4ee80cf812"
TARGETS = (61, 62, 63)
LOT = "05"
DESTINATION = f"evidencias/KAN-18/congelado-expansao-lote-{LOT}"
PRIOR_LOTS = (
    ("02", HERE / "congelado-expansao-lote-02", "41a22e394de36512921bad82a4a28d029d8bb55f"),
    ("03", HERE / "congelado-expansao-lote-03", "ba7f204693007f18db648fdf16e34f52c62397f7"),
    ("04", HERE / "congelado-expansao-lote-04", "767f08b6dc2fe203d925bd9f97883028c3af551d"),
)


def main(run, upstream, out):
    previous = common.manifest_data(OLD / "manifesto.json")
    for name, expected in previous["saidas_sha256"].items():
        assert common.hash_file(OLD / name) == expected, name

    prior_hashes = {}
    occupied = set()
    for _, prior, commit_sha in PRIOR_LOTS:
        prior_manifest = common.manifest_data(prior / "manifesto.json")
        for name, expected in prior_manifest["saidas_sha256"].items():
            assert common.hash_file(prior / name) == expected, name
        prior_hashes[commit_sha] = common.hash_file(prior / "manifesto.json")
        occupied.update(row["sha"] for row in common.rows(prior / "cobertura.csv"))

    audit = common.rows(OLD / "cobertura.csv")
    assert len(audit) == 100 and [int(row["posicao"]) for row in audit if row["holdout"] == "true"] == [96]

    times = common.rows(run / "tempos.csv")
    measured = {row["fase"]: (int(row["ns"]), int(row["rc"])) for row in times}
    assert len(measured) == len(times) and all(ns >= 0 for ns, _ in measured.values())

    output = defaultdict(list)
    entries = {}
    git = ["git", "-c", "safe.directory=*", f"--git-dir={upstream.resolve()}"]

    for pos in TARGETS:
        row = audit[pos - 1]
        assert row["estado_selecao"] == "indisponivel" and row["holdout"] == "false"
        sha, parent = row["sha"], row["pai"]
        assert parent == audit[pos - 2]["sha"] and sha not in occupied
        assert subprocess.check_output([*git, "rev-parse", f"{sha}^1"], text=True).strip() == parent

        folder = run / str(pos)
        assert common.lines(folder / "sha") == [sha] and common.lines(run / f"{pos}.parent") == [parent]
        for archive, expected in ((f"{pos}.tar", sha), (f"{parent}.tar", parent)):
            with (run / archive).open("rb") as stream:
                identity = subprocess.check_output([*git, "get-tar-commit-id"], stdin=stream).decode().strip()
            assert identity == expected, archive

        diff = subprocess.check_output([*git, "diff", "--no-renames", "--name-status", parent, sha],
                                       text=True).splitlines()
        assert common.lines(folder / "diff.txt") == diff

        fallback = (folder / "fallback").read_text(encoding="utf-8").strip()
        continuity = common.lines(folder / "continuidade")[0]
        candidates = common.inventory(folder / "metodos.tsv")
        assert candidates and measured[f"inventario_jdeps_{pos}"][1] == 0
        expected_roots = set(common.lines(folder / "expanded-roots.txt"))

        if fallback:
            assert continuity == "fallback"
            assert common.lines(folder / "controle.status") == ["fallback_integral"]
            assert expected_roots == set(common.lines(folder / "classes.txt"))
            pure = None
            pure_roots = set()
        else:
            assert common.lines(folder / "controle.status") == ["equivalente"]
            assert all(measured[f"{phase}_{pos}"][1] == 0 for phase in
                       ("dirts", "selo", "selecao", "expansao"))
            pure_roots = set(common.lines(folder / "dirts-roots.txt"))
            prev_seal = (run / "inicializacao.hashes" if pos == TARGETS[0] else run / str(pos - 1) / "continuo.hashes")
            if continuity == "incremental":
                assert common.hash_file(prev_seal) == common.hash_file(folder / "estado-pai.hashes")
            else:
                assert continuity == "reconstruido" and measured[f"reconstrucao_{pos}"][1] == 0
            assert "DIRTS included: []" in common.lines(folder / "isolado/controle.log")
            assert measured[f"validacao_isolada_{pos}"][1] == 0
            assert pure_roots == set(common.lines(folder / "isolado/dirts-roots.txt"))
            pure = {test for test, root in candidates.items() if root in pure_roots}

        included = {test for test, root in candidates.items() if root in expected_roots}
        changed = {match.group(1).replace("/", ".") for line in diff
                   if (match := re.fullmatch(r"[AM]\tsrc/main/java/([A-Za-z0-9_$/]+)\.java", line))}
        assert changed == set(common.lines(folder / "changed-prod.txt"))

        graph = folder / "jdeps.txt"
        graph_hash = common.hash_file(graph)
        edges = defaultdict(set)
        if fallback:
            assert included == candidates.keys()
        else:
            graph_text = graph.read_text(encoding="utf-8")
            assert baseline.expand(pure, set(candidates), graph_text, changed) == included
            for line in graph_text.splitlines():
                matched = common.EDGE.fullmatch(line)
                if matched:
                    src, dst = (name.split("$", 1)[0] for name in matched.groups())
                    if dst in changed:
                        edges[src].add(dst)

        ref = f"{DESTINATION}/manifesto.json#posicao-{pos:03}"
        for test in sorted(candidates):
            selected = test in included
            reason = "fallback" if fallback else "dependency" if selected else "no_dependency"
            output["selection"].append((sha, "T1", test, str(selected).lower(), reason, ref))
        for rank, test in enumerate(sorted(included), 1):
            output["rankings"].append((sha, "T1", test, rank, "", ref))

        selected_roots = {candidates[test] for test in included}
        for root in sorted(selected_roots):
            evidence = edges[root]
            state = "fallback" if fallback else "direta_jdeps" if evidence else "sem_evidencia_rota"
            output["rotas"].append((sha, root, "" if pure is None else str(root in pure_roots).lower(), "true",
                                    str(bool(fallback)).lower(), "|".join(sorted(evidence)),
                                    graph_hash if evidence else "", state))

        stages = {phase: {"ns": ns, "rc": rc} for phase, (ns, rc) in measured.items()
                  if re.search(fr"_{pos}$", phase) or (pos == TARGETS[0] and phase == "inicializacao")}
        controls = {"pai_isolado", "dirts_pai_isolado", "controle_sem_diff", "dirts_alvo_isolado", "validacao_isolada"}
        production = sum(value["ns"] for phase, value in stages.items() if phase.rsplit("_", 1)[0] not in controls)
        cost = (production + 500000) // 1000000
        output["overhead"].append((sha, "T1", "selection", "measured", cost, ref))
        output["cobertura"].append((pos, sha, parent, row["particao"], "false", "congelado",
                                    continuity, len(candidates), "" if pure is None else len(pure),
                                    len(included), str(bool(fallback)).lower()))

        hashes = {}
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                hashes[path.relative_to(run).as_posix()] = common.hash_file(path)
        entries[f"posicao-{pos:03}"] = {
            "posicao": pos, "sha": sha, "pai": parent, "diff_nome_status": diff,
            "continuidade": continuity, "fallback": fallback or None,
            "controle": common.lines(folder / "controle.status")[0],
            "selos_estado_sha256": {role: common.hash_file(folder / name) if (folder / name).is_file() else None
                                    for role, name in (("pai", "estado-pai.hashes"), ("alvo", "continuo.hashes"))},
            "classes_raiz": {"dirts": None if pure is None else len(pure_roots), "t1": len(selected_roots)},
            "candidatos": len(candidates), "dirts_puro": None if pure is None else len(pure),
            "selecionados": len(included),
            "sha256_conjuntos": {"t0": common.hash_set(candidates), "t1": common.hash_set(included),
                                 "dirts": None if pure is None else common.hash_set(pure)},
            "selection_ns": production, "tentativa_selection_ns": production,
            "fases_ns_rc": stages, "entradas_sha256": hashes,
        }

    out.mkdir(parents=True)
    (out / ".gitattributes").write_bytes(b"*.csv -text\n*.json -text\n")
    for name in ("selection", "rankings", "overhead", "rotas", "cobertura"):
        common.write_csv(out / f"{name}.csv", output[name], name)

    publications = (("base", OLD), *((lbl, p) for lbl, p, _ in PRIOR_LOTS), (LOT, out))
    availability = {}
    for label, publication in publications:
        costs = {row["commit_sha"]: row for row in common.rows(publication / "overhead.csv")}
        for row in common.rows(publication / "cobertura.csv"):
            if row["estado_selecao"] != "congelado":
                continue
            sha = row["sha"]
            assert sha not in availability and sha in costs
            cost = costs[sha]
            availability[sha] = (label, row["continuidade"], row["candidatos"], row["selecionados"],
                                 row["fallback"], cost["measurement_status"], cost["duration_ms"])
    assert len(availability) == 21
    with (out / "disponibilidade.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("posicao", "sha", "pai", "particao", "holdout", "estado_selecao", "lote",
                         "continuidade", "candidatos", "selecionados", "fallback", "estado_custo_t1",
                         "custo_selecao_ms"))
        for row in audit:
            details = availability.get(row["sha"])
            writer.writerow((*[row[key] for key in ("posicao", "sha", "pai", "particao", "holdout")],
                             "congelado" if details else "indisponivel", *(details or ("",) * 7)))

    image_id = (run / "image-id.txt").read_text(encoding="utf-8").strip() if (run / "image-id.txt").is_file() else None
    env_info = dict(previous["ambiente_reuso"])
    if image_id:
        env_info["imagem_dirts_local"] = image_id

    m = {
        "contrato": "0.1.0",
        "seletor": common.VERSION,
        "lote": LOT,
        "publicacao_base": PREVIOUS,
        "manifesto_base_sha256": common.hash_file(OLD / "manifesto.json"),
        "manifestos_lotes_anteriores_sha256": prior_hashes,
        "ordem": previous["ordem"],
        "politica": previous["politica"],
        "fallback": previous["fallback"],
        "ambiente": env_info,
        "holdout": previous["holdout"],
        "cobertura": {"posicoes_delta": list(TARGETS), "soma_com_base": 21, "lacunas": 79},
        "execucao_fisica_de_testes": False,
        "custo": "inicializacao atribuida ao primeiro alvo; selecao ate lista pronta; controles isolados fora do overhead",
        "entradas_comuns_sha256": {p.name: common.hash_file(p) for p in sorted(run.iterdir()) if p.is_file()},
        "codigo_exportador_sha256_lf": common.digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "revisoes": entries,
        "saidas_sha256": {p.name: common.hash_file(p) for p in sorted(out.glob("*.csv"))},
    }
    final = TARGETS[-1]
    checkpoint = run / f"estado-{final}.tar"
    if checkpoint.exists():
        seal_path = run / f"estado-{final}.hashes"
        sha_path = run / f"estado-{final}.sha"
        seal = dict((name, checksum) for checksum, name in
                    (line.split("  ", 1) for line in common.lines(seal_path)))
        assert common.hash_file(seal_path) == common.hash_file(run / str(final) / "continuo.hashes")
        assert common.lines(sha_path) == [entries[f"posicao-{final:03}"]["sha"]]
        exported = {}
        with tarfile.open(checkpoint) as archive:
            for member in archive:
                assert member.isdir() or member.isfile(), member.name
                if member.isfile():
                    assert member.name.startswith(".dirts/") and member.name not in exported
                    exported[member.name] = common.digest(archive.extractfile(member).read())
        assert exported == seal
        m["checkpoint_local"] = {
            "sha": common.lines(sha_path)[0],
            "arquivo": checkpoint.name,
            "sha256": common.hash_file(checkpoint),
            "selo_sha256": common.hash_file(seal_path),
        }
    (out / "manifesto.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n",
                                        encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
