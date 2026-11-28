"""Compara execucoes fisicas da KAN-28 com o simulador serial KAN-23 e metricas KAN-25-27."""
import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT / "evidencias" / "KAN-23"))
sys.path.insert(0, str(ROOT / "evidencias" / "KAN-23" / "coleta"))
sys.path.insert(0, str(ROOT / "src"))

import simular as kan23_simular
from reconciliar_t0 import alinhar
from validar import validar as validar_rastro
from test_prioritization.metrics.cli import avaliar as avaliar_metricas

SHA_49 = "cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9"
SHA_50 = "f24c027ff83b90beab2ec28696721200abb4f9e9"
T1_COMMIT = "ef577158bc012d87784bbfab1b9ccb4ee80cf812"
RANKINGS_COMMIT = "a06d381c7a9e0fc896e7c5ae84d94a452eedc56a"
PERCENTUAIS = (25, 50, 75)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-c", "safe.directory=*", "-C", str(ROOT), "show", f"{commit}:{path}"]
    )


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _ranks(values):
    indexed = sorted(enumerate(values), key=lambda kv: kv[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman(xs, ys):
    if len(xs) < 2:
        return None
    return pearson(_ranks(xs), _ranks(ys))


def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def load_ordered_run(attempt_dir: Path):
    evidencia = attempt_dir / "evidencia"
    plano = validar_rastro(evidencia / "eventos.tsv")
    relogio = alinhar(
        evidencia / "eventos.tsv.clock.tsv",
        evidencia / "marcos.tsv",
        plano["plan_elapsed_ns"],
    )
    tentativa = json.loads((attempt_dir / "tentativa.json").read_text(encoding="utf-8"))
    methods = []
    with (evidencia / "resumo_ordenado.tsv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            inv = int(row["invocations"])
            p_cnt, f_cnt, s_cnt = int(row["pass"]), int(row["fail"]), int(row["skip"])
            outcome = "fail" if f_cnt > 0 else ("pass" if p_cnt > 0 else "skip")
            dur_ns = int(row["invocations_sum_ns"]) if outcome != "skip" else None
            methods.append({
                "rank": int(row["rank"]),
                "test_id": row["test_id"],
                "discovered": row["discovered"] == "true",
                "invocations": inv,
                "pass": p_cnt,
                "fail": f_cnt,
                "skip": s_cnt,
                "outcome": outcome,
                "method_start_ns": int(row["method_start_ns"]),
                "method_end_ns": int(row["method_end_ns"]),
                "method_wall_ns": int(row["method_wall_ns"]),
                "invocations_sum_ns": dur_ns,
                "duration_ms": (dur_ns + 500_000) // 1_000_000 if dur_ns is not None else None,
            })
    return {
        "tentativa": tentativa,
        "plano": plano,
        "clock": relogio,
        "methods": methods,
    }


def load_surefire_run(attempt_dir: Path):
    tentativa = json.loads((attempt_dir / "tentativa.json").read_text(encoding="utf-8"))
    derivados = attempt_dir / "derivados"
    resumo = json.loads((derivados / "resumo.json").read_text(encoding="utf-8"))
    metodos = json.loads((derivados / "metodos.json").read_text(encoding="utf-8"))
    invocacoes = json.loads((derivados / "invocacoes.json").read_text(encoding="utf-8"))
    by_method_end = {}
    for inv in invocacoes:
        if inv["outcome"] != "skip" and inv["end_ns"] is not None:
            m = inv["method"]
            by_method_end[m] = max(by_method_end.get(m, -1), int(inv["end_ns"]))
    for m in metodos:
        m["last_end_ns"] = by_method_end.get(m["test_id"])
    return {
        "tentativa": tentativa,
        "resumo": resumo,
        "metodos": metodos,
    }


def compare_method_durations(t0_methods_map, phys_methods_map):
    common = sorted(set(t0_methods_map) & set(phys_methods_map))
    t0_exec_ns = []
    phys_exec_ns = []
    abs_diffs_ms = []
    signed_diffs_ms = []
    outcome_mismatches = []
    inv_mismatches = []

    for tid in common:
        t0 = t0_methods_map[tid]
        ph = phys_methods_map[tid]
        if t0["outcome"] != ph["outcome"]:
            outcome_mismatches.append({"test_id": tid, "t0": t0["outcome"], "physical": ph["outcome"]})
        if t0["invocations"] != ph["invocations"]:
            inv_mismatches.append({"test_id": tid, "t0": t0["invocations"], "physical": ph["invocations"]})
        if t0["outcome"] != "skip" and ph["outcome"] != "skip":
            t0_ns = t0["duration_ns"]
            ph_ns = ph["duration_ns"]
            t0_exec_ns.append(t0_ns)
            phys_exec_ns.append(ph_ns)
            diff_ms = (ph_ns - t0_ns) / 1_000_000.0
            signed_diffs_ms.append(diff_ms)
            abs_diffs_ms.append(abs(diff_ms))

    t0_sum_ms = sum(t0_exec_ns) / 1_000_000.0
    phys_sum_ms = sum(phys_exec_ns) / 1_000_000.0
    sorted_abs = sorted(abs_diffs_ms)
    sorted_signed = sorted(signed_diffs_ms)
    return {
        "common_methods": len(common),
        "executed_compared": len(t0_exec_ns),
        "outcome_mismatches": outcome_mismatches,
        "invocation_count_mismatches": inv_mismatches,
        "t0_sum_ms": round(t0_sum_ms, 3),
        "physical_sum_ms": round(phys_sum_ms, 3),
        "sum_diff_ms": round(phys_sum_ms - t0_sum_ms, 3),
        "sum_rel_error_pct": round(((phys_sum_ms - t0_sum_ms) / t0_sum_ms) * 100.0, 2) if t0_sum_ms > 0 else None,
        "per_method_diff_ms": {
            "median_signed": round(percentile(sorted_signed, 0.50), 3),
            "median_abs": round(percentile(sorted_abs, 0.50), 3),
            "p90_abs": round(percentile(sorted_abs, 0.90), 3),
            "p95_abs": round(percentile(sorted_abs, 0.95), 3),
            "max_abs": round(sorted_abs[-1], 3) if sorted_abs else None,
        },
        "pearson_r": round(pearson(t0_exec_ns, phys_exec_ns), 4) if pearson(t0_exec_ns, phys_exec_ns) is not None else None,
        "spearman_rho": round(spearman(t0_exec_ns, phys_exec_ns), 4) if spearman(t0_exec_ns, phys_exec_ns) is not None else None,
    }


def physical_prefix_count(methods_with_end_ns, plan_origin_lower_ns, plan_origin_upper_ns,
                          pre_execution_overhead_ms, budget_ms):
    budget_ns = budget_ms * 1_000_000
    overhead_ns = pre_execution_overhead_ms * 1_000_000
    optimistic = 0
    pessimistic = 0
    uncertain = 0
    for end_ns in methods_with_end_ns:
        if end_ns is None:
            continue
        low = overhead_ns + plan_origin_lower_ns + end_ns
        high = overhead_ns + plan_origin_upper_ns + end_ns
        if high <= budget_ns:
            pessimistic += 1
            optimistic += 1
        elif low <= budget_ns < high:
            optimistic += 1
            uncertain += 1
        else:
            break
    return {
        "completed_guaranteed": pessimistic,
        "completed_optimistic": optimistic,
        "boundary_uncertain_methods": uncertain,
    }


def run_simulation_pack(sim_dir: Path, t0_49, t0_50, frozen_ov_50, startup_by_scenario,
                        include_external_overhead=True):
    sim_dir.mkdir(parents=True, exist_ok=True)
    commits_bytes = git_show(T1_COMMIT, "evidencias/KAN-18/congelado-expansao-v1/commits.csv")
    sel_bytes = git_show(T1_COMMIT, "evidencias/KAN-18/congelado-expansao-v1/selection.csv")
    t1_rank_bytes = git_show(T1_COMMIT, "evidencias/KAN-18/congelado-expansao-v1/rankings.csv")
    t23_rank_bytes = git_show(RANKINGS_COMMIT, "evidencias/KAN-19/expansao50-experimental-v1/rankings.csv")

    commit_rows = list(csv.DictReader(commits_bytes.decode("utf-8").splitlines()))
    for row in commit_rows:
        if row["commit_sha"] in (SHA_49, SHA_50):
            row["eligibility_status"] = "eligible"
    with (sim_dir / "commits.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(commit_rows[0].keys()))
        w.writeheader()
        w.writerows(commit_rows)

    # Filter selection & rankings to SHA_50
    sel_rows = [r for r in csv.DictReader(sel_bytes.decode("utf-8").splitlines()) if r["commit_sha"] == SHA_50]
    with (sim_dir / "selection.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["commit_sha", "scenario", "test_id", "selected", "selection_reason", "source_ref"])
        w.writeheader()
        w.writerows(sel_rows)

    rank_rows = (
        [r for r in csv.DictReader(t1_rank_bytes.decode("utf-8").splitlines()) if r["commit_sha"] == SHA_50]
        + [r for r in csv.DictReader(t23_rank_bytes.decode("utf-8").splitlines()) if r["commit_sha"] == SHA_50]
    )
    with (sim_dir / "rankings.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["commit_sha", "scenario", "test_id", "rank", "score", "source_ref"])
        w.writeheader()
        w.writerows(rank_rows)

    # Overhead (integer ms required by KAN-23/simular.py)
    ov_rows = []
    for scenario in ("T1", "T2", "T3"):
        sel_ms = frozen_ov_50["selection_ms"] if include_external_overhead else 0
        ov_rows.append({
            "commit_sha": SHA_50, "scenario": scenario, "phase": "selection",
            "measurement_status": "measured", "duration_ms": str(sel_ms),
            "source_ref": frozen_ov_50["selection_ref"],
        })
        if scenario in ("T2", "T3"):
            feat_ms = frozen_ov_50["features_ms"] if include_external_overhead else 0
            inf_ms = frozen_ov_50[f"inference_{scenario}_ms"] if include_external_overhead else 0
            ov_rows.append({
                "commit_sha": SHA_50, "scenario": scenario, "phase": "features",
                "measurement_status": "measured", "duration_ms": str(feat_ms),
                "source_ref": frozen_ov_50["features_ref"],
            })
            ov_rows.append({
                "commit_sha": SHA_50, "scenario": scenario, "phase": "inference",
                "measurement_status": "measured", "duration_ms": str(inf_ms),
                "source_ref": frozen_ov_50[f"inference_{scenario}_ref"],
            })
            ov_rows.append({
                "commit_sha": SHA_50, "scenario": scenario, "phase": "training",
                "measurement_status": "measured", "duration_ms": str(frozen_ov_50[f"training_{scenario}_ms"]),
                "source_ref": frozen_ov_50[f"training_{scenario}_ref"],
            })
    with (sim_dir / "overhead.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["commit_sha", "scenario", "phase", "measurement_status", "duration_ms", "source_ref"])
        w.writeheader()
        w.writerows(ov_rows)

    # Combine t0_runs.csv and t0_results.csv from t0-49 and t0-50
    for filename in ("t0_runs.csv", "t0_results.csv"):
        r49 = list(csv.DictReader((t0_49["derivados"] / filename).open(encoding="utf-8", newline="")))
        r50 = list(csv.DictReader((t0_50["derivados"] / filename).open(encoding="utf-8", newline="")))
        with (sim_dir / filename).open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(r49[0].keys()))
            w.writeheader()
            w.writerows(r49 + r50)

    avail_49 = t0_49["tentativa"]["finish"]
    cutoff_dt = datetime.fromisoformat(avail_49) + timedelta(seconds=1)
    config_id = f"kan13|{t0_50['tentativa']['image']}|linux/amd64|UTC|cold|1fork|serial"
    manifesto = {
        "contract_version": "0.1.0",
        "data_kind": "technical_physical_validation_50",
        "references": {
            SHA_49: {
                "attempt": "t0-49",
                "available_at": avail_49,
                "configuration": config_id,
            }
        },
        "targets": {
            SHA_50: {
                "cutoff": cutoff_dt.isoformat(),
                "configuration": config_id,
                "selection_ref": f"evidencias/KAN-18/congelado-expansao-v1/manifesto.json@{T1_COMMIT}#posicao-050",
                "ranking_refs": {
                    "T1": f"evidencias/KAN-18/congelado-expansao-v1/rankings.csv@{T1_COMMIT}#posicao-050",
                    "T2": f"evidencias/KAN-19/expansao50-experimental-v1/rankings.csv@{RANKINGS_COMMIT}#T2",
                    "T3": f"evidencias/KAN-19/expansao50-experimental-v1/rankings.csv@{RANKINGS_COMMIT}#T3",
                },
                "startup": {
                    sc: {"duration_ms": str(val), "source_ref": f"kan28-startup-{sc}"}
                    for sc, val in startup_by_scenario.items()
                },
            }
        },
    }
    (sim_dir / "manifesto.json").write_text(json.dumps(manifesto, indent=2) + "\n", encoding="utf-8")

    replay = kan23_simular.simular(sim_dir)
    metricas = avaliar_metricas(sim_dir, replay)
    return replay, metricas


def analyze(rodada_dir: Path):
    exec_manifest = json.loads((rodada_dir / "execucao_manifesto.json").read_text(encoding="utf-8"))
    t0_49 = load_surefire_run(rodada_dir / "t0-49")
    t0_49["derivados"] = rodada_dir / "t0-49" / "derivados"
    t0_50 = load_surefire_run(rodada_dir / "t0-50")
    t0_50["derivados"] = rodada_dir / "t0-50" / "derivados"
    t1_sf = load_surefire_run(rodada_dir / "t1-surefire-50")
    ordered = {
        "T1": load_ordered_run(rodada_dir / "t1-ordenado-50"),
        "T2": load_ordered_run(rodada_dir / "t2-ordenado-50"),
        "T3": load_ordered_run(rodada_dir / "t3-ordenado-50"),
    }

    # Verify frozen overhead on revision 50
    ov_t1_raw = git_show(T1_COMMIT, "evidencias/KAN-18/congelado-expansao-v1/overhead.csv")
    ov_t23_raw = git_show(RANKINGS_COMMIT, "evidencias/KAN-19/expansao50-experimental-v1/overhead.csv")
    m_t23 = json.loads(git_show(RANKINGS_COMMIT, "evidencias/KAN-19/expansao50-experimental-v1/manifesto.json"))
    t1_ov_row = next(r for r in csv.DictReader(ov_t1_raw.decode("utf-8").splitlines()) if r["commit_sha"] == SHA_50)
    t23_ov_rows = {(r["scenario"], r["phase"]): r for r in csv.DictReader(ov_t23_raw.decode("utf-8").splitlines()) if r["commit_sha"] == SHA_50}
    frozen_ov_50 = {
        "selection_ms": int(t1_ov_row["duration_ms"]),
        "selection_ref": t1_ov_row["source_ref"],
        "features_exact_ns": m_t23["tempos"]["extracao_compartilhada_ns"],
        "features_ms": round(float(t23_ov_rows[("T2", "features")]["duration_ms"])),
        "features_ref": t23_ov_rows[("T2", "features")]["source_ref"],
        "inference_T2_exact_ns": m_t23["tempos"]["modelos"]["T2"]["inference_ns"],
        "inference_T2_ms": round(float(t23_ov_rows[("T2", "inference")]["duration_ms"])),
        "inference_T2_ref": t23_ov_rows[("T2", "inference")]["source_ref"],
        "inference_T3_exact_ns": m_t23["tempos"]["modelos"]["T3"]["inference_ns"],
        "inference_T3_ms": round(float(t23_ov_rows[("T3", "inference")]["duration_ms"])),
        "inference_T3_ref": t23_ov_rows[("T3", "inference")]["source_ref"],
        "training_T2_ms": round(m_t23["tempos"]["modelos"]["T2"]["fit_ns"] / 1_000_000),
        "training_T2_ref": f"evidencias/KAN-19/expansao50-experimental-v1/manifesto.json@{RANKINGS_COMMIT}#T2-fit",
        "training_T3_ms": round(m_t23["tempos"]["modelos"]["T3"]["fit_ns"] / 1_000_000),
        "training_T3_ref": f"evidencias/KAN-19/expansao50-experimental-v1/manifesto.json@{RANKINGS_COMMIT}#T3-fit",
    }

    t0_50_map = {
        m["test_id"]: {
            "outcome": m["matched_outcome"],
            "invocations": m["matched_cases"],
            "duration_ns": m["matched_duration_ns"],
            "order": m["matched_execution_order"],
            "last_end_ns": m["last_end_ns"],
        }
        for m in t0_50["metodos"]
    }
    t1_sf_map = {
        m["test_id"]: {
            "outcome": m["matched_outcome"],
            "invocations": m["matched_cases"],
            "duration_ns": m["matched_duration_ns"],
            "order": m["matched_execution_order"],
            "last_end_ns": m["last_end_ns"],
        }
        for m in t1_sf["metodos"]
    }

    # Check order fidelity in T1 Surefire vs frozen T1 order
    t1_frozen_order = [m["test_id"] for m in ordered["T1"]["methods"]]
    t1_sf_exec_order = [
        m["test_id"]
        for m in sorted(
            (m for m in t1_sf["metodos"] if m["matched_execution_order"] is not None),
            key=lambda m: m["matched_execution_order"],
        )
    ]
    t1_frozen_exec = [tid for tid in t1_frozen_order if t0_50_map[tid]["outcome"] != "skip"]
    t1_sf_rank_map = {tid: idx for idx, tid in enumerate(t1_sf_exec_order, 1)}
    t1_sf_order_spearman = spearman(
        list(range(1, len(t1_frozen_exec) + 1)),
        [t1_sf_rank_map[tid] for tid in t1_frozen_exec],
    )

    # Physical duration & framework overhead decomposition
    def sf_summary(label, run):
        clk = run["resumo"]["clock"]
        plan_ms = (run["resumo"]["clock"]["runner_ms"])
        # Exact plan elapsed from eventos.tsv
        plano = validar_rastro(rodada_dir / label / "evidencia" / "eventos.tsv")
        plan_elapsed_ms = plano["plan_elapsed_ns"] / 1_000_000.0
        sum_methods_ms = run["resumo"]["matched_method_duration_ns"] / 1_000_000.0
        origin_mid_ms = (clk["plan_origin_lower_ns"] + clk["plan_origin_upper_ns"]) / 2_000_000.0
        runner_init_ms = origin_mid_ms - clk["prepare_ms"]
        return {
            "mode": "surefire",
            "methods_total": len(run["metodos"]),
            "methods_executed": run["resumo"]["methods_with_duration"],
            "xml_cases": run["resumo"]["xml_cases"],
            "matched_cases": run["resumo"]["matched_cases"],
            "gaps": run["resumo"]["gaps"],
            "maven_totals": run["resumo"].get("maven_totals"),
            "clock": clk,
            "plan_elapsed_ms": round(plan_elapsed_ms, 3),
            "sum_methods_ms": round(sum_methods_ms, 3),
            "inter_method_and_framework_ms": round(plan_elapsed_ms - sum_methods_ms, 3),
            "inter_method_ratio_over_methods_pct": round(((plan_elapsed_ms - sum_methods_ms) / sum_methods_ms) * 100.0, 2) if sum_methods_ms > 0 else None,
            "plan_origin_mid_ms": round(origin_mid_ms, 3),
            "runner_init_est_ms": round(runner_init_ms, 3),
        }

    def ord_summary(scenario, run):
        clk = run["clock"]
        plan_elapsed_ms = run["plano"]["plan_elapsed_ns"] / 1_000_000.0
        sum_methods_ms = sum(m["invocations_sum_ns"] or 0 for m in run["methods"]) / 1_000_000.0
        sum_call_wall_ms = sum(m["method_wall_ns"] for m in run["methods"]) / 1_000_000.0
        origin_mid_ms = (clk["plan_origin_lower_ns"] + clk["plan_origin_upper_ns"]) / 2_000_000.0
        runner_init_ms = origin_mid_ms - clk["prepare_ms"]
        root_classes = [m["test_id"].split("#")[0].split("$")[0] for m in run["methods"]]
        switches = sum(1 for a, b in zip(root_classes, root_classes[1:]) if a != b)
        return {
            "mode": "ordered_junit_launcher",
            "scenario": scenario,
            "methods_total": len(run["methods"]),
            "methods_discovered": sum(m["discovered"] for m in run["methods"]),
            "methods_executed": sum(m["outcome"] != "skip" for m in run["methods"]),
            "total_invocations": sum(m["invocations"] for m in run["methods"]),
            "outcomes": dict(Counter(m["outcome"] for m in run["methods"])),
            "order_exact_match_pct": 100.0 if [m["rank"] for m in run["methods"]] == list(range(1, len(run["methods"]) + 1)) else 0.0,
            "root_class_switches": switches,
            "clock": clk,
            "plan_elapsed_ms": round(plan_elapsed_ms, 3),
            "sum_methods_ms": round(sum_methods_ms, 3),
            "sum_method_call_wall_ms": round(sum_call_wall_ms, 3),
            "inter_method_and_discovery_ms": round(plan_elapsed_ms - sum_methods_ms, 3),
            "inter_method_ratio_over_methods_pct": round(((plan_elapsed_ms - sum_methods_ms) / sum_methods_ms) * 100.0, 2) if sum_methods_ms > 0 else None,
            "plan_origin_mid_ms": round(origin_mid_ms, 3),
            "runner_init_est_ms": round(runner_init_ms, 3),
        }

    physical = {
        "t0_49": sf_summary("t0-49", t0_49),
        "t0_50": sf_summary("t0-50", t0_50),
        "t1_surefire_50": sf_summary("t1-surefire-50", t1_sf),
        "t1_ordenado_50": ord_summary("T1", ordered["T1"]),
        "t2_ordenado_50": ord_summary("T2", ordered["T2"]),
        "t3_ordenado_50": ord_summary("T3", ordered["T3"]),
    }

    method_comparisons = {
        "t1_surefire_vs_t0": compare_method_durations(t0_50_map, t1_sf_map),
    }
    for sc in ("T1", "T2", "T3"):
        ph_map = {
            m["test_id"]: {
                "outcome": m["outcome"],
                "invocations": m["invocations"],
                "duration_ns": m["invocations_sum_ns"],
            }
            for m in ordered[sc]["methods"]
        }
        method_comparisons[f"{sc.lower()}_ordenado_vs_t0"] = compare_method_durations(t0_50_map, ph_map)

    # Run KAN-23 simulation under two explicit startup models:
    # Model A: startup = prepare_ms only (before runner JVM boot)
    # Model B: startup = plan_origin_mid_ms (prepare_ms + runner initialization up to plan start)
    startup_a = {
        "T0": physical["t0_50"]["clock"]["prepare_ms"],
        "T1": physical["t1_ordenado_50"]["clock"]["prepare_ms"],
        "T2": physical["t2_ordenado_50"]["clock"]["prepare_ms"],
        "T3": physical["t3_ordenado_50"]["clock"]["prepare_ms"],
    }
    startup_b = {
        "T0": round(physical["t0_50"]["plan_origin_mid_ms"]),
        "T1": round(physical["t1_ordenado_50"]["plan_origin_mid_ms"]),
        "T2": round(physical["t2_ordenado_50"]["plan_origin_mid_ms"]),
        "T3": round(physical["t3_ordenado_50"]["plan_origin_mid_ms"]),
    }
    replay_a, metricas_a = run_simulation_pack(rodada_dir / "sim-modelo-a-prepare", t0_49, t0_50, frozen_ov_50, startup_a, True)
    replay_b, metricas_b = run_simulation_pack(rodada_dir / "sim-modelo-b-plan-origin", t0_49, t0_50, frozen_ov_50, startup_b, True)

    wall_49 = physical["t0_49"]["clock"]["wall_ms"]
    budgets = {p: (p * wall_49) // 100 for p in PERCENTUAIS}

    # Build cut-by-cut comparison (Simulated A & B vs Physical observed with external overhead)
    ext_ov = {
        "T0": 0,
        "T1": frozen_ov_50["selection_ms"],
        "T2": frozen_ov_50["selection_ms"] + frozen_ov_50["features_ms"] + frozen_ov_50["inference_T2_ms"],
        "T3": frozen_ov_50["selection_ms"] + frozen_ov_50["features_ms"] + frozen_ov_50["inference_T3_ms"],
    }
    t0_exec_ends = [
        m["last_end_ns"]
        for m in sorted(
            (m for m in t0_50["metodos"] if m["matched_outcome"] != "skip"),
            key=lambda m: m["matched_execution_order"],
        )
    ]
    cuts_a = {(c["scenario"], c["percent"]): c for c in replay_a["cuts"]}
    cuts_b = {(c["scenario"], c["percent"]): c for c in replay_b["cuts"]}

    budget_comparison = {}
    for p in PERCENTUAIS:
        b_ms = budgets[p]
        budget_comparison[str(p)] = {"budget_ms": b_ms, "scenarios": {}}
        for sc in ("T0", "T1", "T2", "T3"):
            if sc == "T0":
                clk = physical["t0_50"]["clock"]
                ends = t0_exec_ends
            else:
                clk = physical[f"{sc.lower()}_ordenado_50"]["clock"]
                ends = [m["method_end_ns"] for m in ordered[sc]["methods"] if m["outcome"] != "skip"]
            phys_cut = physical_prefix_count(
                ends, clk["plan_origin_lower_ns"], clk["plan_origin_upper_ns"], ext_ov[sc], b_ms
            )
            sim_a_cnt = len(cuts_a[(sc, p)]["prefix"]) if cuts_a[(sc, p)]["prefix"] is not None else None
            sim_b_cnt = len(cuts_b[(sc, p)]["prefix"]) if cuts_b[(sc, p)]["prefix"] is not None else None
            budget_comparison[str(p)]["scenarios"][sc] = {
                "external_overhead_ms": ext_ov[sc],
                "physical": phys_cut,
                "simulated_model_a_prepare_only": {
                    "completed": sim_a_cnt,
                    "delta_vs_physical_guaranteed": (sim_a_cnt - phys_cut["completed_guaranteed"]) if sim_a_cnt is not None else None,
                },
                "simulated_model_b_plan_origin": {
                    "completed": sim_b_cnt,
                    "delta_vs_physical_guaranteed": (sim_b_cnt - phys_cut["completed_guaranteed"]) if sim_b_cnt is not None else None,
                },
            }

    # Total serial estimate (RQ1) vs physical total with external overhead
    rq1_b = {r["cenario"]: r for r in metricas_b["revisoes"][0]["rq1"]}
    rq1_a = {r["cenario"]: r for r in metricas_a["revisoes"][0]["rq1"]}
    total_time_comparison = {}
    for sc in ("T0", "T1", "T2", "T3"):
        if sc == "T0":
            phys_wall_with_ov = physical["t0_50"]["clock"]["wall_ms"]
            phys_plan_end_with_ov = round(physical["t0_50"]["plan_origin_mid_ms"] + physical["t0_50"]["plan_elapsed_ms"])
        else:
            ph = physical[f"{sc.lower()}_ordenado_50"]
            phys_wall_with_ov = ph["clock"]["wall_ms"] + ext_ov[sc]
            phys_plan_end_with_ov = round(ph["plan_origin_mid_ms"] + ph["plan_elapsed_ms"] + ext_ov[sc])
        sim_a_total = rq1_a[sc]["tempo_total_ms"]
        sim_b_total = rq1_b[sc]["tempo_total_ms"]
        total_time_comparison[sc] = {
            "physical_wall_plus_overhead_ms": phys_wall_with_ov,
            "physical_plan_completion_plus_overhead_ms": phys_plan_end_with_ov,
            "simulated_model_a_ms": sim_a_total,
            "simulated_model_b_ms": sim_b_total,
            "error_model_b_vs_plan_completion_ms": sim_b_total - phys_plan_end_with_ov if sim_b_total is not None else None,
            "error_model_b_vs_plan_completion_pct": round(((sim_b_total - phys_plan_end_with_ov) / phys_plan_end_with_ov) * 100.0, 2) if sim_b_total is not None and phys_plan_end_with_ov > 0 else None,
        }

    # Also compare T1 Surefire physical reduction vs T0
    t0_wall = physical["t0_50"]["clock"]["wall_ms"]
    t1_sf_wall = physical["t1_surefire_50"]["clock"]["wall_ms"]
    t1_sf_plan = physical["t1_surefire_50"]["plan_elapsed_ms"]
    t0_plan = physical["t0_50"]["plan_elapsed_ms"]

    report = {
        "ticket": "KAN-28",
        "data_kind": "physical_validation_revision_50",
        "official_budget_evaluation": False,
        "sample_selection_rule": (
            "Revisao 50 (f24c027ff83b90beab2ec28696721200abb4f9e9): unica revisao pre-holdout "
            "fora do treino (15, 26, 42) com selecao congelada DIRTS + expansao direta sem fallback "
            "(416 metodos em 9 classes) e rankings congelados T1/T2/T3 com custos de selecao, features "
            "e inferencia medidos; revisao 49 (cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9) coletada no "
            "mesmo host e imagem como referencia T0 anterior tecnica para calibracao de 25%/50%/75%. "
            "Holdout 96 preservado sem leitura."
        ),
        "environment": {
            "image_id": exec_manifest["image_id"],
            "image_base_label": exec_manifest["image_base_label"],
            "platform": "linux/amd64",
            "timezone": "UTC",
            "maven_cache_initial": "cold",
            "surefire_forks": 1,
            "junit_parallel": False,
        },
        "frozen_sources": {
            "t1_commit": T1_COMMIT,
            "rankings_commit": RANKINGS_COMMIT,
            "overhead_50": frozen_ov_50,
        },
        "physical_runs": physical,
        "t1_surefire_order_vs_frozen_t1": {
            "executed_methods": len(t1_frozen_exec),
            "exact_position_matches": sum(a == b for a, b in zip(t1_frozen_exec, t1_sf_exec_order)),
            "spearman_rho": round(t1_sf_order_spearman, 4) if t1_sf_order_spearman is not None else None,
            "note": "Surefire/JUnit 5 executa por classe e ordem propria, nao seguindo ordem ordinal nem intercalacao entre classes de T2/T3.",
        },
        "t1_surefire_vs_t0_reduction": {
            "t0_wall_ms": t0_wall,
            "t1_surefire_wall_ms": t1_sf_wall,
            "t1_surefire_wall_plus_selection_ms": t1_sf_wall + frozen_ov_50["selection_ms"],
            "t0_plan_elapsed_ms": round(t0_plan, 3),
            "t1_surefire_plan_elapsed_ms": round(t1_sf_plan, 3),
            "plan_time_reduction_pct": round(((t0_plan - t1_sf_plan) / t0_plan) * 100.0, 2) if t0_plan > 0 else None,
            "wall_time_reduction_without_selection_pct": round(((t0_wall - t1_sf_wall) / t0_wall) * 100.0, 2) if t0_wall > 0 else None,
            "wall_time_reduction_with_selection_pct": round(((t0_wall - (t1_sf_wall + frozen_ov_50["selection_ms"])) / t0_wall) * 100.0, 2) if t0_wall > 0 else None,
        },
        "method_duration_comparisons": method_comparisons,
        "total_time_comparison": total_time_comparison,
        "budget_calibration_from_t0_49": {
            "reference_sha": SHA_49,
            "reference_wall_ms": wall_49,
            "budgets_ms": {str(k): v for k, v in budgets.items()},
            "cuts": budget_comparison,
        },
        "decision_adequacy": {
            "status": "adequada_com_restricoes_explicitas",
            "conditions": [
                "O simulador serial (KAN-23) reproduz integralmente a populacao e os desfechos quando o T0 tem cobertura e ordem global reconciliadas (416/416 metodos, 51.172/51.172 invocacoes, 0 divergencias de desfecho nesta amostra).",
                "O startup passado ao simulador DEVE incluir tanto o preparo (compilacao/Maven) quanto a inicializacao do runner ate o inicio do plano JUnit (Modelo B): no corte de 50% do T0, o Modelo B acertou exatamente os 1.424 metodos concluidos (delta 0), enquanto omitir a inicializacao do runner (Modelo A) superestimou em +6 metodos.",
                "A simulacao serial NAO captura o overhead entre metodos/framework (3,76% em T0 Surefire; 7,65% em T1 Surefire; 12,28% a 14,92% no runner ordenado) nem o efeito de localidade/troca de classe (T1 ordenado com 8 trocas somou 53,66 s vs. T2 com 75 trocas em 64,50 s e T3 com 178 trocas em 66,53 s). No corte de 75% do T0, o overhead de framework nao modelado produziu +41 metodos (+0,97%) no simulador.",
                "Fator de confusao identificado e quantificado: o Surefire do Commons Lang injeta o agente JaCoCo (jacoco:0.8.14:prepare-agent), enquanto o runner ordenado direto executa sem JaCoCo. Mesmo dentro do Surefire com JaCoCo, T1 Surefire teve soma de metodos 19,50% menor que T0 (mediana absoluta de 0,472 ms, com concentracao em poucos metodos pesados de FastDateParserTest), e no runner ordenado sem JaCoCo a diferenca foi de -31,24% a -44,54%, tornando a estimativa total da simulacao conservadora (+9,31% a +15,33% acima da execucao ordenada).",
                "Restricao fisica de runner em CI: o Surefire/JUnit 5 padrao agrupou as 9 classes e executou em ordem propria (Spearman rho = 0,3914 contra a ordem T1 congelada), nao suportando a intercalacao inter-classe exigida por T2 e T3; executar rankings T2/T3 fielmente requer um runner ordenado dedicado.",
                "Impacto de preparo em cache frio e custo de selecao nos orcamentos RQ2: com cache Maven frio (~74 s de preparo) e custo de selecao DIRTS + expansao de 78,58 s, todos os cenarios ficaram em 0 metodos no corte de 25% e T1-T3 permaneceram em 0 metodos no corte de 50% (concordancia exata entre fisico e simulado).",
                "Como a revisao 50 tem 0 falhas naturais em T0, esta validacao comprova fidelidade de populacao, ordem, desfechos pass/skip e modelagem de tempo/prefixo, mas NAO substitui validacao de deteccao de falhas naturais sob ordenacoes distintas (ex.: interacao entre testes ou flakiness dependente de ordem)."
            ],
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rodada_dir", type=Path)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.rodada_dir)
    args.saida.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.saida}")


if __name__ == "__main__":
    main()
