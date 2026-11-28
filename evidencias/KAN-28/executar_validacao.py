"""Orquestra execucoes fisicas em serie da KAN-28 (T0 49/50, T1 Surefire e T1/T2/T3 ordenados)."""
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
IMAGE = "test-prioritization/commons-lang:kan13"
SHA_49 = "cc5ecf5db64abf0d2a2f59be16f9dc49a520dca9"
SHA_50 = "f24c027ff83b90beab2ec28696721200abb4f9e9"
T1_COMMIT = "ef577158bc012d87784bbfab1b9ccb4ee80cf812"
RANKINGS_COMMIT = "a06d381c7a9e0fc896e7c5ae84d94a452eedc56a"
SUREFIRE_CLASSES_50 = (
    "org.apache.commons.lang3.EnumUtilsTest,"
    "org.apache.commons.lang3.JavaVersionTest,"
    "org.apache.commons.lang3.LocaleUtilsTest,"
    "org.apache.commons.lang3.StringUtilsTest,"
    "org.apache.commons.lang3.SystemPropertiesTest,"
    "org.apache.commons.lang3.SystemUtilsTest,"
    "org.apache.commons.lang3.reflect.FieldUtilsTest,"
    "org.apache.commons.lang3.time.FastDateParserTest,"
    "org.apache.commons.lang3.time.FastDateParser_TimeZoneStrategyTest"
)


def git_env():
    env = os.environ.copy()
    env.setdefault("GIT_CONFIG_COUNT", "1")
    env.setdefault("GIT_CONFIG_KEY_0", "safe.directory")
    env.setdefault("GIT_CONFIG_VALUE_0", "*")
    return env


def run_checked(cmd, **kwargs):
    return subprocess.run(cmd, check=True, **kwargs)


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


def find_junit_jars(junit_dir: Path) -> Path:
    needed = [
        junit_dir / "junit-platform-commons" / "1.13.4" / "junit-platform-commons-1.13.4.jar",
        junit_dir / "junit-platform-engine" / "1.13.4" / "junit-platform-engine-1.13.4.jar",
        junit_dir / "junit-platform-launcher" / "1.13.4" / "junit-platform-launcher-1.13.4.jar",
    ]
    for p in needed:
        if not p.is_file():
            raise FileNotFoundError(f"JAR JUnit Platform ausente: {p}")
    return needed


def compile_collector_in_docker(image_id: str, junit_jars, out_dir: Path):
    jars_dir = out_dir / "launcher-jars"
    jars_dir.mkdir(parents=True, exist_ok=True)
    for jar in junit_jars:
        shutil.copy2(jar, jars_dir / jar.name)

    collector_classes = out_dir / "coletor-classes"
    collector_classes.mkdir(parents=True, exist_ok=True)
    run_checked([
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--mount", f"type=bind,source={KAN23_COLETA.resolve()},target=/src,readonly",
        "--mount", f"type=bind,source={jars_dir.resolve()},target=/jars,readonly",
        "--mount", f"type=bind,source={collector_classes.resolve()},target=/out",
        image_id,
        "sh", "-c",
        "javac -cp '/jars/*' -d /out /src/RastroJUnit.java && cp -R /src/META-INF /out/",
    ])
    return collector_classes, jars_dir


