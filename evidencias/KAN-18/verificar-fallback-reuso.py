"""Check the fallback dispatch with the same measured runner and an instrumented Maven."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from importlib import import_module

IMAGE = import_module("preparar-reuso").IMAGE


def main(measured, out):
    assert measured.resolve() != out.resolve()
    out.mkdir(parents=True)
    for path in (*measured.glob("*.tar"), *measured.glob("*.parent"), measured / "medir-reuso.sh"):
        shutil.copyfile(path, out / path.name)
    for position in ("49", "50"):
        folder = out / position
        folder.mkdir()
        shutil.copyfile(measured / position / "sha", folder / "sha")
    # Configuration fallback is injected separately from a selector failure.
    (out / "50/unsupported").touch()
    bin_dir = out / "bin"
    bin_dir.mkdir()
    (bin_dir / "mvn").write_bytes(b"""#!/bin/sh
base=${PWD##*/}
case "$*" in
  *method_level_select*) printf '%s\n' 'selector failure injected'; exit 47 ;;
  *' test')
    if [ "$base" = source ]; then
      base=source-49
      if [ -e /out/argv-source-49.txt ]; then base=source-50; fi
    fi
    printf '%s\n' "$@" > "/out/argv-$base.txt"
    ;;
  *) exit 48 ;;
esac
""")
    command = ["docker", "run", "--rm", "--pull", "never", "--platform", "linux/amd64",
               "--mount", f"type=bind,source={out.resolve()},target=/out", IMAGE, "sh", "-c",
               'mkdir /fault-bin && cp /out/bin/mvn /fault-bin && chmod +x /fault-bin/mvn && '
               'PATH=/fault-bin:$PATH sh /out/medir-reuso.sh']
    completed = subprocess.run(command)
    # The synthetic Maven also fails at the first isolated control.
    assert completed.returncode == 1, completed.returncode
    with (out / "tempos.csv").open(newline="") as source:
        stages = {row["fase"]: int(row["rc"]) for row in csv.DictReader(source)}
    assert stages["inicializacao"] == stages["reconstrucao_49"] == 1
    assert stages["reuso_test_49"] == stages["reuso_test_50"] == 0
    assert stages["dirts_pai_isolado_49"] == 1
    results = {}
    for pos, reason in (("49", "estado_invalido"), ("50", "diff_nao_suportado")):
        assert (out / pos / "fallback").read_text().strip() == reason
        # Separate target trees and an unfiltered invocation in both arms.
        args = (out / f"argv-t0-{pos}.txt").read_text().splitlines()
        reuso_args = (out / f"argv-source-{pos}.txt").read_text().splitlines()
        assert all(not arg.startswith("-Dtest") for arg in args + reuso_args)
        assert args[-1] == reuso_args[-1] == "test"
        results[pos] = {"motivo": reason, "argumentos_maven": reuso_args}
    print(json.dumps({"tipo": "Maven instrumentado, sem executar a suíte", "revisoes": results, "retornos": stages},
                     indent=2))


if __name__ == "__main__":
    main(*(Path(arg) for arg in sys.argv[1:]))
