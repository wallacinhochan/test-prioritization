"""Consolida dados T0-T3 da KAN-29 no contrato KAN-15 0.1.0 e calcula RQ1/RQ2/APFDc."""
import argparse
import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT / "evidencias" / "KAN-22"))
sys.path.insert(0, str(ROOT / "evidencias" / "KAN-23"))
sys.path.insert(0, str(ROOT / "src"))

import replay as kan22_replay
import simular as kan23_simular
from test_prioritization.metrics.cli import avaliar as avaliar_metricas

LOTS = {
    "congelado-expansao-v1": ("ef577158bc012d87784bbfab1b9ccb4ee80cf812", "38156c385b0ee24915b230ffdb4439acb660467f147238492651c23b683456d1"),
    "congelado-expansao-lote-02": ("41a22e394de36512921bad82a4a28d029d8bb55f", "b82944a76add5bfcfa148d00f8af5ed0bf0a0b00a23e72b4fdf70865da9ed702"),
    "congelado-expansao-lote-03": ("ba7f204693007f18db648fdf16e34f52c62397f7", "b886dd2e473b96aa3a35df166affb26a48de3860622bdd8778b3ff975ea8ae67"),
    "congelado-expansao-lote-04": ("767f08b6dc2fe203d925bd9f97883028c3af551d", "0dffd291d16d20966f7cce60c87eea621c6d9cfe94757daf017d1fc346da19b8"),
}
FREEZE_50 = "a06d381c7a9e0fc896e7c5ae84d94a452eedc56a"
AUX_EVAL_50 = "d2c0e7ad276dd567d8e063306ebbf23662d51866"
FROZEN_50_DIR = "evidencias/KAN-19/expansao50-experimental-v1"
FEATURE_FIELDS = ("comprimento_nome", "quantidade_parametros", "classe_aninhada")
HOLDOUT = 96


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(commit: str, path: str, expected_sha256: str | None = None) -> bytes:
    data = subprocess.check_output(
        ["git", "-c", "safe.directory=*", "-C", str(ROOT), "show", f"{commit}:{path}"]
    )
    if expected_sha256 is not None and digest(data) != expected_sha256:
        raise ValueError(f"Hash divergente em {commit}:{path}")
    return data


def signature(test_id: str):
    match = re.fullmatch(r"([^#]+)#([^()]+)\(([^()]*)\)", test_id)
    if not match:
        raise ValueError(f"Identidade JUnit invalida: {test_id}")
    binary_class, name, parameters = match.groups()
    return len(name), parameters.count(",") + 1 if parameters else 0, int("$" in binary_class)


