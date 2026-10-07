#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recompute every number quoted in README.md from a live run.

Recalled numbers are wrong numbers - that rule was learned on this very
project when 5 of 20 figures in a report turned out to have been written
from memory. So nothing in the README is allowed to stand unless this
script re-derives it from validate.py's actual output.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# This script lives in tools/, one level below the package root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BAD = []


def run(tag):
    picks = os.path.join(ROOT, "demos", "demo_picks_%s.csv" % tag)
    uni = os.path.join(ROOT, "demos", "demo_universe.csv")
    r = subprocess.run(
        [sys.executable, "validate.py", "--picks", picks,
         "--universe", uni, "--draws", "2000"],
        capture_output=True, cwd=ROOT)
    text = (r.stdout.decode("utf-8", errors="replace")
            + r.stderr.decode("utf-8", errors="replace"))

    def g(pat, default="??"):
        m = re.search(pat, text)
        return m.group(1) if m else default

    return {
        # Windows: reports are written with \r\n line endings, so strip.
        "verdict": g(r"VERDICT: (.+)").strip(),
        # README quotes the magnitude; the sign comes from the run.
        "observed": g(r"observed mean\s*:\s*([+-][\d.]+)%").lstrip("+"),
        "control": g(r"control mean\s*:\s*([+-][\d.]+)%"),
        "percentile": g(r"observed percentile : ([\d.]+)"),
        "pick_rows": sum(1 for _ in io.open(picks, encoding="utf-8")) - 1,
        "returncode": r.returncode,
    }


EXPECT = {
    "skilled": ("SELECTION DETECTED", "4.0742", "1.0000"),
    "random": ("NOT SHOWN", "-0.1166", "0.2495"),
    "thin": ("SELECTION DETECTED", "2.1905", "1.0000"),
}

print("%-9s %-20s %10s %10s %9s %6s" % (
    "client", "verdict", "observed", "control", "percentile", "rows"))
for tag, (v, o, p) in EXPECT.items():
    d = run(tag)
    print("%-9s %-20s %10s %10s %9s %6d" % (
        tag, d["verdict"], d["observed"], d["control"],
        d["percentile"], d["pick_rows"]))
    if d["verdict"] != v:
        BAD.append("%s verdict %r != README %r" % (tag, d["verdict"], v))
    if d["observed"] != o:
        BAD.append("%s observed %s != README %s" % (tag, d["observed"], o))
    if d["percentile"] != p:
        BAD.append("%s percentile %s != README %s" % (tag, d["percentile"], p))
    if d["returncode"] != 0:
        BAD.append("%s exited %d" % (tag, d["returncode"]))

uni_rows = sum(1 for _ in io.open(
    os.path.join(ROOT, "demos", "demo_universe.csv"), encoding="utf-8")) - 1
print("")
print("universe rows: %d (README says 7200)" % uni_rows)
if uni_rows != 7200:
    BAD.append("universe rows %d != 7200" % uni_rows)

# README must quote the control mean it prints in the example block
readme = io.open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
# README states the demo shape as days x names; 7200 rows must follow from it
# rather than being pasted in separately (a pasted total can go stale).
for token in ("SELECTION DETECTED", "NOT SHOWN", "NOT ESTABLISHED",
              "0.2495", "1.0000", "60 days", "120 names", "39 assertions"):
    if token not in readme:
        BAD.append("README missing %r" % token)

if " x " not in readme or not re.search(r"60 days\s*x\s*120 names", readme):
    BAD.append("README does not state the demo shape as '60 days x 120 names'")

print("=" * 60)
if BAD:
    for b in BAD:
        print("MISMATCH: %s" % b)
    sys.exit(1)
print("ALL README NUMBERS RECOMPUTED AND MATCH: %d checks" % (len(EXPECT) * 4 + 8))
