"""Confere os insumos congelados da revisão 50 sem materializar um replay oficial."""

import argparse
import csv
import hashlib
import io
import json
import subprocess


SHA = "f24c027ff83b90beab2ec28696721200abb4f9e9"
T1 = "ef577158bc012d87784bbfab1b9ccb4ee80cf812"
RANKINGS = "a06d381c7a9e0fc896e7c5ae84d94a452eedc56a"
AVALIACAO = "d2c0e7ad276dd567d8e063306ebbf23662d51866"
PASTA_T1 = "evidencias/KAN-18/congelado-expansao-v1"
PASTA_RANKINGS = "evidencias/KAN-19/expansao50-experimental-v1"


def auditar(repo):
    hashes = {}

    def ler(commit, caminho):
        spec = f"{commit}:{caminho}"
        dados = subprocess.check_output(["git", "-C", repo, "show", spec])
        hashes[spec] = hashlib.sha256(dados).hexdigest()
        return dados.decode("utf-8")

    def linhas(commit, pasta, arquivo):
        return [r for r in csv.DictReader(io.StringIO(ler(commit, f"{pasta}/{arquivo}.csv")))
                if r["commit_sha"] == SHA]

    manifesto = json.loads(ler(RANKINGS, f"{PASTA_RANKINGS}/manifesto.json"))
    manifesto_t1 = f"{PASTA_T1}/manifesto.json"
    ler(T1, manifesto_t1)
    if (manifesto["sha"] != SHA or manifesto["posicao"] != 50
            or manifesto["publicacao_t1"] != T1
            or manifesto["manifesto_t1_sha256"] != hashes[f"{T1}:{manifesto_t1}"]):
        raise ValueError("proveniência dos rankings divergente")
    selecao = linhas(T1, PASTA_T1, "selection")
    selecionados = {r["test_id"] for r in selecao if r["selected"] == "true"}
    if (len(selecionados) != manifesto["selecionados"]
            or len(selecao) != len({r["test_id"] for r in selecao})
            or any(r["scenario"] != "T1" or r["selected"] not in {"true", "false"}
                   for r in selecao)):
        raise ValueError("população da seleção divergente")
    ordenados = linhas(T1, PASTA_T1, "rankings") + linhas(RANKINGS, PASTA_RANKINGS, "rankings")
    for cenario in ("T1", "T2", "T3"):
        ranking = [r for r in ordenados if r["scenario"] == cenario]
        if ({r["test_id"] for r in ranking} != selecionados
                or sorted(int(r["rank"]) for r in ranking) != list(range(1, len(selecionados) + 1))):
            raise ValueError(f"ranking divergente: {cenario}")
    overhead = linhas(RANKINGS, PASTA_RANKINGS, "overhead")
    ler(AVALIACAO, "evidencias/KAN-19/avaliacao-expansao50.json")
    return {"commit_sha": SHA, "selected": len(selecionados), "sha256": hashes,
            "fractional_overhead_rows": sum("." in r["duration_ms"] for r in overhead),
            "official_replay": "blocked",
            "required": ["global_t0_trace_reconciled_with_reference",
                         "prior_comparable_t0_published_before_cutoff",
                         "comparable_complete_phase_measurements",
                         "validated_model_update_and_frozen_decisions"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    args = parser.parse_args()
    print(json.dumps(auditar(args.repo), indent=2))