def export_frozen_orders(out_dir: Path):
    orders_dir = out_dir / "ordens"
    orders_dir.mkdir(parents=True, exist_ok=True)

    t1_raw = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{T1_COMMIT}:evidencias/KAN-18/congelado-expansao-v1/rankings.csv"],
        env=git_env(),
    ).decode("utf-8")
    t23_raw = subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{RANKINGS_COMMIT}:evidencias/KAN-19/expansao50-experimental-v1/rankings.csv"],
        env=git_env(),
    ).decode("utf-8")

    by_scenario = {"T1": [], "T2": [], "T3": []}
    for row in csv.DictReader(t1_raw.splitlines()):
        if row["commit_sha"] == SHA_50 and row["scenario"] == "T1":
            by_scenario["T1"].append((int(row["rank"]), row["test_id"]))
    for row in csv.DictReader(t23_raw.splitlines()):
        if row["commit_sha"] == SHA_50 and row["scenario"] in ("T2", "T3"):
            by_scenario[row["scenario"]].append((int(row["rank"]), row["test_id"]))

    paths = {}
    for scenario, items in by_scenario.items():
        items.sort()
        if len(items) != 416 or [r for r, _ in items] != list(range(1, 417)):
            raise ValueError(f"Ranking congelado invalido para {scenario}: {len(items)}")
        path = orders_dir / f"{scenario}.txt"
        path.write_bytes(("\n".join(tid for _, tid in items) + "\n").encode("utf-8"))
        paths[scenario] = path
    return paths


def make_archive(source_repo: Path, sha: str, target_tar: Path):
    run_checked(["git", "-C", str(source_repo), "archive", "--format=tar", f"--output={target_tar}", sha],
                env=git_env())
    return sha256_file(target_tar)


def run_surefire(label: str, image_id: str, source_repo: Path, sha: str, position: int,
                 collector_classes: Path, out_root: Path, test_filter: str | None = None):
    attempt_dir = out_root / label
    evidencia_dir = attempt_dir / "evidencia"
    evidencia_dir.mkdir(parents=True, exist_ok=False)
    tar_path = attempt_dir / "fonte.tar"
    archive_sha = make_archive(source_repo, sha, tar_path)

    cmd = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--mount", f"type=bind,source={tar_path.resolve()},target=/fonte.tar,readonly",
        "--mount", f"type=bind,source={collector_classes.resolve()},target=/coletor,readonly",
        "--mount", f"type=bind,source={evidencia_dir.resolve()},target=/evidencia",
        "--mount", f"type=bind,source={KAN23_COLETA.resolve()},target=/roteiros,readonly",
        image_id,
        "sh", "/roteiros/piloto-surefire.sh",
    ]
    if test_filter:
        cmd.append(test_filter)

    start = datetime.now(timezone.utc)
    log_path = attempt_dir / "maven.log"
    with log_path.open("wb") as log_file:
        proc = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    finish = datetime.now(timezone.utc)

    meta = {
        "label": label,
        "mode": "surefire",
        "sha": sha,
        "position": position,
        "test_filter": test_filter,
        "image": image_id,
        "archive_sha256": archive_sha,
        "start": start.isoformat(),
        "finish": finish.isoformat(),
        "exit_code": proc.returncode,
    }
    (attempt_dir / "tentativa.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"[{label}] exit={proc.returncode} wall_host={(finish - start).total_seconds():.2f}s", flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Execucao {label} falhou com codigo {proc.returncode}")

    derived_dir = attempt_dir / "derivados"
    reconcile_cmd = [
        sys.executable, "-B", str(KAN23_COLETA / "reconciliar_t0.py"),
        str(evidencia_dir), str(derived_dir),
    ]
    if test_filter is None:
        reconcile_cmd.extend([
            "--kan15-source-ref",
            f"evidencias/KAN-28/local/{out_root.name}/{label}/derivados/resumo.json",
        ])
    run_checked(reconcile_cmd)
    return meta


