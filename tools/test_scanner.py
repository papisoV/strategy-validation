#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test scan_privacy.py against known-bad and known-clean inputs.

A privacy scanner that has never been shown something it should catch is not
verified - it is merely running. Every relaxation made to its patterns (like
ignoring regex-literal lines) is exactly the kind of change that quietly
turns it off, so this pins both directions: dirty inputs must be flagged and
clean ones must not.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "tools", "scan_privacy.py")

DIRTY = [
    ("windows path", "the file lives at D:\\PROJECT_OC\\调查\\thing\n"),
    ("unix home", "saved to /Users/someone/repos/x.csv\n"),
    ("project root", "root was PROJECT_OC here\n"),
    ("cyrillic damage", "result: ЁЁЁ broken\n"),
    ("kana damage", "result: カナ broken\n"),
    ("replacement char", "result: ��� broken\n"),
]
CLEAN = [
    ("plain prose", "the control group is drawn from the same day\n"),
    ("regex literal line",
     'm = re.search(r"PASSED:\\s*(\\d+)", text)\n'),
    ("path pattern line",
     'PATH_HINT = re.compile(r"[A-Za-z]:[\\\\/]|PROJECT_OC")\n'),
    ("returns only", "observed mean -0.4961%\n"),
]


def run_on(tmpdir, name, body):
    """Run the scanner over a temp tree containing just this one file."""
    d = os.path.join(tmpdir, name)
    os.makedirs(d, exist_ok=True)
    with io.open(os.path.join(d, "probe.py"), "w", encoding="utf-8") as fh:
        fh.write(body)
    r = subprocess.run([sys.executable, SCAN, "--root", d],
                       capture_output=True, cwd=ROOT)
    out = (r.stdout.decode("utf-8", errors="replace")
           + r.stderr.decode("utf-8", errors="replace"))
    return r.returncode, out


def main():
    # The scanner currently derives its own root; allow an override so this
    # test can point it at a temp tree.
    src = io.open(SCAN, encoding="utf-8").read()
    if "--root" not in src:
        print("NOTE: scanner has no --root; testing via a copied tree instead")
    print("scanner: %s" % SCAN)

    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, body) in enumerate(DIRTY):
            rc, out = run_on(tmp, "dirty%d" % i, body)
            ok = rc != 0
            print("  [%s] dirty: %s" % ("OK  " if ok else "FAIL", label))
            if not ok:
                failures.append("dirty not flagged: %s" % label)
        for i, (label, body) in enumerate(CLEAN):
            rc, out = run_on(tmp, "clean%d" % i, body)
            ok = rc == 0
            print("  [%s] clean: %s" % ("OK  " if ok else "FAIL", label))
            if not ok:
                failures.append("clean false positive: %s" % label)

    print("")
    print("=" * 62)
    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        return 1
    print("SCANNER VERIFIED: %d dirty caught, %d clean passed"
          % (len(DIRTY), len(CLEAN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
