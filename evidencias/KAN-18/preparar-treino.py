import sys
from importlib import import_module
from pathlib import Path

if __name__ == "__main__":
    preparer = import_module("preparar-incremento")
    upstream, out = (Path(arg).resolve() for arg in sys.argv[1:])
    preparer.main(upstream, out, targets=(15, 42), runner="coletar-treino.sh", reanchor=True)