def run_ordered(label: str, scenario: str, image_id: str, source_repo: Path, sha: str,
                order_file: Path, jars_dir: Path, out_root: Path):
    attempt_dir = out_root / label
    evidencia_dir = attempt_dir / "evidencia"
    evidencia_dir.mkdir(parents=True, exist_ok=False)
    tar_path = attempt_dir / "fonte.tar"
    archive_sha = make_archive(source_repo, sha, tar_path)

    cmd = [
        "docker", "run", "--rm", "--platform", "linux/amd64",
        "--mount", f"type=bind,source={tar_path.resolve()},target=/fonte.tar,readonly",
        "--mount", f"type=bind,source={order_file.resolve()},target=/ordem.txt,readonly",
        "--mount", f"type=bind,source={jars_dir.resolve()},target=/launcher-jars,readonly",
        "--mount", f"type=bind,source={BASE.resolve()},target=/roteiros,readonly",
        "--mount", f"type=bind,source={evidencia_dir.resolve()},target=/evidencia",
        image_id,
        "sh", "/roteiros/executar-ordenado.sh",
    ]

    start = datetime.now(timezone.utc)
    log_path = attempt_dir / "maven.log"
    with log_path.open("wb") as log_file:
        proc = subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    finish = datetime.now(timezone.utc)

    meta = {
        "label": label,
        "mode": "ordered_junit_launcher",
        "scenario": scenario,
        "sha": sha,
        "position": 50,
        "order_file_sha256": sha256_file(order_file),
        "image": image_id,
        "archive_sha256": archive_sha,
        "start": start.isoformat(),
        "finish": finish.isoformat(),
        "exit_code": proc.returncode,
    }
    (attempt_dir / "tentativa.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"[{label}] exit={proc.returncode} wall_host={(finish - start).total_seconds():.2f}s", flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Execucao {label} falhou com codigo {proc.returncode}")
    return meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="Nome do novo diretorio sob evidencias/KAN-28/local/")
    parser.add_argument("--fonte", type=Path, default=ROOT.parent / "KAN-10-upstream.git")
    parser.add_argument(
        "--junit-dir",
        type=Path,
        default=Path.home() / ".m2" / "repository" / "org" / "junit" / "platform",
    )
    parser.add_argument(
        "--etapas",
        nargs="+",
        default=["t0-49", "t0-50", "t1-surefire-50", "t1-ordenado-50", "t2-ordenado-50", "t3-ordenado-50"],
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_id):
        parser.error("run_id invalido")

    out_root = BASE / "local" / args.run_id
    out_root.mkdir(parents=True, exist_ok=True)
    image_id, base_label = inspect_image()
    junit_jars = find_junit_jars(args.junit_dir)
    collector_classes, jars_dir = compile_collector_in_docker(image_id, junit_jars, out_root)
    orders = export_frozen_orders(out_root)

    manifest = {
        "run_id": args.run_id,
        "image_id": image_id,
        "image_base_label": base_label,
        "source_repo": str(args.fonte.resolve()),
        "etapas": args.etapas,
        "attempts": {},
    }
    for etapa in args.etapas:
        if etapa == "t0-49":
            manifest["attempts"][etapa] = run_surefire(
                etapa, image_id, args.fonte, SHA_49, 49, collector_classes, out_root, None
            )
        elif etapa == "t0-50":
            manifest["attempts"][etapa] = run_surefire(
                etapa, image_id, args.fonte, SHA_50, 50, collector_classes, out_root, None
            )
        elif etapa == "t1-surefire-50":
            manifest["attempts"][etapa] = run_surefire(
                etapa, image_id, args.fonte, SHA_50, 50, collector_classes, out_root, SUREFIRE_CLASSES_50
            )
        elif etapa == "t1-ordenado-50":
            manifest["attempts"][etapa] = run_ordered(
                etapa, "T1", image_id, args.fonte, SHA_50, orders["T1"], jars_dir, out_root
            )
        elif etapa == "t2-ordenado-50":
            manifest["attempts"][etapa] = run_ordered(
                etapa, "T2", image_id, args.fonte, SHA_50, orders["T2"], jars_dir, out_root
            )
        elif etapa == "t3-ordenado-50":
            manifest["attempts"][etapa] = run_ordered(
                etapa, "T3", image_id, args.fonte, SHA_50, orders["T3"], jars_dir, out_root
            )
        else:
            raise ValueError(f"Etapa desconhecida: {etapa}")

    (out_root / "execucao_manifesto.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"ALL DONE: {out_root}")


if __name__ == "__main__":
    main()
