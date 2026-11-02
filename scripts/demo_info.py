#!/usr/bin/env python3
"""Prepare project-local observer dependencies and inspect demo results."""
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import runpy
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
MODULES = []
REPORTS = ['reports/summary.json', 'reports/counterexample.json']
SHELLS = ['scripts/run.sh']
VERIFY = 'scripts/verify.py'
PACKAGES = ROOT / "build" / "observer"


def package_paths():
    variables = {"base": str(PACKAGES), "platbase": str(PACKAGES)}
    return list(dict.fromkeys(sysconfig.get_path(name, vars=variables) for name in ("purelib", "platlib")))


def imported_dependencies():
    for path in reversed(package_paths()):
        if path not in sys.path:
            sys.path.insert(0, path)
    for name in MODULES:
        module = importlib.import_module(name)
        if not Path(module.__file__).resolve().is_relative_to(PACKAGES.resolve()):
            raise SystemExit("Observer module is not from the project dependency prefix: " + name)
    print("DEMO_PYTHON_READY: " + ", ".join(MODULES))


def check():
    if MODULES:
        expected = hashlib.sha256((ROOT / "requirements.txt").read_bytes()).hexdigest()
        marker = PACKAGES / ".requirements.sha256"
        if not marker.is_file() or marker.read_text().strip() != expected:
            raise SystemExit("Observer dependencies missing or changed; run the managed make setup target.")
        imported_dependencies()
    else:
        print("DEMO_PYTHON_READY: standard library only")


def setup():
    if MODULES:
        requirements = ROOT / "requirements.txt"
        expected = hashlib.sha256(requirements.read_bytes()).hexdigest()
        marker = PACKAGES / ".requirements.sha256"
        if not marker.is_file() or marker.read_text().strip() != expected:
            PACKAGES.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "--ignore-installed", "--prefix", str(PACKAGES), "-r", str(requirements)], check=True)
            imported_dependencies()
            marker.write_text(expected + "\n", encoding="utf-8")
    check()


def normalise():
    changed = 0
    for relative in SHELLS:
        path = ROOT / relative
        if path.is_symlink():
            raise SystemExit("Refusing linked shell input: " + relative)
        original = path.read_bytes()
        result = original.removeprefix(b"\xef\xbb\xbf").replace(b"\r\n", b"\n")
        if result != original:
            path.write_bytes(result)
            changed += 1
    print("DEMO_SHELL_INPUTS_READY changed=" + str(changed))


def report():
    for relative in REPORTS:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit("Result missing: " + relative + "; run the experiment first.")
        print("--- " + relative + " ---")
        print(json.dumps(json.loads(path.read_text()), indent=2))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("action", choices=("setup", "check", "normalise", "report", "verify"))
parser.add_argument("arguments", nargs="*")
args = parser.parse_args()
if args.action == "verify":
    check()
    sys.path.insert(0, str(ROOT / Path(VERIFY).parent))
    sys.argv = [str(ROOT / VERIFY), *args.arguments]
    runpy.run_path(str(ROOT / VERIFY), run_name="__main__")
else:
    {"setup": setup, "check": check, "normalise": normalise, "report": report}[args.action]()
