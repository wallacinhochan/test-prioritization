"""Registra fases físicas sequenciais em um relógio monotônico comum."""

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


FASES = {
    "T0": ("prepare", "runner", "reports"),
    "T1": ("prepare", "selection", "runner", "reports"),
    "T2": ("prepare", "selection", "features", "inference", "runner", "reports"),
    "T3": ("prepare", "selection", "features", "inference", "runner", "reports"),
}


def medir(plano, pasta):
    fases = plano["phases"]
    if tuple(f["phase"] for f in fases) != FASES[plano["scenario"]]:
        raise ValueError("fases ausentes ou fora da ordem do cenário")
    if any(not isinstance(f["argv"], list) or not f["argv"]
           or not all(isinstance(a, str) for a in f["argv"]) for f in fases):
        raise ValueError("cada fase requer um vetor de argumentos")
    inicio = time.monotonic_ns()
    pasta.mkdir()
    resultado = {"plan": plano, "started_at": datetime.now(timezone.utc).isoformat(),
                 "phases": [], "complete": False}
    try:
        for fase in fases:
            log = pasta / (fase["phase"] + ".log")
            with log.open("xb") as arquivo:
                antes = time.monotonic_ns() - inicio
                processo = subprocess.run(fase["argv"], stdout=arquivo, stderr=subprocess.STDOUT)
                depois = time.monotonic_ns() - inicio
            resultado["phases"].append(
                {"phase": fase["phase"], "start_ns": antes, "end_ns": depois,
                 "duration_ms": (depois - antes + 500_000) // 1_000_000,
                 "returncode": processo.returncode, "log": log.name})
            if processo.returncode:
                return processo.returncode
        resultado["complete"] = True
        return 0
    except OSError as erro:
        resultado["error"] = str(erro)
        raise
    finally:
        resultado["wall_ns"] = time.monotonic_ns() - inicio
        resultado["finished_at"] = datetime.now(timezone.utc).isoformat()
        (pasta / "fases.json").write_text(json.dumps(resultado, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plano", type=Path)
    parser.add_argument("saida", type=Path)
    args = parser.parse_args()
    raise SystemExit(medir(json.loads(args.plano.read_text(encoding="utf-8")), args.saida))
