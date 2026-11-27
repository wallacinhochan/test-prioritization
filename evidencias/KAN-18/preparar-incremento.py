"""Stage a chronological selection-only batch using the measured KAN-18 shell helpers."""
import csv
import re
import subprocess
import sys
from pathlib import Path
from importlib import import_module

base = import_module("preparar-reuso")
HERE = Path(__file__).resolve().parent


def main(upstream, out, *, targets=(47, 48), runner="coletar-incremento.sh", reanchor=False, adaptar=False):
    git = ["git", f"--git-dir={upstream.resolve()}"]
    with (HERE / "../KAN-10/commits.csv").open(encoding="utf-8-sig", newline="") as stream:
        history = {int(row["position"]): row for row in csv.DictReader(stream)}
    out.mkdir(parents=True)

    def put(path, text):
        path.write_text(text, encoding="utf-8", newline="\n")

    for pos in targets:
        sha = history[pos]["commit_sha"]
        parent = history[pos]["first_parent_sha"]
        name = str(pos)
        assert subprocess.check_output([*git, "rev-parse", f"{sha}^1"], text=True).strip() == parent

        subprocess.run([*git, "archive", "--format=tar", f"--output={out / (name + '.tar')}", sha],
                       check=True)
        if not reanchor:
            assert parent == history[pos - 1]["commit_sha"]
        subprocess.run([*git, "archive", "--format=tar", f"--output={out / (parent + '.tar')}", parent],
                       check=True)
        put(out / f"{pos}.parent", parent + "\n")
        target = out / name
        target.mkdir()
        put(target / "sha", sha + "\n")
        diff = subprocess.check_output([*git, "diff", "--no-renames", "--name-status", parent, sha],
                                       text=True)
        put(target / "diff.txt", diff)
        changes = {"main": [], "test": []}
        for row in diff.splitlines():
            if row == "M\tsrc/changes/changes.xml":
                continue
            match = re.fullmatch(r"[AM]\tsrc/(main|test)/java/([A-Za-z0-9_$/]+)\.java", row)
            if match is None:
                (target / "unsupported").touch()
            else:
                scope, clazz = match.groups()
                changes[scope].append(clazz.replace("/", "."))
        if not any(changes.values()):
            (target / "unsupported").touch()
        for scope, file in (("main", "changed-prod.txt"), ("test", "changed-tests.txt")):
            put(target / file, "".join(clazz + "\n" for clazz in sorted(changes[scope])))
    script = (HERE / "medir-reuso.sh").read_text(encoding="utf-8-sig")
    helpers, suffix = script.split("\ntest_maven() (", 1)
    assert "initialize()" in helpers and "expand_roots()" in helpers and "for pos in 49 50" in suffix
    # T0 is an inventory reference here, so its physical Maven cache is unnecessary.
    helpers = helpers.replace("cp -a /opt/dirts-maven /t0-cache\n", "")
    shell = (HERE / runner).read_text(encoding="utf-8-sig")
    if adaptar:
        assert runner == "coletar-incremento.sh" and not reanchor
        assert tuple(targets) == tuple(range(targets[0], targets[-1] + 1))
        shell = shell.replace("/out/47.parent", f"/out/{targets[0]}.parent")
        shell = shell.replace("for pos in 47 48;", "for pos in " + " ".join(map(str, targets)) + ";")
        final = targets[-1]
        shell += f"""
cd /work/state
if valid_state "$(cat /out/{final}/sha)"; then
    tar -cf /out/estado-{final}.tar .dirts
    cp /work/state.sha /out/estado-{final}.sha
    cp /work/state.hashes /out/estado-{final}.hashes
fi
"""
    put(out / "rodar.sh", helpers + "\n" + shell)
    put(out / "DescobertaT0.java", (HERE / "../KAN-16/DescobertaT0.java").read_text(encoding="utf-8-sig"))
    subprocess.run(["docker", "run", "--rm", "--pull", "never", "--platform", "linux/amd64",
                    "--mount", f"type=bind,source={out.resolve()},target=/out",
                    base.IMAGE, "sh", "/out/rodar.sh"], check=True)


if __name__ == "__main__":
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
