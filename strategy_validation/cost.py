#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cost sensitivity - at what cost per trade does this stop working?

A screen that only clears 8 bps is not a screen, it is a rounding error. The
client almost never modelled their own costs, and the answer they actually
need is usually "your edge disappears somewhere between here and here".
"""
from __future__ import annotations

from .load import DataError, load_picks, load_universe


def sweep(universe_path, picks_path, costs_bps=(0, 2, 5, 10, 25, 50, 100),
          draws=2000, seed=20261007):
    """Recompute the observed mean net of a round-trip cost per trade."""
    from .control import evaluate

    if not costs_bps:
        raise DataError("costs_bps must not be empty")

    uni = load_universe(universe_path)
    picks = load_picks(picks_path)

    ret_map = {}
    for r in uni["rows"]:
        ret_map.setdefault(r["date"], {})[r["name"]] = r["ret"]

    picks_by_day = {}
    for p in picks:
        picks_by_day.setdefault(p["date"], []).append(p["name"])

    rows = []
    for bps in costs_bps:
        cost = bps / 10000.0
        day_means = []
        for date, names in sorted(picks_by_day.items()):
            avail = ret_map.get(date)
            if not avail:
                continue
            vals = [avail[n] for n in names if n in avail]
            if not vals:
                continue
            # cost applies once per round trip per pick
            day_means.append(sum(v - cost for v in vals) / len(vals))
        rows.append({
            "cost_bps": bps,
            "mean_after_cost": (sum(day_means) / len(day_means))
                               if day_means else None,
            "days": len(day_means),
        })

    base = evaluate(universe_path, picks_path, draws=draws, seed=seed)
    surviving = [r for r in rows
                 if r["mean_after_cost"] is not None
                 and r["mean_after_cost"] > 0]
    return {
        "rows": rows,
        "observed_mean_gross": base["observed_mean"],
        "control_mean_gross": base["control_mean"],
        "percentile_gross": base["percentile"],
        "breakeven_bps": max([r["cost_bps"] for r in surviving], default=None),
        "costs_tested": list(costs_bps),
        "note": "breakeven is the largest tested cost at which the mean was "
                "still positive; it is a step in the tested grid, not a fit",
    }
