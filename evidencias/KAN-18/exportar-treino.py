import sys
from importlib import import_module
from pathlib import Path

if __name__ == "__main__":
    exporter = import_module("exportar-incremento")
    run, control, upstream, out = (Path(arg).resolve() for arg in sys.argv[1:])
    exporter.main(run, upstream, out, control=control)
