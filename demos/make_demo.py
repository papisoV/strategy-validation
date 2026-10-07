#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a realistic-size demo pair so the estimator can actually speak.

The 5-day fixture only proves wiring - below 20 days the report says
NOT ESTABLISHED, which is correct but does not exercise the verdict path.
So: 60 trading days, 120 names, three clients.

  client_A  genuine skill: picks get a real edge, then we subtract spreads
  client_B  no skill: picks are random from the pool every day
  client_C  has edge before costs, none after costs

The point of the demo is that the tool must be able to say NO. A validator
that only ever says yes is decoration.
"""
from __future__ import annotations

import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
# This file lives IN demos/, so the output dir is HERE, not HERE/demos -
# nesting it produced demos/demos/ and duplicated every csv.
OUT = HERE
os.makedirs(OUT, exist_ok=True)

DAYS = 60
POOL = 120
K = 5
SEED = 424242


def dates(n):
    """Synthetic consecutive trading dates - no weekend semantics needed."""
    import datetime
    d = datetime.date(2024, 1, 2)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def main():
    rng = random.Random(SEED)
    days = dates(DAYS)
    names = ["N%03d" % i for i in range(POOL)]

    uni_rows = []
    base = {}
    for di, day in enumerate(days):
        # a market-wide drift so that comparing against "the market" would
        # be flattering - this is exactly what same-day control removes
        drift = 0.0004 * (di % 7 - 3)
        for n in names:
            r = drift + rng.gauss(0, 0.02)
            base[(day, n)] = r
            uni_rows.append({"date": day, "name": n, "fwd_ret": r})

    uni_path = os.path.join(OUT, "demo_universe.csv")
    with open(uni_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["date", "name", "fwd_ret"])
        w.writeheader()
        for r in uni_rows:
            w.writerow({"date": r["date"], "name": r["name"],
                        "fwd_ret": "%.6f" % r["fwd_ret"]})

    def write_picks(tag, chooser):
        rows = []
        for day in days:
            for n in chooser(day):
                rows.append({"date": day, "name": n})
        p = os.path.join(OUT, "demo_picks_%s.csv" % tag)
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, ["date", "name"])
            w.writeheader()
            w.writerows(rows)
        return p

    # A: skilled - has information about tomorrow within the day
    def chooser_a(day):
        scored = sorted(names,
                        key=lambda n: -(base[(day, n)] + rng.gauss(0, 0.004)))
        return scored[:K]

    # B: random - no information at all
    def chooser_b(day):
        return rng.sample(names, K)

    # C: tiny edge that survives 2bps but not 25bps
    def chooser_c(day):
        scored = sorted(names,
                        key=lambda n: -(base[(day, n)] + rng.gauss(0, 0.03)))
        return scored[:K]

    pa = write_picks("skilled", chooser_a)
    pb = write_picks("random", chooser_b)
    pc = write_picks("thin", chooser_c)

    print("universe rows: %d (%d days x %d names)" % (len(uni_rows), DAYS, POOL))
    print("wrote %s" % uni_path)
    for p in (pa, pb, pc):
        print("wrote %s" % p)


if __name__ == "__main__":
    main()
