"""Freeze the verified KAN-18 selections independently of any oracle or labels."""
import csv
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = "evidencias/KAN-18/congelado-expansao-v1"
EDGE = re.compile(r"\s+(\S+)\s+->\s+(\S+)\s+(?:classes|test-classes)\s*")
PREFIX = "src/main/java/"
VERSION = "dirts-expansao-direta-reuso/1.0.0"
VERDICT = "670381c27d7ff48983e8fd097d52ba3878b94a1e"
IMAGE = "sha256:fad87a144128c905f9ba915f61c03abe436372c2c6e26a02a18984369c42a4ea"
FIELDS = {
    "commits": "commit_sha commit_order committed_at eligibility_status exclusion_reason build_changed tests_changed source_ref",
    "selection": "commit_sha scenario test_id selected selection_reason source_ref",
    "rankings": "commit_sha scenario test_id rank score source_ref",
    "overhead": "commit_sha scenario phase measurement_status duration_ms source_ref",
    "cobertura": "posicao sha pai particao holdout estado_selecao continuidade candidatos dirts selecionados fallback",
    "rotas": "commit_sha classe_raiz selecionada_dirts selecionada_expansao fallback sementes_diretas jdeps_evidencia estado_rota",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def hash_file(path):
    return digest(path.read_bytes())


def hash_set(items):
    return digest("".join(item + "\n" for item in sorted(items)).encode())


def rows(path, delimiter=","):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def lines(path):
    return path.read_text(encoding="utf-8-sig").splitlines()


def inventory(path):
    result = {}
    for row in rows(path, "\t"):
        clazz = row["classe"]
        test = f'{clazz}#{row["metodo"]}({row["tipos"]})'
        assert test not in result and row["raiz"] == clazz.split("$", 1)[0], test
        assert row["tipo_descritor"] in {"method", "test-template", "test-factory"}
        assert row["descritor"].startswith("[engine:junit-jupiter]/")
        result[test] = row["raiz"]
    return result


def write_csv(path, data, name):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writerow(FIELDS[name].split())
        writer.writerows(data)


def manifest_data(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(checkout, upstream, measured, out):
    archive = HERE / "../KAN-10/commits.csv"
    audit = rows(archive)
    git = ["git", f"--git-dir={upstream.resolve()}"]

    def query(*args):
        return subprocess.check_output([*git, *args], text=True, encoding="utf-8").splitlines()

    assert len(audit) == len({r["commit_sha"] for r in audit}) == 100
    chain = query("log", "-100", "--first-parent", "--format=%H%x09%P%x09%cI", audit[-1]["commit_sha"])
    for pos, (row, record) in enumerate(zip(audit, reversed(chain), strict=True), 1):
        sha, parents, date = record.split("\t")
        utc = datetime.fromisoformat(date).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        assert (str(pos), sha, parents.split()[0], utc) == (row["position"], row["commit_sha"],
                                                            row["first_parent_sha"], row["committer_date_utc"])
        assert pos == 1 or row["first_parent_sha"] == audit[pos - 2]["commit_sha"]

    local = checkout / "evidencias/KAN-18/local"
    pilot = local / "starts-poc"
    comparison = manifest_data(checkout / "evidencias/KAN-18/comparacao-dirts.json")
    legacy = {r["posicao"]: r for r in comparison["revisoes"]}
    frozen = {r["posicao"]: r for r in manifest_data(HERE / "filtro-congelado.json")["revisoes"]}
    expansion_evidence = {r["posicao"]: r for r in manifest_data(HERE / "validacao-expansao.json")}
    run = manifest_data(HERE / "reuso-resultado.json")
    current = {r["posicao"]: r for r in run["revisoes"]}
    assert set(current) == {49, 50}
    assert current[49]["sha"] == current[50]["pai"]
    assert hash_file(measured / "tempos.csv") == run["sha256_entradas_e_controles"]["tempos.csv"]
    output = defaultdict(list)
    entries = {}
    for row in audit:
        pos = int(row["position"])
        sha, parent = row["commit_sha"], row["first_parent_sha"]
        partition = "treino" if pos <= 42 else "validacao" if pos <= 50 else "avaliacao"
        output["commits"].append((sha, pos, row["committer_date_utc"], row["eligibility_status"],
                                  row["blocker_reason"] if row["eligibility_status"] == "ineligible" else "",
                                  row["build_changed"], row["tests_changed"], f"evidencias/KAN-10/commits.csv#{sha}"))
        if pos not in legacy and pos not in current:
            output["cobertura"].append((pos, sha, parent, partition, str(pos == 96).lower(),
                                        "indisponivel", "", "", "", "", ""))
            continue

        fallback = pos in legacy and legacy[pos]["fallback_integral"]
        if pos in current:
            logged = current[pos]
            assert (sha, parent) == (logged["sha"], logged["pai"])
            source = measured / str(pos)
            tsv = source / "metodos.tsv"
            graph_file = source / "jdeps.txt"
            for name in ("metodos.tsv", "jdeps.txt", "continuo.hashes"):
                assert hash_file(source / name) == logged["sha256_evidencias"][name]
            pure_file = source / "ids-dirts.txt"
            continuity = "cronologico_validado"
            expected = {key: value["sha256"] for key, value in logged["selecoes"].items()}
            assert expected["dirts"] == expected["isolado"]
            evidence = [source / "continuo.hashes", source / "isolado/dirts-roots.txt",
                        measured / "inicializacao.hashes", measured / "tempos.csv"]
        else:
            previous = legacy[pos]
            assert (sha, parent) == (previous["sha"], previous["pai"])
            source = pilot / "estudo-20261124-134619" / str(pos)
            if not (source / "ids-inventario.txt").exists():
                source = pilot / "linux-pares-20261124-131107" / str(pos)
            tsv = source / "metodos.tsv"
            graph_file = local / "dirts/entradas" / sha / "jdeps.txt"
            if not graph_file.exists():
                graph_file = source / "jdeps.txt"
            pure_path = pilot / "dirts-20261124-151151"
            isolated = previous["rodada_dirts"] == "independente"
            if not isolated:
                pure_path /= "estado-continuo"
            pure_file = pure_path / str(pos) / "ids-finais.txt"
            continuity = ("fallback_integral" if fallback else "isolado" if isolated
                          else "historico_reancorado_sem_validacao_cronologica")
            expected = frozen[pos]["sha256"]
            evidence = [source / "ids-inventario.txt"]
        candidates = inventory(tsv)
        if pos not in current:
            assert set(candidates) == set(lines(source / "ids-inventario.txt"))
        pure = set(lines(pure_file))
        assert pure <= candidates.keys()
        assert hash_set(candidates) == expected["t0"] and hash_set(pure) == expected["dirts"]
        pure_roots = {candidates[test] for test in pure}
        assert {test for test, root in candidates.items() if root in pure_roots} == pure
        diff = query("diff", "--no-renames", "--name-status", parent, sha)
        changed = {line.split("\t")[1][len(PREFIX):-5].replace("/", ".")
                   for line in diff if "\t" + PREFIX in line and line.endswith(".java")}
        routes = defaultdict(set)
        graph_hash = ""
        used_graph = bool(changed and not fallback and pure != candidates.keys())
        if used_graph:
            graph_hash = hash_file(graph_file)
            for line in graph_file.read_text(encoding="utf-8").splitlines():
                edge = EDGE.fullmatch(line)
                if edge:
                    origin, target = (name.split("$", 1)[0] for name in edge.groups())
                    if target in changed:
                        routes[origin].add(target)
            if pos not in current:
                previous_expansion = expansion_evidence[pos]
                assert graph_hash == previous_expansion["sha256_jdeps"]
            evidence.append(graph_file)
        included = pure if fallback else {test for test, root in candidates.items()
                                          if root in pure_roots or root in routes or root in changed}
        assert hash_set(included) == expected["expansao"] and pure <= included
        if fallback:
            assert pure == included == candidates.keys()
        ranked_roots = {candidates[test] for test in included}
        route_states = defaultdict(int)
        for root in sorted(ranked_roots):
            edges = routes.get(root, set())
            known = bool(edges)
            state = "fallback" if fallback else "direta_jdeps" if known else "sem_evidencia_rota"
            route_states[state] += sum(candidates[test] == root for test in included)
            output["rotas"].append((sha, root, str(root in pure_roots).lower(), "true",
                                   str(fallback).lower(), "|".join(sorted(edges)),
                                   graph_hash if known else "", state))

        ref = f"{DEST}/manifesto.json#posicao-{pos:03}"
        for test in sorted(candidates):
            selected = test in included
            reason = "fallback" if fallback else "dependency" if selected else "no_dependency"
            output["selection"].append((sha, "T1", test, str(selected).lower(), reason, ref))
        for rank, test in enumerate(sorted(included), 1):
            output["rankings"].append((sha, "T1", test, rank, "", ref))
        phase_ns = {}
        selection_ms = ""
        if pos in current:
            phases = ("arvore_reuso", "dirts", "selo", "inventario_jdeps", "selecao", "expansao", "reuso_test",
                      "arvore_t0", "t0_test")
            phase_ns = {name: run["fases"][f"{name}_{pos}"]["ns"] for name in phases}
            if pos == 49:
                phase_ns["inicializacao"] = run["ns_inicio"]
            selection_ns = sum(value for phase, value in phase_ns.items()
                               if phase not in {"reuso_test", "arvore_t0", "t0_test"})
            selection_ms = (selection_ns + 500000) // 1000000
        output["overhead"].append((sha, "T1", "selection", "measured" if phase_ns else "unknown",
                                   selection_ms, ref))
        output["cobertura"].append((pos, sha, parent, partition, str(pos == 96).lower(), "congelado",
                                    continuity, len(candidates), len(pure), len(included), str(fallback).lower()))
        locator = f"posicao-{pos:03}"
        entries[locator] = {
            "posicao": pos, "sha": sha, "pai": parent, "particao": partition, "holdout": pos == 96,
            "continuidade": continuity, "fallback_integral": fallback, "diff_nome_status": diff,
            "candidatos": len(candidates), "selecionados": len(included), "dirts_puro": len(pure),
            "rotas_por_metodo": dict(route_states), "fases_medidas_ns": phase_ns,
            "sha256_conjuntos": {k: hash_set(v) for k, v in (("t0", candidates), ("dirts", pure), ("t1", included))},
            "entradas": [{"caminho_workspace": path.resolve().relative_to(HERE.parents[2]).as_posix(),
                          "sha256": hash_file(path)} for path in (tsv, pure_file, *evidence)],
        }
    out.mkdir(parents=True)
    (out / ".gitattributes").write_bytes(b"*.csv -text\n*.json -text\n")
    for name in FIELDS:
        write_csv(out / f"{name}.csv", output[name], name)
    manifest = {
        "contrato": "0.1.0", "seletor": VERSION, "veredito": VERDICT,
        "ordem": "commit_order KAN-10, test_id crescente ordinal, score vazio em T1",
        "politica": "uniao DIRTS com dependentes diretos de bytecode de Java de producao; sem filtro textual",
        "fallback": "inventario integral em configuracao ou selecao indisponivel; recuperar estado do pai antes do fallback se viavel",
        "reuso": "somente estado selado do primeiro pai; reancorar quando indisponivel; sem interpolar lacunas",
        "referencias": {"T0": "inventario por SHA, execucao fisica nas posicoes 49 e 50",
                        "DIRTS_puro": "conjuntos de referencia com hashes e contagens por posicao"},
        "ordem_validada": {"revisoes": 100, "vinculos_consecutivos": 99, "sha256_kan10": hash_file(archive)},
        "ambiente_reuso": {"imagem": IMAGE, "dirts_commit": "62efcec2f909f93fffdd4ae1da24b0aee1071749"},
        "ambiente_legado": {"imagem_base_piloto": comparison["imagem_piloto"],
                           "dirts_commit": comparison["dirts_commit"]},
        "custo": "selection inclui inicializacao no primeiro alvo e preparo ate lista pronta; execucao e T0 em fases brutas; piloto legado sem tempo comparavel",
        "holdout": {"posicao": 96, "rotulos_lidos": False},
        "saidas_sha256": {f"{name}.csv": hash_file(out / f"{name}.csv") for name in FIELDS},
        "codigo_sha256_lf": digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "revisoes": entries,
    }
    (out / "manifesto.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
