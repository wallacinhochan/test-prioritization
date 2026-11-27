"""Export the 47–48 delta against the immutable ef57715 publication."""
import json
import csv
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
DEST = "evidencias/KAN-18/congelado-expansao-lote-02"
PREVIOUS = "ef577158bc012d87784bbfab1b9ccb4ee80cf812"
TARGETS = (47, 48)


def main(run, upstream, out, *, control=None, kan29=False):
    training = control is not None
    targets = (58, 59, 60) if kan29 else (15, 42) if training else TARGETS
    lot = "04" if kan29 else "03" if training else "02"
    destination = f"evidencias/KAN-18/congelado-expansao-lote-{lot}"
    previous = common.manifest_data(OLD / "manifesto.json")
    for name, expected in previous["saidas_sha256"].items():
        assert common.hash_file(OLD / name) == expected, name
    prior_lots = {}
    occupied = set()
    if training or kan29:
        prior = HERE / "congelado-expansao-lote-02"
        prior_manifest = common.manifest_data(prior / "manifesto.json")
        for name, expected in prior_manifest["saidas_sha256"].items():
            assert common.hash_file(prior / name) == expected, name
        prior_lots["41a22e394de36512921bad82a4a28d029d8bb55f"] = common.hash_file(prior / "manifesto.json")
        occupied = {row["sha"] for row in common.rows(prior / "cobertura.csv")}
    if kan29:
        prior = HERE / "congelado-expansao-lote-03"
        for name, expected in common.manifest_data(prior / "manifesto.json")["saidas_sha256"].items():
            assert common.hash_file(prior / name) == expected, name
        prior_lots["ba7f204693007f18db648fdf16e34f52c62397f7"] = common.hash_file(prior / "manifesto.json")
        occupied.update(row["sha"] for row in common.rows(prior / "cobertura.csv"))
    audit = common.rows(OLD / "cobertura.csv")
    assert len(audit) == 100 and [int(row["posicao"]) for row in audit if row["holdout"] == "true"] == [96]
    times = common.rows(run / "tempos.csv")
    measured = {row["fase"]: (int(row["ns"]), int(row["rc"])) for row in times}
    assert len(measured) == len(times) and all(ns >= 0 for ns, _ in measured.values())
    output = defaultdict(list)
    entries = {}
    git = ["git", f"--git-dir={upstream.resolve()}"]
    for pos in targets:
        row = audit[pos - 1]
        assert row["estado_selecao"] == "indisponivel" and row["holdout"] == "false"
        sha, parent = row["sha"], row["pai"]
        assert parent == audit[pos - 2]["sha"] and sha not in occupied
        assert not training or row["particao"] == "treino"
        assert subprocess.check_output([*git, "rev-parse", f"{sha}^1"], text=True).strip() == parent
        folder = run / str(pos)
        assert common.lines(folder / "sha") == [sha] and common.lines(run / f"{pos}.parent") == [parent]
        if training or kan29:
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
        audit_fallback = None
        training_control = None
        if training:
            control_folder = control / str(pos)
            for name in (f"{pos}.tar", f"{parent}.tar", f"{pos}.parent"):
                assert common.hash_file(run / name) == common.hash_file(control / name)
            for name in ("classes.txt", "changed-tests.txt"):
                assert common.hash_file(folder / name) == common.hash_file(control_folder / name)
            control_status = common.lines(control_folder / "controle.status")[0]
            control_target = common.lines(control_folder / "status")[0]
            assert common.hash_file(control_folder / "estado-pai.hashes") == common.hash_file(control_folder / "estado-restaurado.hashes")
            training_control = {"sem_diff": control_status, "alvo": control_target,
                                "sha256": {f.name: common.hash_file(f) for f in sorted(control_folder.iterdir())}}
            if not fallback:
                if control_status != "zero_sem_diff":
                    audit_fallback = "controle_sem_diff_nao_zero"
                elif control_target != "alvo_validado":
                    audit_fallback = "controle_alvo_invalido"
                elif common.lines(control_folder / "dirts-roots.txt") != common.lines(folder / "dirts-roots.txt"):
                    audit_fallback = "dirts_divergente_do_isolado"
            if audit_fallback:
                fallback, continuity = audit_fallback, "fallback_integral"
                expected_roots = set(common.lines(folder / "classes.txt"))
        if fallback:
            assert continuity == ("fallback_integral" if training else "fallback")
            if not training:
                assert common.lines(folder / "controle.status") == ["fallback_integral"]
            assert expected_roots == set(common.lines(folder / "classes.txt"))
            pure = None
        else:
            if not training:
                assert common.lines(folder / "controle.status") == ["equivalente"]
            assert all(measured[f"{phase}_{pos}"][1] == 0 for phase in
                       ("dirts", "selo", "selecao", "expansao"))
            pure_roots = set(common.lines(folder / "dirts-roots.txt"))
            if training:
                assert continuity == "reancorado_primeiro_pai" and measured[f"inicializacao_{pos}"][1] == 0
                assert "DIRTS included: []" in common.lines(control_folder / "controle.log")
            else:
                prev_seal = (run / "inicializacao.hashes" if pos == targets[0] else run / str(pos - 1) / "continuo.hashes")
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
        ref = f"{destination}/manifesto.json#posicao-{pos:03}"
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
                  if re.search(fr"_{pos}$", phase) or (pos == targets[0] and phase == "inicializacao")}
        controls = {"pai_isolado", "dirts_pai_isolado", "controle_sem_diff", "dirts_alvo_isolado", "validacao_isolada"}
        production = sum(value["ns"] for phase, value in stages.items() if phase.rsplit("_", 1)[0] not in controls)
        cost = "" if audit_fallback else (production + 500000) // 1000000
        output["overhead"].append((sha, "T1", "selection", "unknown" if audit_fallback else "measured", cost, ref))
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
            "controle": training_control if training else common.lines(folder / "controle.status")[0],
            "selos_estado_sha256": {role: common.hash_file(folder / name) if (folder / name).is_file() else None
                                     for role, name in (("pai", "estado-pai.hashes"), ("alvo", "continuo.hashes"))},
            "classes_raiz": {"dirts": None if pure is None else len(pure_roots), "t1": len(selected_roots)},
            "candidatos": len(candidates), "dirts_puro": None if pure is None else len(pure),
            "selecionados": len(included),
            "sha256_conjuntos": {"t0": common.hash_set(candidates), "t1": common.hash_set(included),
                                 "dirts": None if pure is None else common.hash_set(pure)},
            "selection_ns": None if audit_fallback else production,
            "tentativa_selection_ns": production, "fases_ns_rc": stages, "entradas_sha256": hashes,
        }

        if training:
            old = HERE / "../MUTACAO/t1/congelado" / str(pos)
            old_manifest = common.manifest_data(old / "manifesto.json")
            assert (old_manifest["sha"], old_manifest["pai"]) == (sha, parent)
            old_selection = old / "selection.csv"
            assert common.hash_file(old_selection) == old_manifest["saidas_sha256"]["selection.csv"]
            old_rows = common.rows(old_selection)
            assert all(item["commit_sha"] == sha and item["scenario"] == "T1" for item in old_rows)
            old_ids = {item["test_id"] for item in old_rows}
            old_selected = {item["test_id"] for item in old_rows if item["selected"] == "true"}
            assert len(old_ids) == len(old_rows) == old_manifest["candidatos"]
            entries[f"posicao-{pos:03}"]["compatibilidade_inventario_piloto_treino"] = {
                "selecao_antiga_sha256": common.hash_file(old_selection),
                "candidatos_em_comum": len(old_ids & candidates.keys()),
                "so_no_inventario_novo": len(candidates.keys() - old_ids),
                "so_no_inventario_antigo": len(old_ids - candidates.keys()),
                "selecionados_em_comum": len(old_selected & included),
            }

    out.mkdir(parents=True)
    (out / ".gitattributes").write_bytes(b"*.csv -text\n*.json -text\n")
    for name in ("selection", "rankings", "overhead", "rotas", "cobertura"):
        common.write_csv(out / f"{name}.csv", output[name], name)
    if kan29:
        publications = (("base", OLD), ("02", HERE / "congelado-expansao-lote-02"),
                        ("03", HERE / "congelado-expansao-lote-03"), ("04", out))
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
        assert len(availability) == 18
        with (out / "disponibilidade.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(("posicao", "sha", "pai", "particao", "holdout", "estado_selecao", "lote",
                             "continuidade", "candidatos", "selecionados", "fallback", "estado_custo_t1",
                             "custo_selecao_ms"))
            for row in audit:
                details = availability.get(row["sha"])
                writer.writerow((*[row[key] for key in ("posicao", "sha", "pai", "particao", "holdout")],
                                 "congelado" if details else "indisponivel", *(details or ("",) * 7)))

    m = {"contrato": "0.1.0", "seletor": common.VERSION, "lote": lot, "publicacao_base": PREVIOUS,
         "manifesto_base_sha256": common.hash_file(OLD / "manifesto.json"),
         "ordem": previous["ordem"], "politica": previous["politica"], "fallback": previous["fallback"],
         "ambiente": previous["ambiente_reuso"], "holdout": previous["holdout"],
         "cobertura": {"posicoes_delta": list(targets), "soma_com_base": 18 if kan29 else 15 if training else 13,
                       "lacunas": 82 if kan29 else 85 if training else 87},
         "execucao_fisica_de_testes": False,
         "custo": "inicializacao atribuida ao primeiro alvo; selecao ate lista pronta; controles isolados fora do overhead",
         "entradas_comuns_sha256": {p.name: common.hash_file(p) for p in sorted(run.iterdir()) if p.is_file()},
         "codigo_exportador_sha256_lf": common.digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
         "revisoes": entries,
         "saidas_sha256": {p.name: common.hash_file(p) for p in sorted(out.glob("*.csv"))}}
    if kan29:
        final = targets[-1]
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
            m["checkpoint_local"] = {"sha": common.lines(sha_path)[0], "arquivo": checkpoint.name,
                                     "sha256": common.hash_file(checkpoint), "selo_sha256": common.hash_file(seal_path)}
    if prior_lots:
        m["manifestos_lotes_anteriores_sha256"] = prior_lots
    if training:
        m["controle_treino_entradas_sha256"] = {f.name: common.hash_file(f) for f in sorted(control.iterdir()) if f.is_file()}
        m["custo"] = "cada alvo inclui sua propria inicializacao; controles sem diff fora do overhead; execucao fisica indisponivel; fallback definido na auditoria tem custo final desconhecido"
    (out / "manifesto.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
