#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recompute every figure quoted in SAMPLE.md from the files it ships.

SAMPLE.md is the sales artifact, which makes it the most dangerous file in
the repo: it is where a stale or flattering number would do the most damage
and be least noticed. So each claim is re-derived here rather than trusted.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = []


def run(args):
    r = subprocess.run([sys.executable] + args, cwd=ROOT,
                       capture_output=True)
    return (r.returncode,
            r.stdout.decode("utf-8", errors="replace")
            + r.stderr.decode("utf-8", errors="replace"))


print("=== regenerating the shipped report ===")
rc, out = run(["validate.py", "--picks", "demos/sample_picks.csv",
               "--universe", "demos/sample_universe.csv",
               "--draws", "2000", "--costs", "0,2,5,10,25,50,100",
               "--out", "sample-report.txt"])
if rc != 0:
    BAD.append("validate.py exited %d" % rc)
print("exit=%d" % rc)

report = io.open(os.path.join(ROOT, "sample-report.txt"),
                 encoding="utf-8").read()
sample_md = io.open(os.path.join(ROOT, "SAMPLE.md"), encoding="utf-8").read()


def g(pat, text=report, default=None):
    m = re.search(pat, text)
    return m.group(1).strip() if m else default


fac = {
    "verdict": g(r"VERDICT: (.+)"),
    "observed": g(r"observed mean\s*:\s*([+-][\d.]+)%"),
    "control": g(r"control mean\s*:\s*([+-][\d.]+)%"),
    "percentile": g(r"observed percentile : ([\d.]+)"),
    "days": g(r"days used\s*:\s*(\d+)"),
    "pick_rows": g(r"picks\s*:\s*\S+ \((\d+) rows\)"),
}
print("  %s" % fac)

# row counts straight from the csv files
uni_rows = sum(1 for _ in io.open(
    os.path.join(ROOT, "demos", "sample_universe.csv"),
    encoding="utf-8")) - 1
pick_rows = sum(1 for _ in io.open(
    os.path.join(ROOT, "demos", "sample_picks.csv"),
    encoding="utf-8")) - 1
uni_names = len({ln.split(",")[1] for ln in io.open(
    os.path.join(ROOT, "demos", "sample_universe.csv"),
    encoding="utf-8").read().strip().split("\n")[1:]})
print("  universe rows=%d unique names=%d pick rows=%d"
      % (uni_rows, uni_names, pick_rows))

# per-day picks range parsed from the report table
picks_col = re.findall(r"^\s+(\d{4}-\d{2}-\d{2})\s+(\d+)\s+(\d+)\s+", report,
                       re.M)
if picks_col:
    ks = [int(x[1]) for x in picks_col]
    pools = [int(x[2]) for x in picks_col]
    print("  per-day picks %d-%d, pool %d-%d, rows %d"
          % (min(ks), max(ks), min(pools), max(pools), len(picks_col)))
else:
    BAD.append("could not parse the per-day table from the report")

CHECK = [
    ("days used 8", fac["days"] == "8", str(fac["days"])),
    ("99 pick rows", pick_rows == 99, str(pick_rows)),
    ("pick rows reported == csv",
     fac["pick_rows"] == str(pick_rows),
     "%s vs %s" % (fac["pick_rows"], pick_rows)),
    ("verdict NOT ESTABLISHED", fac["verdict"] == "NOT ESTABLISHED",
     str(fac["verdict"])),
    ("observed -0.4961", fac["observed"] == "-0.4961", str(fac["observed"])),
    ("control -0.4096", fac["control"] == "-0.4096", str(fac["control"])),
    ("percentile 0.4775", fac["percentile"] == "0.4775",
     str(fac["percentile"])),
    ("picks vary 6-22", (min(ks), max(ks)) == (6, 22),
     "%d-%d" % (min(ks), max(ks))),
    ("pool varies 25-59", (min(pools), max(pools)) == (25, 59),
     "%d-%d" % (min(pools), max(pools))),
    ("197 unique names priced", uni_names == 197, str(uni_names)),
    ("293 universe rows", uni_rows == 293, str(uni_rows)),
]

for label, ok, got in CHECK:
    print("  [%s] %-32s %s" % ("OK  " if ok else "FAIL", label, got))
    if not ok:
        BAD.append(label + " -> " + got)

# SAMPLE.md must contain the numbers the report actually produced
for tok in (fac["observed"], fac["control"], fac["percentile"],
            "NOT ESTABLISHED", "197", "99", "293"):
    if tok not in sample_md:
        BAD.append("SAMPLE.md missing %r" % tok)

# SAMPLE.md must not contain a banned word
for banned in ("recommend", "guarantee", "conviction", "smart money",
               "worth watching", "win rate"):
    if banned in sample_md.lower():
        BAD.append("SAMPLE.md contains banned %r" % banned)

print("")
print("=" * 62)
if BAD:
    for b in BAD:
        print("MISMATCH: %s" % b)
    sys.exit(1)
print("SAMPLE.md CHECKS PASS: %d facts recomputed" % (len(CHECK) + 8))
