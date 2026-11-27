"""Replay serial de T0–T3 segundo KAN-15 0.1.0 e KAN-24."""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path


PERCENTUAIS = (25, 50, 75)
FASES = {"T0": (), "T1": ("selection",),
         "T2": ("selection", "features", "inference"),
         "T3": ("selection", "features", "inference")}


def indexar(pasta, tabela, *chaves):
    indice = {}
    with (pasta / f"{tabela}.csv").open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            chave = tuple(linha[campo] for campo in chaves)
            if chave in indice:
                raise ValueError(f"{tabela}: chave duplicada {chave}")
            indice[chave] = linha
    return indice


def ms(valor):
    if valor is None or valor == "":
        return None
    numero = int(valor)
    if str(numero) != str(valor) or not 0 <= numero < 2**63:
        raise ValueError(f"duração inválida: {valor}")
    return numero


def referencia(commits, tentativas, manifesto, sha, alvo):
    ordem = int(commits[sha,]["commit_order"])
    anteriores = sorted(
        ((int(c["commit_order"]), s) for (s,), c in commits.items()
         if int(c["commit_order"]) < ordem), reverse=True)
    for posicao, candidato in anteriores:
        tentativa = tentativas.get((candidato,), {})
        origem = manifesto.get(candidato, {})
        duracao = ms(tentativa.get("suite_duration_ms"))
        if (tentativa.get("run_status") == "complete" and duracao
                and origem.get("attempt") and origem.get("available_at")
                and datetime.fromisoformat(origem["available_at"])
                < datetime.fromisoformat(alvo["cutoff"])
                and origem.get("configuration")
                and origem["configuration"] == alvo["configuration"]):
            return {"commit_sha": candidato, "commit_order": posicao,
                    "suite_duration_ms": duracao, "source_ref": tentativa["source_ref"],
                    **{campo: origem[campo] for campo in
                       ("attempt", "available_at", "configuration")}}
    return None


def cronograma(ordem, resultados, custos, maior_limite):
    eventos = []
    for nome, custo, origem in custos:
        if custo is None:
            return eventos, 0, {"reason": nome, "source_ref": origem}
    acumulado = sum(custo for _, custo, _ in custos)
    inicio = acumulado
    if acumulado > maior_limite:
        return eventos, inicio, None
    if ordem is None:
        return eventos, inicio, {"reason": "order_unavailable", "after_ms": acumulado}
    for teste in ordem:
        resultado = resultados.get(teste)
        if resultado and resultado["outcome"] == "skip":
            continue
        duracao = ms(resultado["duration_ms"]) if resultado else None
        if duracao is None:
            return eventos, inicio, {
                "reason": "duration_unavailable" if resultado else "result_unavailable",
                "test_id": teste, "after_ms": acumulado,
                "source_ref": resultado["source_ref"] if resultado else None,
            }
        acumulado += duracao
        if acumulado > maior_limite:
            break
        eventos.append({"test_id": teste, "completed_at_ms": acumulado,
                        "outcome": resultado["outcome"],
                        "source_ref": resultado["source_ref"]})
    return eventos, inicio, None


def ordem_t0(tentativa, resultados):
    if tentativa.get("run_status") != "complete" or not resultados:
        return None
    executados = {t: r for t, r in resultados.items() if r["outcome"] != "skip"}
    posicoes = [int(r["execution_order"]) for r in executados.values()
                if r["execution_order"]]
    if len(posicoes) != len(executados) or any(p < 1 for p in posicoes):
        return None
    if len(set(posicoes)) != len(posicoes):
        raise ValueError("T0: posições globais duplicadas")
    return sorted(executados, key=lambda t: int(executados[t]["execution_order"]))


def ordem_ranking(sha, cenario, alvo, selecionados, rankings):
    if not alvo.get("selection_ref") or cenario not in alvo.get("ranking_refs", {}):
        return None
    linhas = [(int(r["rank"]), t) for (s, c, t), r in rankings.items()
              if (s, c) == (sha, cenario)]
    linhas.sort()
    if ({t for _, t in linhas} != selecionados
            or [p for p, _ in linhas] != list(range(1, len(linhas) + 1))):
        raise ValueError(f"{sha} {cenario}: ranking diverge da seleção ou tem posições inválidas")
    return [t for _, t in linhas]


