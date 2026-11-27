"""Export the 47–48 delta against the immutable ef57715 publication."""
import json
import re
import subprocess
import sys
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


def main(run, upstream, out):
    previous = common.manifest_data(OLD / "manifesto.json")
    for name, expected in previous["saidas_sha256"].items():
        assert common.hash_file(OLD / name) == expected, name
    audit = common.rows(OLD / "cobertura.csv")
    assert len(audit) == 100 and [int(row["posicao"]) for row in audit if row["holdout"] == "true"] == [96]
    times = common.rows(run / "tempos.csv")
    measured = {row["fase"]: (int(row["ns"]), int(row["rc"])) for row in times}
    assert len(measured) == len(times) and all(ns >= 0 for ns, _ in measured.values())
    output = defaultdict(list)
    entries = {}
    git = ["git", f"--git-dir={upstream.resolve()}"]
    for pos in TARGETS:
        row = audit[pos - 1]
        assert row["estado_selecao"] == "indisponivel" and row["holdout"] == "false"
        sha, parent = row["sha"], row["pai"]
        assert parent == audit[pos - 2]["sha"]
        assert subprocess.check_output([*git, "rev-parse", f"{sha}^1"], text=True).strip() == parent
        folder = run / str(pos)
        assert common.lines(folder / "sha") == [sha] and common.lines(run / f"{pos}.parent") == [parent]
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
        else:
            assert common.lines(folder / "controle.status") == ["equivalente"]
            assert all(measured[f"{phase}_{pos}"][1] == 0 for phase in
                       ("dirts", "selo", "selecao", "expansao", "validacao_isolada"))
            prev_seal = (run / "inicializacao.hashes" if pos == 47 else run / str(pos - 1) / "continuo.hashes")
            if continuity == "incremental":
                assert common.hash_file(prev_seal) == common.hash_file(folder / "estado-pai.hashes")
            else:
                assert continuity == "reconstruido" and measured[f"reconstrucao_{pos}"][1] == 0
            assert "DIRTS included: []" in common.lines(folder / "isolado/controle.log")
            pure_roots = set(common.lines(folder / "dirts-roots.txt"))
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
        ref = f"{DEST}/manifesto.json#posicao-{pos:03}"
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
                  if re.search(fr"_{pos}$", phase) or (pos == 47 and phase == "inicializacao")}
        controls = {"pai_isolado", "dirts_pai_isolado", "controle_sem_diff", "dirts_alvo_isolado", "validacao_isolada"}
        production = sum(value["ns"] for phase, value in stages.items() if phase.rsplit("_", 1)[0] not in controls)
        output["overhead"].append((sha, "T1", "selection", "measured", (production + 500000) // 1000000, ref))
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
            "selection_ns": production, "fases_ns_rc": stages, "entradas_sha256": hashes,
        }

    out.mkdir(parents=True)
    (out / ".gitattributes").write_bytes(b"*.csv -text\n*.json -text\n")
    for name in ("selection", "rankings", "overhead", "rotas", "cobertura"):
        common.write_csv(out / f"{name}.csv", output[name], name)
    m = {"contrato": "0.1.0", "seletor": common.VERSION, "lote": "02", "publicacao_base": PREVIOUS,
         "manifesto_base_sha256": common.hash_file(OLD / "manifesto.json"),
         "ordem": previous["ordem"], "politica": previous["politica"], "fallback": previous["fallback"],
         "ambiente": previous["ambiente_reuso"], "holdout": previous["holdout"],
         "cobertura": {"posicoes_delta": list(TARGETS), "soma_com_base": 13, "lacunas": 87},
         "execucao_fisica_de_testes": False,
         "custo": "inicializacao atribuida ao primeiro alvo; selecao ate lista pronta; controles isolados fora do overhead",
         "entradas_comuns_sha256": {p.name: common.hash_file(p) for p in sorted(run.iterdir()) if p.is_file()},
         "codigo_exportador_sha256_lf": common.digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
         "revisoes": entries,
         "saidas_sha256": {p.name: common.hash_file(p) for p in sorted(out.glob("*.csv"))}}
    (out / "manifesto.json").write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
