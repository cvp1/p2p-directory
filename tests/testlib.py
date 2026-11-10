"""Tiny shared helpers for the standalone test scripts."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FIXTURES = os.path.join(ROOT, "fixtures")

_failed = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failed.append(name)


def done():
    if _failed:
        print(f"{len(_failed)} failed")
        sys.exit(1)
    print("all passed")


def fixture_names(kind):
    d = os.path.join(FIXTURES, kind)
    return sorted(n[:-4] for n in os.listdir(d) if n.endswith(".txt"))


def read(kind, name, ext):
    with open(os.path.join(FIXTURES, kind, name + ext), "rb") as fh:
        return fh.read()
