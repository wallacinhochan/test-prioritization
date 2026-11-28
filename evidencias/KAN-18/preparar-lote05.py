"""Stage and execute KAN-18 Lote 05 (posicoes consecutivas 61, 62 e 63) na imagem local kan18-dirts."""
import subprocess
import sys
from importlib import import_module
from pathlib import Path

DEFAULT_IMAGE = "test-prioritization/commons-lang:kan18-dirts"


def main(upstream, out, image=DEFAULT_IMAGE):
    image_id = subprocess.check_output(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True,
    ).strip()
    base = import_module("preparar-reuso")
    base.IMAGE = image_id
    inc = import_module("preparar-incremento")
    inc.main(upstream, out, targets=(61, 62, 63), adaptar=True)
    (out / "image-id.txt").write_text(image_id + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) not in (2, 3):
        raise SystemExit("Uso: preparar-lote05.py <upstream.git> <saida> [imagem]")
    upstream, out = Path(args[0]).resolve(), Path(args[1]).resolve()
    image = args[2] if len(args) == 3 else DEFAULT_IMAGE
    main(upstream, out, image=image)
