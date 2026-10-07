#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategy_validation — does a screen select, or does it just inherit the day?

Two CSV files in, one sheet out.

    python validate.py --picks picks.csv --universe universe.csv

  picks.csv     date,name                 one row per name the screen chose
  universe.csv  date,name,fwd_ret         every name available that day, with
                                          the forward return being judged

The number that matters is the percentile of the observed result among
random draws OF THE SAME SIZE FROM THE SAME DAY. Same-day is the point:
comparing against 'the market' lets a screen take credit for the day itself.

Nothing here recommends anything. Every figure printed is recomputable from
the two files and the seed named in the output.
"""
from __future__ import annotations

import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from strategy_validation.control import evaluate          # noqa: E402
from strategy_validation.cost import sweep                # noqa: E402
from strategy_validation.load import DataError            # noqa: E402
from strategy_validation.report import render, selfcheck  # noqa: E402

DEFAULT_COSTS = [0, 2, 5, 10, 25, 50, 100]


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="validate.py",
        description="Does this screen select, or inherit the day?")
    ap.add_argument("--picks", required=True,
                    help="CSV with columns date,name")
    ap.add_argument("--universe", required=True,
                    help="CSV with columns date,name,fwd_ret")
    ap.add_argument("--draws", type=int, default=2000,
                    help="random draws per run (default 2000)")
    ap.add_argument("--seed", type=int, default=20261007,
                    help="fix this to reproduce any report exactly")
    ap.add_argument("--variants", type=int, default=1,
                    help="how many formulations were tried before this one; "
                         "widens the gate, does not change the number")
    ap.add_argument("--costs", default="",
                    help="comma-separated bps grid, e.g. 0,5,10,50 "
                         "(default %s)" % ",".join(str(c)
                                                   for c in DEFAULT_COSTS))
    ap.add_argument("--no-cost", action="store_true",
                    help="skip the cost sensitivity block")
    ap.add_argument("--out", default="", help="also write the sheet here")
    args = ap.parse_args(argv)

    costs = None
    if args.costs:
        try:
            costs = [int(float(x)) for x in args.costs.split(",")]
        except ValueError:
            ap.error("--costs must be numbers, e.g. 0,5,10,50")

    try:
        res = evaluate(args.universe, args.picks,
                       draws=args.draws, seed=args.seed,
                       variants=args.variants)
    except DataError as exc:
        # Refuse to guess what a malformed input meant.
        print("INPUT ERROR: %s" % exc, file=sys.stderr)
        return 2

    costres = None
    if not args.no_cost:
        costres = sweep(args.universe, args.picks,
                        costs_bps=costs or DEFAULT_COSTS,
                        draws=args.draws, seed=args.seed)

    text = render(res, cost=costres, variants=args.variants,
                  input_name=os.path.basename(args.picks))

    # Last line of defence: never emit a sheet that makes a banned claim.
    hits = selfcheck(text)
    if hits:
        print("REFUSED TO PRINT: banned wording present: %s"
              % ", ".join(hits), file=sys.stderr)
        return 3

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)

    if args.out:
        d = os.path.dirname(args.out)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        io.open(args.out, "w", encoding="utf-8").write(text)
        print("[saved] %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
