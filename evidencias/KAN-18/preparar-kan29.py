import sys
from importlib import import_module
from pathlib import Path

if __name__ == "__main__":
    upstream, out = (Path(arg).resolve() for arg in sys.argv[1:])
    import_module("preparar-incremento").main(upstream, out, targets=(58, 59, 60), adaptar=True)
