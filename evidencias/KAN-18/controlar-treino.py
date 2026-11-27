import shutil
import subprocess
import sys
from importlib import import_module
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = import_module("preparar-reuso")


def main(run, out):
    out.mkdir(parents=True)
    for path in (*run.glob("*.tar"), *run.glob("*.parent")):
        shutil.copyfile(path, out / path.name)
    for pos in ("15", "42"):
        folder = out / pos
        folder.mkdir()
        for name in ("classes.txt", "changed-tests.txt"):
            shutil.copyfile(run / pos / name, folder / name)
    helpers, _ = (HERE / "medir-reuso.sh").read_text(encoding="utf-8-sig").split("\ntest_maven() (", 1)
    helpers = helpers.replace("cp -a /opt/dirts-maven /t0-cache\n", "")
    helpers = helpers.replace("cp -a /opt/dirts-maven /maven-cache\n", "")
    control = (HERE / "controlar-treino.sh").read_text(encoding="utf-8-sig")
    (out / "rodar.sh").write_text(helpers + "\n" + control, encoding="utf-8", newline="\n")
    subprocess.run(["docker", "run", "--rm", "--pull", "never", "--platform", "linux/amd64",
                    "--mount", f"type=bind,source={out.resolve()},target=/out", base.IMAGE,
                    "sh", "/out/rodar.sh"], check=True)


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