def custos_cenario(sha, cenario, alvo, overhead):
    preparo = alvo.get("startup", {}).get(cenario, {})
    custos = [("startup_unavailable", ms(preparo.get("duration_ms", "")),
               preparo.get("source_ref"))]
    for fase in FASES[cenario]:
        linha = overhead.get((sha, cenario, fase), {})
        valor = ms(linha["duration_ms"]) if linha.get("measurement_status") == "measured" else None
        if fase == "selection" and cenario != "T1" and linha:
            base = overhead.get((sha, "T1", fase), {})
            campos = ("measurement_status", "duration_ms", "source_ref")
            if any(linha[k] != base.get(k) for k in campos):
                raise ValueError(f"{sha} {cenario}: overhead de seleção diverge de T1")
        custos.append((f"{fase}_unavailable", valor, linha.get("source_ref")))
    return custos


def simular(pasta):
    manifesto = json.loads((pasta / "manifesto.json").read_text(encoding="utf-8"))
    if manifesto["contract_version"] != "0.1.0":
        raise ValueError("versão de contrato incompatível")
    commits = indexar(pasta, "commits", "commit_sha")
    tentativas = indexar(pasta, "t0_runs", "commit_sha")
    selecao = indexar(pasta, "selection", "commit_sha", "scenario", "test_id")
    rankings = indexar(pasta, "rankings", "commit_sha", "scenario", "test_id")
    overhead = indexar(pasta, "overhead", "commit_sha", "scenario", "phase")
    oraculo = indexar(pasta, "t0_results", "commit_sha", "test_id")
    saida = []
    for sha, alvo in sorted(manifesto["targets"].items(),
                            key=lambda item: int(commits[item[0],]["commit_order"])):
        commit = commits[sha,]
        if commit["eligibility_status"] != "eligible":
            continue
        ref = referencia(commits, tentativas, manifesto["references"], sha, alvo)
        limites = [p * ref["suite_duration_ms"] // 100 if ref else None for p in PERCENTUAIS]
        selecionados = {t for (s, c, t), r in selecao.items()
                        if (s, c) == (sha, "T1") and r["selected"] == "true"}
        ordens = {c: ordem_ranking(sha, c, alvo, selecionados, rankings)
                  for c in ("T1", "T2", "T3")}
        tentativa = tentativas.get((sha,), {})
        resultados = {t: r for (s, t), r in oraculo.items() if s == sha}
        ordens["T0"] = ordem_t0(tentativa, resultados)
        for cenario in FASES:
            custos = custos_cenario(sha, cenario, alvo, overhead)
            treino = overhead.get((sha, cenario, "training"))
            if ref:
                eventos, inicio, lacuna = cronograma(ordens[cenario], resultados, custos, limites[-1])
            else:
                eventos, inicio, lacuna = [], None, {"reason": "historical_reference_unavailable"}
            for percentual, limite in zip(PERCENTUAIS, limites):
                indisponivel = lacuna and (
                    "after_ms" not in lacuna or lacuna["after_ms"] <= limite)
                prefixo = None if indisponivel else [
                    e for e in eventos if e["completed_at_ms"] <= limite]
                saida.append({
                    "commit_sha": sha, "commit_order": int(commit["commit_order"]),
                    "scenario": cenario, "percent": percentual, "budget_ms": limite,
                    "cutoff": alvo["cutoff"], "reference": ref,
                    "t0_current": tentativa or None,
                    "training": treino,
                    "pre_test_ms": inicio if all(c is not None for _, c, _ in custos) else None,
                    "costs": [{"phase": n.removesuffix("_unavailable"), "duration_ms": d,
                               "source_ref": r} for n, d, r in custos],
                    "decision_refs": {"selection": alvo.get("selection_ref"),
                                      "ranking": alvo.get("ranking_refs", {}).get(cenario)}
                    if cenario != "T0" else None,
                    "status": "unavailable" if indisponivel else "available",
                    "gap": lacuna if indisponivel else None, "prefix": prefixo,
                })
    return {"contract_version": manifesto["contract_version"],
            "data_kind": manifesto["data_kind"], "cuts": saida}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path)
    args = parser.parse_args()
    print(json.dumps(simular(args.inputs), ensure_ascii=True, indent=2))
