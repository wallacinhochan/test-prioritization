"""Coleta em serie T0 instrumentado (piloto-surefire.sh + RastroJUnit) para posicoes KAN-10."""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
KAN23_COLETA = ROOT / "evidencias" / "KAN-23" / "coleta"
COMMITS_CSV = ROOT / "evidencias" / "KAN-10" / "commits.csv"
IMAGE = "test-prioritization/commons-lang:kan13"


def git_env():
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_COUNT", "1")
    env.setdefault("GIT_CONFIG_KEY_0", "safe.directory")
    env.setdefault("GIT_CONFIG_VALUE_0", "*")
    return env


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_image():
    raw = subprocess.check_output(["docker", "image", "inspect", IMAGE], text=True)
    info = json.loads(raw)[0]
    base_label = info["Config"]["Labels"].get("org.opencontainers.image.base.name", "")
    if info["Os"] != "linux" or info["Architecture"] != "amd64" or "@sha256:" not in base_label:
        raise RuntimeError(f"Imagem {IMAGE} incompativel: {info['Os']}/{info['Architecture']} {base_label}")
    return info["Id"], base_label


def load_positions():
    by_pos = {}
    with COMMITS_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            by_pos[int(row["position"])] = row["commit_sha"]
    return by_pos


def compile_collector(image_id: str, junit_dir: Path, out_dir: Path):
    needed = [
        junit_dir / "junit-platform-commons" / "1.13.4" / "junit-platform-commons-1.13.4.jar",
        junit_dir / "junit-platform-engine" / "1.13.4" / "junit-platform-engine-1.13.4.jar",
        junit_dir / "junit-platform-launcher" / "1.13.4" / "junit-platform-launcher-1.13.4.jar",
    ]
    for p in needed:
        if not p.is_file():
            raise FileNotFoundError(f"JAR JUnit ausente: {p}")
    jars_dir = out_dir / "launcher-jars"
    jars_dir.mkdir(parents=True, exist_ok=True)
    for jar in needed:
        shutil.copy2(jar, jars_dir / jar.name)

    collector = out_dir / "coletor-classes"
    collector.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--mount", f"type=bind,source={KAN23_COLETA.resolve()},target=/src,readonly",
        "--mount", f"type=bind,source={jars_dir.resolve()},target=/jars,readonly",
        "--mount", f"type=bind,source={collector.resolve()},target=/out",
        image_id,
        "sh", "-c",
        "javac -cp '/jars/*' -d /out /src/RastroJUnit.java && cp -R /src/META-INF /out/",
    ], check=True)
    return collector


def collect_one(pos: int, sha: str, image_id: str, source_repo: Path, collector: Path, out_root: Path):
    if pos == 96:
        raise ValueError("Holdout 96 proibido nesta coleta")
    label = f"pos-{pos:03d}"
    attempt_dir = out_root / label
    evidencia = attempt_dir / "evidencia"
    evidencia.mkdir(parents=True, exist_ok=False)
    tar_path = attempt_dir / "fonte.tar"
    subprocess.run(
        ["git", "-C", str(source_repo), "archive", "--format=tar", f"--output={tar_path}", sha],
        check=True, env=git_env(),
    )
    archive_sha = sha256_file(tar_path)

    cmd = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--mount", f"type=bind,source={tar_path.resolve()},target=/fonte.tar,readonly",
        "--mount", f"type=bind,source={collector.resolve()},target=/coletor,readonly",
        "--mount", f"type=bind,source={evidencia.resolve()},target=/evidencia",
        "--mount", f"type=bind,source={KAN23_COLETA.resolve()},target=/roteiros,readonly",
        image_id,
        "sh", "/roteiros/piloto-surefire.sh",
    ]
    start = datetime.now(timezone.utc)
    log_path = attempt_dir / "maven.log"
    with log_path.open("wb") as fh:
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT)
    finish = datetime.now(timezone.utc)

    meta = {
        "label": label,
        "position": pos,
        "sha": sha,
        "image": image_id,
        "archive_sha256": archive_sha,
        "start": start.isoformat(),
        "finish": finish.isoformat(),
        "exit_code": proc.returncode,
    }
    (attempt_dir / "tentativa.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"[{label} {sha[:7]}] exit={proc.returncode} wall_host={(finish - start).total_seconds():.2f}s", flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f"T0 {label} falhou com codigo {proc.returncode}")

    derived = attempt_dir / "derivados"
    source_ref = f"evidencias/KAN-29/local/{out_root.name}/{label}/derivados/resumo.json"
    subprocess.run([
        sys.executable, "-B", str(KAN23_COLETA / "reconciliar_t0.py"),
        str(evidencia), str(derived), "--kan15-source-ref", source_ref,
    ], check=True)
    resumo = json.loads((derived / "resumo.json").read_text(encoding="utf-8"))
    meta["derived_available_locally_at"] = datetime.now(timezone.utc).isoformat()
    meta["reconciliation_summary"] = {
        "xml_cases": resumo["xml_cases"],
        "matched_cases": resumo["matched_cases"],
        "methods_with_start": resumo["methods_with_start"],
        "methods_with_duration": resumo["methods_with_duration"],
        "gaps": resumo["gaps"],
        "maven_totals": resumo.get("maven_totals"),
        "clock": resumo["clock"],
    }
    meta["derived_sha256"] = {
        p.name: sha256_file(p) for p in sorted(derived.iterdir()) if p.is_file()
    }
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Novo diretorio sob evidencias/KAN-29/local/")
    parser.add_argument("--posicoes", type=int, nargs="+", default=[57, 58, 59, 60])
    parser.add_argument("--fonte", type=Path, default=ROOT.parent / "KAN-10-upstream.git")
    parser.add_argument(
        "--junit-dir", type=Path,
        default=Path.home() / ".m2" / "repository" / "org" / "junit" / "platform",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_id):
        parser.error("run_id invalido")
    if 96 in args.posicoes:
        parser.error("Holdout 96 nao permitido")

    out_root = BASE / "local" / args.run_id
    out_root.mkdir(parents=True, exist_ok=False)
    image_id, base_label = inspect_image()
    collector = compile_collector(image_id, args.junit_dir, out_root)
    by_pos = load_positions()

    manifest = {
        "ticket": "KAN-29",
        "data_kind": "instrumented_technical_t0_window",
        "run_id": args.run_id,
        "image_id": image_id,
        "image_base_label": base_label,
        "configuration": {
            "platform": "linux/amd64",
            "timezone": "UTC",
            "maven_cache_initial": "cold",
            "surefire_forks": 1,
            "junit_parallel": False,
            "executor": "piloto-surefire.sh/full-suite",
            "wall_interval": "prepare_start through reports_finish in container",
        },
        "positions": args.posicoes,
        "attempts": [],
    }
    for pos in args.posicoes:
        manifest["attempts"].append(
            collect_one(pos, by_pos[pos], image_id, args.fonte, collector, out_root)
        )
    (out_root / "coleta_t0_manifesto.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"T0 WINDOW DONE: {out_root}")


if __name__ == "__main__":
    main()
