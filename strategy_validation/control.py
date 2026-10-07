#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The same-day control group. This is the product.

Question answered: given what the screen picked, and every OTHER set of names
it could have picked that same day of the same size, is the observed result
unusual?

Why same-day: comparing against "the market" or against zero silently credits
the screen for whatever the day itself did. A screen can look brilliant in a
week when everything went up. SAME-DAY draws remove the calendar and leave
only selection - which is the only thing the screen is claiming credit for.
"""
from __future__ import annotations

import random
import statistics

from .load import DataError, load_picks, load_universe


def _index(universe):
    """date -> {name: ret}, plus names per date."""
    ret = {}
    names = {}
    for r in universe["rows"]:
        ret.setdefault(r["date"], {})[r["name"]] = r["ret"]
        names.setdefault(r["date"], []).append(r["name"])
    return ret, names


def evaluate(universe_path, picks_path, draws=2000, seed=20261007,
             variants=1):
    """Compare the client's picks against same-day random draws.

    Returns a plain dict of recomputable facts. `variants` is how many
    alternative formulations the client tried before settling on this one -
    it widens the gate, it does not change the number.
    """
    if draws < 2:
        raise DataError("draws must be >= 2 (got %r)" % draws)

    uni = load_universe(universe_path)
    picks = load_picks(picks_path)
    ret_map, name_map = _index(uni)

    picks_by_day = {}
    for p in picks:
        picks_by_day.setdefault(p["date"], []).append(p["name"])

    days = []
    observed_day_means = []
    skipped = []
    for date in sorted(picks_by_day):
        chosen = picks_by_day[date]
        avail = ret_map.get(date)
        if not avail:
            # The pick names a day the universe does not have. That is a real
            # mismatch - say so rather than dropping the day silently.
            skipped.append({"date": date, "why": "no universe rows for date"})
            continue
        missing = [n for n in chosen if n not in avail]
        if missing:
            skipped.append({"date": date,
                            "why": "picked names absent from universe: %s"
                                   % ", ".join(sorted(missing)[:5])})
            continue
        vals = [avail[n] for n in chosen]
        day_mean = sum(vals) / len(vals)
        observed_day_means.append(day_mean)
        days.append({"date": date, "k": len(chosen),
                     "pool": len(avail), "names": chosen,
                     "mean": day_mean})

    if not days:
        raise DataError(
            "no pick day could be matched against the universe "
            "(%d pick row(s), %d skipped: %s)"
            % (len(picks), len(skipped), skipped[:3]))

    observed_mean = sum(observed_day_means) / len(observed_day_means)

    rng = random.Random(seed)
    control_means = []
    for _ in range(draws):
        acc = []
        for d in days:
            pool = name_map[d["date"]]
            k = d["k"]
            if k >= len(pool):
                chosen_names = pool
            else:
                chosen_names = rng.sample(pool, k)
            vals = [ret_map[d["date"]][n] for n in chosen_names]
            acc.append(sum(vals) / len(vals))
        control_means.append(sum(acc) / len(acc))

    below = sum(1 for c in control_means if c < observed_mean)
    percentile = below / float(draws)

    return {
        "universe": universe_path,
        "picks": picks_path,
        "draws": draws,
        "seed": seed,
        "variants": variants,
        "days_used": len(days),
        "days_skipped": skipped,
        "picks_per_day": days[0]["k"] if len({d["k"] for d in days}) == 1
                        else "varies",
        "pool_per_day": days[0]["pool"],
        # Only surfaces when the available set actually changed size; a single
        # "pool/day" line would otherwise hide that the days differ.
        "pool_range": (min(d["pool"] for d in days),
                       max(d["pool"] for d in days)),
        "picks_range": (min(d["k"] for d in days),
                        max(d["k"] for d in days)),
        "total_picks": len(picks),
        "observed_mean": observed_mean,
        "control_mean": statistics.fmean(control_means),
        "control_sd": (statistics.pstdev(control_means)
                       if len(control_means) > 1 else 0.0),
        "control_min": min(control_means),
        "control_max": max(control_means),
        "percentile": percentile,
        "control_draws": control_means,
        "day_detail": days,
    }
