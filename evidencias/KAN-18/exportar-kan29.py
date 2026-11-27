import sys
from importlib import import_module
from pathlib import Path

if __name__ == "__main__":
    import_module("exportar-incremento").main(*(Path(arg).resolve() for arg in sys.argv[1:]), kan29=True)
