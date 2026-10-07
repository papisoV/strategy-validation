#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fresh-copy verification.

Everything so far ran in the working directory, where __pycache__, fixture
files left over from earlier runs, and absolute paths can hide breakage. The
insider-radar repo passed all its tests and then crashed on a fresh clone
because the scratch dir was gitignored and did not exist. So: copy only what
a real distribution would contain, into a clean tree, and run there.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(os.path.dirname(ROOT), "strategy-validation-FRESH")
SKIP_DIRS = {"__pycache__", ".omc", ".git", "_fixtures"}
KEEP_EXT = {".py", ".md", ".csv", ".txt"}


def wanted(rel_parts):
    if any(p in SKIP_DIRS for p in rel_parts):
        return False
    name = rel_parts[-1]
    return os.path.splitext(name)[1] in KEEP_EXT


def main():
    if os.path.isdir(DEST):
        # Only ever wipe a tree that looks like one we created. This tool does
        # an rmtree, so it must not be trusted with an arbitrary directory.
        marker = os.path.join(DEST, "validate.py")
        here = os.path.join(DEST, "README.md")
        if not (os.path.isfile(marker) and os.path.isfile(here)):
            print("refusing to clear %s: not a strategy-validation tree"
                  % DEST)
            return 2
        shutil.rmtree(DEST, ignore_errors=True)
    os.makedirs(DEST, exist_ok=True)

    copied = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        parts = [] if rel == "." else rel.split(os.sep)
        if any(p in SKIP_DIRS for p in parts):
            continue
        for f in filenames:
            if os.path.splitext(f)[1] not in KEEP_EXT:
                continue
            src = os.path.join(dirpath, f)
            dst = os.path.join(DEST, *(parts + [f]))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1

    print("copied %d files -> %s" % (copied, DEST))
    print("")

    steps = [
        ("tests", [sys.executable, "tests/test_strategy_validation.py"]),
        ("generate demo", [sys.executable, "demos/make_demo.py"]),
        ("validate skilled",
         [sys.executable, "validate.py",
          "--picks", "demos/demo_picks_skilled.csv",
          "--universe", "demos/demo_universe.csv", "--draws", "2000"]),
        ("validate random",
         [sys.executable, "validate.py",
          "--picks", "demos/demo_picks_random.csv",
          "--universe", "demos/demo_universe.csv", "--draws", "2000"]),
        ("recheck readme", [sys.executable, "tools/check_readme.py"]),
    ]

    failures = []
    for label, cmd in steps:
        r = subprocess.run(cmd, cwd=DEST, capture_output=True)
        out = (r.stdout.decode("utf-8", errors="replace")
               + r.stderr.decode("utf-8", errors="replace"))
        ok = r.returncode == 0
        print("[%s] %s" % ("OK  " if ok else "FAIL", label))
        if not ok:
            failures.append(label)
            tail = "\n".join(out.strip().split("\n")[-12:])
            print("     " + tail.replace("\n", "\n     "))
        # surface the headline result even on success
        for line in out.split("\n"):
            if line.startswith(("PASSED:", "VERDICT:", "ALL README",
                                "MISMATCH", "Traceback")):
                print("     %s" % line.strip())

    print("")
    print("=" * 62)
    if failures:
        print("FRESH COPY FAILED: %s" % ", ".join(failures))
        return 1
    print("FRESH COPY CLEAN: all %d steps passed in %s" % (len(steps), DEST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
