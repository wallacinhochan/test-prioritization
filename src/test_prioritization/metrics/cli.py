"""Calcula RQ1, RQ2 e APFDc com os CSVs KAN-15 e a saída KAN-23."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from .apfdc import apfdc
from .detection import deteccao


REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCIAS = REPO_ROOT / "evidencias"


FASES = {"T0": (), "T1": ("selection",),
         "T2": ("selection", "features", "inference"),
         "T3": ("selection", "features", "inference")}
PERCENTUAIS = (25, 50, 75)


def ler(pasta, tabela, *chave):
    linhas = {}
    with (pasta / f"{tabela}.csv").open(encoding="utf-8-sig", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            id_linha = tuple(linha[campo] for campo in chave)
            if id_linha in linhas:
                raise ValueError(f"{tabela}: chave repetida {id_linha}")
            linhas[id_linha] = linha
    return linhas


def ms(valor):
    if valor is None or valor == "":
        return None
    numero = int(valor)
    if str(numero) != str(valor) or numero < 0:
        raise ValueError(f"duração inválida: {valor}")
    return numero


def ordem_ranking(sha, cenario, alvo, selecionados, rankings):
    if selecionados is None or not alvo.get("ranking_refs", {}).get(cenario):
        return None
    linhas = sorted((int(r["rank"]), t) for (s, c, t), r in rankings.items()
                    if (s, c) == (sha, cenario))
    if ({t for _, t in linhas} != selecionados
            or [p for p, _ in linhas] != list(range(1, len(linhas) + 1))):
        return None
    return [t for _, t in linhas]


def validar_referencia(ref, alvo, ordem, commits, runs, manifesto):
    if ref is None:
        return
    sha = ref["commit_sha"]
    run = runs[sha,]
    origem = manifesto["references"][sha]
    if (int(commits[sha,]["commit_order"]) != ref["commit_order"]
            or ref["commit_order"] >= ordem or run["run_status"] != "complete"
            or not ms(run["suite_duration_ms"])
            or ref["suite_duration_ms"] != ms(run["suite_duration_ms"])
            or ref["source_ref"] != run["source_ref"]
            or not ref["attempt"]
            or any(ref[campo] != origem[campo] for campo in
                   ("attempt", "available_at", "configuration"))
            or not ref["configuration"] or ref["configuration"] != alvo["configuration"]
            or datetime.fromisoformat(ref["available_at"]) >= datetime.fromisoformat(alvo["cutoff"])):
        raise ValueError("referência histórica incompatível")


def tradeoff(cenario, selecionados, resultados, falhas, t0, corte):
    executados = {t for t, (estado, _) in resultados.items() if estado != "skip"}
    n_t0 = len(executados) if falhas is not None else None
    comparavel = (falhas is not None and selecionados is not None
                  and selecionados <= resultados.keys())
    populacao = selecionados & executados if comparavel else None
    n_selecionados = len(populacao) if populacao is not None else None
    detectadas = len(populacao & falhas) if comparavel else None
    fases = {fase: {"duration_ms": None if fase in FASES[cenario] else 0,
                    "status": "unknown" if fase in FASES[cenario] else "not_applicable"}
             for fase in ("selection", "features", "inference")}
    preparo = None
    for custo in corte["costs"]:
        duracao = ms(custo["duration_ms"])
        if custo["phase"] == "startup":
            preparo = duracao
        else:
            fases[custo["phase"]] = {
                "duration_ms": duracao, "source_ref": custo["source_ref"],
                "status": "measured" if duracao is not None else "unknown",
            }
    duracoes = [resultados[t][1] for t in populacao] if comparavel else []
    testes_ms = sum(duracoes) if comparavel and None not in duracoes else None
    parede_t0 = ms(t0.get("suite_duration_ms")) if falhas is not None else None
    parcelas = [preparo, testes_ms] + [fase["duration_ms"] for fase in fases.values()]
    if cenario == "T0":
        total = parede_t0
        tipo_total = "parede_t0_observada"
        motivo_tempo = None if total is not None else "parede_t0_indisponivel"
    else:
        total = sum(parcelas) if None not in parcelas else None
        tipo_total = "estimativa_serial"
        motivo_tempo = (None if total is not None else
                        "populacao_indisponivel_ou_nao_comparavel" if not comparavel else
                        "custo_indisponivel")
    treino = corte["training"]
    return {
        "cenario": cenario, "tempo_total_ms": total, "tipo_tempo_total": tipo_total,
        "motivo_tempo": motivo_tempo, "execucao_metodos_ms": testes_ms,
        "preparo_ms": preparo, "overhead": fases,
        "treinamento": treino,
        "estado_treinamento": (treino["measurement_status"] if treino else
                               "sem_evento_registrado" if cenario in ("T2", "T3") else "not_applicable"),
        "treinamento_ms": ms(treino["duration_ms"]) if treino and
        treino["measurement_status"] == "measured" else None,
        "testes_t0": n_t0, "testes_selecionados": n_selecionados,
        "testes_selecionados_brutos": len(selecionados) if selecionados is not None else None,
        "reducao": (n_t0 - n_selecionados) / n_t0 if comparavel and n_t0 else None,
        "falhas_t0": len(falhas) if falhas is not None else None,
        "detectadas": detectadas, "proporcao": detectadas / len(falhas) if comparavel and falhas else None,
        "motivo_populacao": None if comparavel else
        "oraculo_incompleto" if falhas is None else
        "selecao_indisponivel" if selecionados is None else "populacao_nao_comparavel",
    }


def avaliar(pasta, replay):
    manifesto = json.loads((pasta / "manifesto.json").read_text(encoding="utf-8-sig"))
    if (manifesto["contract_version"] != "0.1.0"
            or any(replay[campo] != manifesto[campo] for campo in ("data_kind", "contract_version"))):
        raise ValueError("manifesto e replay incompatíveis")
    commits = ler(pasta, "commits", "commit_sha")
    runs = ler(pasta, "t0_runs", "commit_sha")
    oraculo = ler(pasta, "t0_results", "commit_sha", "test_id")
    selecao = ler(pasta, "selection", "commit_sha", "scenario", "test_id")
    rankings = ler(pasta, "rankings", "commit_sha", "scenario", "test_id")
    alvos = {sha: alvo for sha, alvo in manifesto["targets"].items()
             if commits[sha,]["eligibility_status"] == "eligible"}
    cortes = {}
    for corte in replay["cuts"]:
        chave = (corte["commit_sha"], corte["scenario"], corte["percent"])
        if chave in cortes:
            raise ValueError(f"corte repetido: {chave}")
        cortes[chave] = corte
    esperados = {(sha, c, p) for sha in alvos for c in FASES for p in PERCENTUAIS}
    if cortes.keys() != esperados:
        raise ValueError("replay não cobre exatamente os alvos elegíveis por cenário e percentual")

    revisoes = []
    for sha in sorted(alvos, key=lambda s: int(commits[s,]["commit_order"])):
        alvo = alvos[sha]
        ordem_commit = int(commits[sha,]["commit_order"])
        t0 = runs.get((sha,), {})
        resultados = {t: (r["outcome"], ms(r["duration_ms"]))
                      for (s, t), r in oraculo.items() if s == sha}
        if any(estado not in ("pass", "fail", "skip") for estado, _ in resultados.values()):
            raise ValueError(f"{sha}: desfecho inválido no T0")
        falhas = ({t for t, (estado, _) in resultados.items() if estado == "fail"}
                  if t0.get("run_status") == "complete" and resultados else None)
        selecionados = ({t for (s, c, t), r in selecao.items()
                         if s == sha and c == "T1" and r["selected"] == "true"}
                        if alvo.get("selection_ref") else None)
        ordens = {c: ordem_ranking(sha, c, alvo, selecionados, rankings)
                  for c in ("T1", "T2", "T3")}
        tradeoffs = []
        deteccoes = []
        ref = cortes[sha, "T0", 25]["reference"]
        validar_referencia(ref, alvo, ordem_commit, commits, runs, manifesto)
        for p in PERCENTUAIS:
            grupo = [cortes[sha, c, p] for c in FASES]
            limite = p * ref["suite_duration_ms"] // 100 if ref else None
            for corte in grupo:
                c = corte["scenario"]
                if (corte["budget_ms"] != limite or corte["reference"] != ref
                        or corte["t0_current"] != (t0 or None) or corte["cutoff"] != alvo["cutoff"]
                        or corte["commit_order"] != ordem_commit
                        or corte["status"] not in ("available", "unavailable")
                        or (corte["status"] == "available") != (corte["prefix"] is not None)):
                    raise ValueError(f"{sha} {c} {p}: corte incompatível")
                base = cortes[sha, c, 25]
                if any(corte[campo] != base[campo] for campo in
                       ("costs", "training", "decision_refs")):
                    raise ValueError(f"{sha} {c}: custos ou decisões divergem entre cortes")
                if c != "T0" and ordens[c] is not None and corte["prefix"] is not None:
                    esperados = [t for t in ordens[c] if resultados.get(t, (None,))[0] != "skip"]
                    if [e["test_id"] for e in corte["prefix"]] != esperados[:len(corte["prefix"])]:
                        raise ValueError(f"{sha} {c}: prefixo diverge do ranking")
                for evento in corte["prefix"] or []:
                    teste = evento["test_id"]
                    if (teste not in resultados or resultados[teste][0] != evento["outcome"]
                            or evento["outcome"] == "skip"):
                        raise ValueError(f"{sha} {c}: evento não associado a execução no T0")
                deteccoes.append(deteccao(corte, falhas))
                if p == PERCENTUAIS[0]:
                    populacao = set(resultados) if c == "T0" else selecionados
                    tradeoffs.append(tradeoff(c, populacao, resultados, falhas, t0, corte))
        for c in FASES:
            validos = [cortes[sha, c, p] for p in PERCENTUAIS
                       if cortes[sha, c, p]["prefix"] is not None]
            for menor, maior in zip(validos, validos[1:]):
                if menor["prefix"] != [e for e in maior["prefix"]
                                       if e["completed_at_ms"] <= menor["budget_ms"]]:
                    raise ValueError(f"{sha} {c}: prefixos divergem entre cortes")
        revisoes.append({"commit_sha": sha, "commit_order": ordem_commit,
                         "configuracao_declarada": alvo["configuration"],
                         "rq1": tradeoffs, "rq2": deteccoes,
                         "apfdc": apfdc(ordens, selecionados, resultados, falhas)})

    cobertura = {}
    for p in PERCENTUAIS:
        comuns, lacunas = [], {}
        for revisao in revisoes:
            sha = revisao["commit_sha"]
            motivos = {c["scenario"]: c["motivo"] for c in revisao["rq2"]
                       if c["percent"] == p and c["motivo"]}
            if motivos:
                lacunas[sha] = motivos
            else:
                comuns.append(sha)
        cobertura[p] = {"alvos_elegiveis": len(revisoes), "comuns": comuns, "lacunas": lacunas}
    return {"contract_version": replay["contract_version"], "data_kind": replay["data_kind"],
            "modo": "replay_serial", "revisoes": revisoes, "cobertura_rq2": cobertura,
            "elegiveis_fora_do_manifesto": sorted(sha for (sha,), c in commits.items()
                                                 if c["eligibility_status"] == "eligible"
                                                 and sha not in alvos)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, help="CSV KAN-15 e manifesto KAN-23")
    parser.add_argument("replay", type=Path, help="JSON de cortes produzido pela KAN-23")
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text(encoding="utf-8-sig"))
    print(json.dumps(avaliar(args.inputs, replay), ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
