"""Prepare and run the two-target first-parent experiment in the local Linux image."""
import csv
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = "sha256:fad87a144128c905f9ba915f61c03abe436372c2c6e26a02a18984369c42a4ea"


def main(upstream, out):
    git = ["git", f"--git-dir={upstream.resolve()}"]

    def run_git(*args):
        return subprocess.check_output([*git, *args], text=True).strip()

    def archive(sha, name):
        run_git("archive", "--format=tar", f"--output={out / (name + '.tar')}", sha)

    with (HERE / "../KAN-10/commits.csv").open(newline="", encoding="utf-8-sig") as stream:
        manifest = {int(row["position"]): row for row in csv.DictReader(stream)}
    out.mkdir(parents=True)
    for pos in (49, 50):
        entry = manifest[pos]
        sha, parent = entry["commit_sha"], entry["first_parent_sha"]
        assert parent == manifest[pos - 1]["commit_sha"] == run_git("rev-parse", f"{sha}^1")
        if pos == 49:
            archive(parent, parent)
        archive(sha, str(pos))
        if pos == 49:
            archive(sha, sha)
        (out / f"{pos}.parent").write_bytes(parent.encode() + b"\n")
        folder = out / str(pos)
        folder.mkdir()
        (folder / "sha").write_bytes(sha.encode() + b"\n")
        changes = run_git("diff", "--no-renames", "--name-status", parent, sha).splitlines()
        (folder / "diff.txt").write_text("\n".join(changes) + "\n", encoding="utf-8", newline="\n")
        classes = {"main": [], "test": []}
        for change in changes:
            if change == "M\tsrc/changes/changes.xml":
                continue
            match = re.fullmatch(r"[AM]\tsrc/(main|test)/java/([A-Za-z0-9_$/]+)\.java", change)
            if not match:
                (folder / "unsupported").touch()
                continue
            scope, path = match.groups()
            classes[scope].append(path.replace("/", "."))
        for filename, scope in (("changed-tests.txt", "test"), ("changed-prod.txt", "main")):
            (folder / filename).write_text("".join(f"{c}\n" for c in sorted(classes[scope])),
                                          encoding="utf-8", newline="\n")
    # The final state is also the cold reconstruction target for fault injection.
    archive(manifest[50]["commit_sha"], manifest[50]["commit_sha"])
    for source in (HERE / "medir-reuso.sh", HERE / "../KAN-16/DescobertaT0.java"):
        (out / source.name).write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")
    subprocess.run(["docker", "run", "--rm", "--pull", "never", "--platform", "linux/amd64",
                    "--mount", f"type=bind,source={out.resolve()},target=/out",
                    IMAGE, "sh", "/out/medir-reuso.sh"], check=True)


if __name__ == "__main__":
    main(*(Path(arg) for arg in sys.argv[1:]))