def write_csv(path: Path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(fields)
        w.writerows(rows)


def round_ms(value) -> str:
    if value is None or value == "":
        return ""
    return str(round(float(value)))


def prepare_t1_t2_t3(work_dir: Path):
    work_dir.mkdir(parents=True, exist_ok=True)
    tables = defaultdict(list)
    commits_raw = None
    commits = {}
    lot_sources = {}
    seen_pos = set()

    for lot, (commit, expected_manifest_sha) in LOTS.items():
        bundle = f"evidencias/KAN-18/{lot}"
        raw_manifest = git_show(commit, f"{bundle}/manifesto.json", expected_manifest_sha)
        manifest = json.loads(raw_manifest)
        if manifest["holdout"]["rotulos_lidos"]:
            raise ValueError(f"Holdout violado no lote {lot}")
        hashes = manifest["saidas_sha256"]
        if commits_raw is None:
            commits_raw = git_show(commit, f"{bundle}/commits.csv", hashes["commits.csv"])
            commits = {int(r["commit_order"]): r["commit_sha"]
                       for r in csv.DictReader(commits_raw.decode("utf-8-sig").splitlines())}
        pos_in_lot = {r["posicao"] for r in manifest["revisoes"].values()}
        if seen_pos & pos_in_lot:
            raise ValueError(f"Sobreposicao de posicoes no lote {lot}")
        seen_pos |= pos_in_lot
        lot_sources[lot] = {
            "commit": commit,
            "manifest_sha256": digest(raw_manifest),
            "positions": sorted(p for p in pos_in_lot if p != HOLDOUT),
        }
        for key, filename in (("selection", "selection.csv"), ("t1", "rankings.csv"), ("overhead", "overhead.csv")):
            data = git_show(commit, f"{bundle}/{filename}", hashes[filename])
            rows = list(csv.DictReader(data.decode("utf-8-sig").splitlines()))
            tables[key].extend(r for r in rows if r["commit_sha"] != commits[HOLDOUT])

    # Frozen training from FREEZE_50 (15, 26, 42; 524 known targets; no balancing)
    frozen_m = json.loads(git_show(FREEZE_50, f"{FROZEN_50_DIR}/manifesto.json"))
    train_raw = git_show(FREEZE_50, f"{FROZEN_50_DIR}/treino_sintetico.csv",
                         frozen_m["sha256_saida"]["treino_sintetico.csv"])
    training_rows = list(csv.DictReader(train_raw.decode("utf-8-sig").splitlines()))

    positions_by_sha = {sha: pos for pos, sha in commits.items()}
    t1_by_sha = defaultdict(list)
    for r in tables["t1"]:
        t1_by_sha[r["commit_sha"]].append(r)

    features_rows, feature_ns = [], {}
    for sha, rows in t1_by_sha.items():
        ordered = sorted(rows, key=lambda r: int(r["rank"]))
        t0 = perf_counter_ns()
        features_rows.extend((positions_by_sha[sha], sha, r["test_id"], *signature(r["test_id"])) for r in ordered)
        feature_ns[sha] = perf_counter_ns() - t0

    # Write inputs for KAN-22 replay
    inp = work_dir / "kan22_entradas"
    inp.mkdir(parents=True, exist_ok=True)
    write_csv(inp / "commits.csv", ("position", "commit_sha"), sorted(commits.items()))
    write_csv(inp / "selection.csv", kan22_replay.SELECTION_FIELDS,
              [tuple(r[f] for f in kan22_replay.SELECTION_FIELDS) for r in tables["selection"]])
    write_csv(inp / "t1.csv", kan22_replay.RANK_FIELDS,
              [tuple(r[f] for f in kan22_replay.RANK_FIELDS) for r in tables["t1"]])
    write_csv(inp / "overhead.csv", kan22_replay.OVERHEAD_FIELDS,
              [tuple(r[f] for f in kan22_replay.OVERHEAD_FIELDS) for r in tables["overhead"]])
    train_fields = ("position", "commit_sha", "test_id", *FEATURE_FIELDS, "partition", "target_synthetic")
    write_csv(inp / "train.csv", train_fields,
              [tuple(r.get(f, "treino") for f in train_fields) for r in training_rows])
    write_csv(inp / "features.csv", ("position", "commit_sha", "test_id", *FEATURE_FIELDS), features_rows)
    rel_ref = f"{FROZEN_50_DIR}/manifesto.json@{FREEZE_50}#treino"
    write_csv(inp / "availability.csv", kan22_replay.AVAILABILITY_FIELDS,
              [(commits[p], 50, rel_ref) for p in (15, 26, 42)])

    paths = {k: inp / f"{k}.csv" for k in ("commits", "train", "availability", "features", "selection", "t1", "overhead")}
    c_map, labeled, avail, feats, costs, _ = kan22_replay.load_inputs(paths, FEATURE_FIELDS)
    hist = kan22_replay.replay(c_map, [], {}, feats, costs, "evidencias/KAN-29/consolidado-58-60.json",
                               feature_fields=FEATURE_FIELDS)
    if hist[0] or hist[1] or hist[4]:
        raise RuntimeError("Replay historico sem disponibilidade deve permanecer vazio")

    t23_ranks, t23_ov, windows, cov, _ = kan22_replay.replay(
        c_map, labeled, avail, feats, costs, "evidencias/KAN-29/consolidado-58-60.json",
        feature_fields=FEATURE_FIELDS,
    )

    # Also load frozen rankings/overhead for position 50 (technical validation block)
    r50_raw = git_show(FREEZE_50, f"{FROZEN_50_DIR}/rankings.csv", frozen_m["sha256_saida"]["rankings.csv"])
    r50_rows = [tuple(r[f] for f in kan22_replay.RANK_FIELDS)
                for r in csv.DictReader(r50_raw.decode("utf-8-sig").splitlines())]
    ov50_raw = git_show(FREEZE_50, f"{FROZEN_50_DIR}/overhead.csv", frozen_m["sha256_saida"]["overhead.csv"])
    ov50_parsed = {(r["scenario"], r["phase"]): r
                   for r in csv.DictReader(ov50_raw.decode("utf-8-sig").splitlines())}

    # Normalize overhead rows with integer ms for KAN-23/simular.py
    all_ov = []
    # T1 overhead from frozen lots
    for r in tables["overhead"]:
        all_ov.append((r["commit_sha"], r["scenario"], r["phase"], r["measurement_status"],
                       round_ms(r["duration_ms"]), r["source_ref"]))
    # T2/T3 overhead from KAN-22 replay (58, 59, 60, 64, 75, 100)
    for row in t23_ov:
        sha, sc, phase, status, dur, ref = row
        if phase == "features":
            all_ov.append((sha, sc, phase, "measured", round_ms(feature_ns[sha] / 1_000_000),
                           "evidencias/KAN-29/consolidado-58-60.json#features"))
        else:
            all_ov.append((sha, sc, phase, status, round_ms(dur), ref))
    # T2/T3 overhead for position 50 (frozen experimental)
    sha50 = commits[50]
    for sc in ("T2", "T3"):
        for phase in ("selection", "features", "inference"):
            r = ov50_parsed[(sc, phase)]
            all_ov.append((sha50, sc, phase, r["measurement_status"], round_ms(r["duration_ms"]), r["source_ref"]))
        fit_ms = round(frozen_m["tempos"]["modelos"][sc]["fit_ns"] / 1_000_000)
        all_ov.append((sha50, sc, "training", "measured", str(fit_ms),
                       f"{FROZEN_50_DIR}/manifesto.json@{FREEZE_50}#{sc}-fit"))

    all_ranks = (
        [tuple(r[f] for f in kan22_replay.RANK_FIELDS) for r in tables["t1"]]
        + r50_rows
        + list(t23_ranks)
    )
    return {
        "commits_raw": commits_raw,
        "commits": commits,
        "lot_sources": lot_sources,
        "seen_t1_positions": sorted(seen_pos),
        "selection_rows": [tuple(r[f] for f in kan22_replay.SELECTION_FIELDS) for r in tables["selection"]],
        "ranking_rows": all_ranks,
        "overhead_rows": all_ov,
        "windows": windows,
        "kan22_coverage": cov,
        "feature_ns": feature_ns,
        "historical_ranking_rows": len(hist[0]),
    }


def load_t0_entries(t0_window_dir: Path, t0_49_50_dir: Path | None):
    entries = {}
    win_manifest = json.loads((t0_window_dir / "coleta_t0_manifesto.json").read_text(encoding="utf-8"))
    for att in win_manifest["attempts"]:
        pos = att["position"]
        deriv = t0_window_dir / att["label"] / "derivados"
        resumo = json.loads((deriv / "resumo.json").read_text(encoding="utf-8"))
        entries[pos] = {
            "position": pos,
            "sha": att["sha"],
            "attempt_id": f"kan29-{att['label']}",
            "finish": att["finish"],
            "image": att["image"],
            "derivados": deriv,
            "resumo": resumo,
            "origin": "kan29_coleta_57_60",
        }
    if t0_49_50_dir and (t0_49_50_dir / "execucao_manifesto.json").is_file():
        m28 = json.loads((t0_49_50_dir / "execucao_manifesto.json").read_text(encoding="utf-8"))
        for label, pos in (("t0-49", 49), ("t0-50", 50)):
            att = m28["attempts"][label]
            deriv = t0_49_50_dir / label / "derivados"
            resumo = json.loads((deriv / "resumo.json").read_text(encoding="utf-8"))
            entries[pos] = {
                "position": pos,
                "sha": att["sha"],
                "attempt_id": f"kan28-{label}",
                "finish": att["finish"],
                "image": att["image"],
                "derivados": deriv,
                "resumo": resumo,
                "origin": "kan28_rodada_v1_mesmo_host",
            }
    return entries, win_manifest


def consolidate(t0_window_dir: Path, out_dir: Path, t0_49_50_dir: Path | None = None):
    out_dir.mkdir(parents=True, exist_ok=True)
    t123 = prepare_t1_t2_t3(out_dir / "intermediarios")
    t0_entries, win_manifest = load_t0_entries(t0_window_dir, t0_49_50_dir)

    images = {e["image"] for e in t0_entries.values()}
    if len(images) != 1:
        raise ValueError(f"Imagens T0 divergentes entre tentativas: {images}")
    image_id = next(iter(images))
    config_id = f"kan13|{image_id}|linux/amd64|UTC|cold|1fork|serial"

    # Build unified KAN-15 CSV bundle in out_dir / "pacote-kan15"
    pack = out_dir / "pacote-kan15"
    pack.mkdir(parents=True, exist_ok=True)

    commits_rows = list(csv.DictReader(t123["commits_raw"].decode("utf-8-sig").splitlines()))
    t0_shas = {e["sha"] for e in t0_entries.values()}
    for row in commits_rows:
        if row["commit_sha"] in t0_shas:
            row["eligibility_status"] = "eligible"
    write_csv(pack / "commits.csv", list(commits_rows[0].keys()),
              [[r[k] for k in commits_rows[0].keys()] for r in commits_rows])

    t0_runs_rows, t0_results_rows = [], []
    for pos in sorted(t0_entries):
        deriv = t0_entries[pos]["derivados"]
        with (deriv / "t0_runs.csv").open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                t0_runs_rows.append((r["commit_sha"], r["scenario"], r["run_status"],
                                     r["suite_duration_ms"], r["source_ref"]))
        with (deriv / "t0_results.csv").open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                t0_results_rows.append((r["commit_sha"], r["scenario"], r["test_id"], r["outcome"],
                                        r["duration_ms"], r["execution_order"], r["source_ref"]))

    write_csv(pack / "t0_runs.csv", ("commit_sha", "scenario", "run_status", "suite_duration_ms", "source_ref"),
              t0_runs_rows)
    write_csv(pack / "t0_results.csv",
              ("commit_sha", "scenario", "test_id", "outcome", "duration_ms", "execution_order", "source_ref"),
              t0_results_rows)
    write_csv(pack / "selection.csv", kan22_replay.SELECTION_FIELDS, t123["selection_rows"])
    write_csv(pack / "rankings.csv", kan22_replay.RANK_FIELDS, t123["ranking_rows"])
    write_csv(pack / "overhead.csv", kan22_replay.OVERHEAD_FIELDS, t123["overhead_rows"])

    # Build KAN-23 manifesto using Model B startup (plan_origin_mid_ms, approved in KAN-28)
    # Chronological technical availability: each prior T0 available 1s before target cutoff
    references = {}
    for pos, e in sorted(t0_entries.items()):
        references[e["sha"]] = {
            "attempt": e["attempt_id"],
            "available_at": e["finish"],
            "configuration": config_id,
        }

    # Evaluate main consecutive targets (58, 59, 60) and technical validation target (50 if present)
    eval_positions = [p for p in (58, 59, 60) if p in t0_entries]
    if 50 in t0_entries and 49 in t0_entries:
        eval_positions = [50] + eval_positions

    targets = {}
    for pos in eval_positions:
        e = t0_entries[pos]
        prev = t0_entries[pos - 1]
        clk = e["resumo"]["clock"]
        # Model B startup (prepare + runner init until JUnit plan start) from measured T0 on same commit/image
        startup_b_ms = round((clk["plan_origin_lower_ns"] + clk["plan_origin_upper_ns"]) / 2_000_000)
        cutoff = (datetime.fromisoformat(prev["finish"]) + timedelta(seconds=1)).isoformat()
        sel_ref = (
            f"evidencias/KAN-18/congelado-expansao-v1/manifesto.json@{LOTS['congelado-expansao-v1'][0]}#posicao-050"
            if pos == 50
            else f"evidencias/KAN-18/congelado-expansao-lote-04/manifesto.json@{LOTS['congelado-expansao-lote-04'][0]}#posicao-{pos:03d}"
        )
        rank_refs = {
            "T1": sel_ref,
            "T2": f"{FROZEN_50_DIR}/rankings.csv@{FREEZE_50}#T2" if pos == 50 else "evidencias/KAN-29/consolidado-58-60.json#janela-50-T2",
            "T3": f"{FROZEN_50_DIR}/rankings.csv@{FREEZE_50}#T3" if pos == 50 else "evidencias/KAN-29/consolidado-58-60.json#janela-50-T3",
        }
        targets[e["sha"]] = {
            "cutoff": cutoff,
            "configuration": config_id,
            "selection_ref": sel_ref,
            "ranking_refs": rank_refs,
            "startup": {
                sc: {"duration_ms": str(startup_b_ms), "source_ref": f"{e['attempt_id']}#plan_origin_mid_ms"}
                for sc in ("T0", "T1", "T2", "T3")
            },
        }

    manifesto_kan23 = {
        "contract_version": "0.1.0",
        "data_kind": "technical_consolidated_kan29_window",
        "references": references,
        "targets": targets,
    }
    (pack / "manifesto.json").write_text(json.dumps(manifesto_kan23, indent=2) + "\n", encoding="utf-8")

    replay_out = kan23_simular.simular(pack)
    (out_dir / "replay_kan23.json").write_text(json.dumps(replay_out, indent=2) + "\n", encoding="utf-8")
    metricas_out = avaliar_metricas(pack, replay_out)
    (out_dir / "metricas_kan25_27.json").write_text(json.dumps(metricas_out, indent=2) + "\n", encoding="utf-8")

    # Separate main consecutive window [58, 59, 60] from technical validation [50] and synthetic auxiliary [50 mutantes]
    cuts_by_key = {(c["commit_order"], c["scenario"], c["percent"]): c for c in replay_out["cuts"]}
    rev_by_pos = {r["commit_order"]: r for r in metricas_out["revisoes"]}

    def summarize_position(pos):
        rev = rev_by_pos[pos]
        t0_e = t0_entries[pos]
        ref_cut = cuts_by_key[(pos, "T0", 25)]
        return {
            "position": pos,
            "commit_sha": rev["commit_sha"],
            "reference_t0_position": ref_cut["reference"]["commit_order"],
            "reference_t0_sha": ref_cut["reference"]["commit_sha"],
            "reference_t0_wall_ms": ref_cut["reference"]["suite_duration_ms"],
            "t0_current_clock": t0_e["resumo"]["clock"],
            "t0_current_maven_totals": t0_e["resumo"].get("maven_totals"),
            "rq1": rev["rq1"],
            "rq2_by_budget": {
                str(p): {
                    "budget_ms": cuts_by_key[(pos, "T0", p)]["budget_ms"],
                    "scenarios": {
                        c["scenario"]: {
                            "status": cuts_by_key[(pos, c["scenario"], p)]["status"],
                            "completed_methods": len(cuts_by_key[(pos, c["scenario"], p)]["prefix"] or []),
                            "detected_failures": c["detectadas"],
                            "proportion": c["proporcao"],
                            "first_failure_state": c["estado_primeira_falha"],
                        }
                        for c in rev["rq2"] if c["percent"] == p
                    },
                }
                for p in (25, 50, 75)
            },
            "apfdc": rev["apfdc"],
        }

    # Auxiliary synthetic evidence (kept strictly separate)
    aux_raw = git_show(AUX_EVAL_50, "evidencias/KAN-19/avaliacao-expansao50.json")
    aux_data = json.loads(aux_raw)

    # Full 100-commit coverage audit
    t1_set = set(t123["seen_t1_positions"])
    t0_set = set(t0_entries.keys())
    eval_set = set(eval_positions)
    cov_counts = Counter()
    for p in range(1, 101):
        if p == HOLDOUT:
            cov_counts["excluded_holdout"] += 1
        elif p in eval_set:
            cov_counts["complete_t0_t3_evaluated"] += 1
        elif p in t0_set:
            cov_counts["t0_reference_only"] += 1
        elif p in t1_set:
            cov_counts["t1_frozen_missing_t0"] += 1
        else:
            cov_counts["missing_t0_and_t1"] += 1

    package_hashes = {p.name: digest(p.read_bytes()) for p in sorted(pack.iterdir()) if p.is_file()}

    consolidated = {
        "ticket": "KAN-29",
        "contract_version": "0.1.0",
        "data_kind": "technical_consolidated_kan29_window",
        "official_full_100_campaign": False,
        "holdout": {"position": HOLDOUT, "labels_read": False, "excluded_from_pack": True},
        "environment": {
            "image_id": image_id,
            "image_base_label": win_manifest["image_base_label"],
            "configuration_id": config_id,
            "python": platform.python_version(),
            "scikit_learn": version("scikit-learn"),
            "startup_model": "Modelo B (plan_origin_mid_ms = prepare_ms + runner_init, aprovado na KAN-28)",
        },
        "sources": {
            "t1_lots": t123["lot_sources"],
            "kan22_training_freeze": FREEZE_50,
            "kan22_cadence": 10,
            "kan22_historical_ranking_rows": t123["historical_ranking_rows"],
            "t0_window_positions": sorted(t0_entries.keys()),
            "t0_attempts": {
                str(pos): {
                    "sha": e["sha"],
                    "attempt_id": e["attempt_id"],
                    "origin": e["origin"],
                    "finish": e["finish"],
                    "wall_ms": e["resumo"]["clock"]["wall_ms"],
                    "matched_cases": e["resumo"]["matched_cases"],
                    "xml_cases": e["resumo"]["xml_cases"],
                    "gaps": e["resumo"]["gaps"],
                    "maven_totals": e["resumo"].get("maven_totals"),
                }
                for pos, e in sorted(t0_entries.items())
            },
        },
        "coverage_100_commits": {
            "counts": dict(cov_counts),
            "t1_frozen_positions": sorted(t1_set),
            "t0_instrumented_positions": sorted(t0_set),
            "evaluated_main_consecutive_positions": [p for p in (58, 59, 60) if p in eval_set],
            "evaluated_technical_validation_positions": [50] if 50 in eval_set else [],
            "missing_t1_count": 100 - len(t1_set),
            "missing_t0_count": 100 - len(t0_set),
        },
        "main_consecutive_results": [summarize_position(p) for p in (58, 59, 60) if p in eval_set],
        "technical_validation_results": [summarize_position(50)] if 50 in eval_set else [],
        "auxiliary_synthetic_evidence_separate": {
            "source": f"{AUX_EVAL_50}:evidencias/KAN-19/avaliacao-expansao50.json",
            "source_sha256": digest(aux_raw),
            "position": 50,
            "note": "Evidencia auxiliar de 4 mutantes sinteticos na revisao 50; mantida separada do oraculo natural T0.",
            "mutants_total": aux_data["denominador_mutantes"],
            "detected_by_scenario": aux_data["detectados"],
        },
        "kan15_package_sha256": package_hashes,
        "cobertura_rq2": metricas_out["cobertura_rq2"],
    }
    return consolidated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("t0_window_dir", type=Path, help="Diretorio gerado por coletar_t0_janela.py")
    parser.add_argument("--t0-49-50-dir", type=Path, default=None, help="Opcional: rodada-v1 da KAN-28 com T0 49 e 50")
    parser.add_argument("--work-dir", type=Path, required=True, help="Diretorio local de saida do pacote KAN-15")
    parser.add_argument("--saida", type=Path, required=True, help="JSON consolidado versionavel")
    args = parser.parse_args()
    result = consolidate(args.t0_window_dir, args.work_dir, args.t0_49_50_dir)
    args.saida.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.saida}")


if __name__ == "__main__":
    main()
