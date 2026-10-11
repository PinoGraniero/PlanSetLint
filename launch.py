"""Prepare an isolated local installation, then launch the desktop app."""
import subprocess
import sys
import venv
from pathlib import Path

VERSION = "0.2.0"


def main():
    if sys.version_info < (3, 10):
        print("Serve Python 3.10 o successivo. Installa Python dal sito python.org.")
        return 1
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Questa installazione di Python non include Tkinter. Consulta GUIDA-ITALIANA.md.")
        return 1
    root = Path(__file__).resolve().parent
    environment = root / ".venv"
    interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    try:
        if not interpreter.is_file():
            print("Primo avvio: preparo PlanSetLint in questa cartella…", flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        check = subprocess.run([str(interpreter), "-c", "from importlib.metadata import version; import pypdf; import tkinter; print(version('plansetlint'))"], capture_output=True, text=True)
        if check.returncode or check.stdout.strip() != VERSION:
            print("Installazione delle dipendenze: per questo passaggio serve Internet.", flush=True)
            subprocess.run([str(interpreter), "-m", "pip", "install", str(root)], check=True, cwd=root)
        return subprocess.run([str(interpreter), "-m", "plansetlint.gui"], cwd=root).returncode
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Preparazione non riuscita: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
