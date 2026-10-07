#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn the insider-radar backtest into a real deliverable sample.

Why real data instead of another synthetic set:
  * a buyer's first question is "have you done this before, on real numbers"
  * it is already measured and it came out NO-GO, which is exactly the case
    a validator has to handle honestly - a sample that only ever succeeds
    is marketing, not evidence

Sources, both local - no network needed:
  backtest_buys.json   Form 4 purchases, keyed by filing day
  pricecache.json      Yahoo daily closes already cached from that run

Emits the two CSVs validate.py consumes:
  universe.csv   date,name,fwd_ret   every priced name that day
  picks.csv      date,name           what the insider screen chose (>$100k)
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
BUYS = os.path.join(HERE, "backtest_buys.json")
CACHE = os.path.join(HERE, "pricecache.json")
OUT_UNI = os.path.join(HERE, "sample_universe.csv")
OUT_PICK = os.path.join(HERE, "sample_picks.csv")
HORIZON = 5          # trading days forward, matching the T+5 window
MIN_NOTIONAL = 100000  # the published screen's own floor


def load_json(p):
    if not os.path.isfile(p):
        raise SystemExit("missing %s - copy it next to this script" % p)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def series_map(cache):
    """ticker -> {yyyymmdd: close} from Yahoo epoch/close pairs."""
    out = {}
    for ticker, rows in cache.items():
        if not rows:
            continue
        m = {}
        for ts, close in rows:
            try:
                d = dt.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
            except Exception:
                continue
            if close:
                m[d] = float(close)
        if m:
            out[ticker] = m
    return out


def fwd_return(series, day, horizon):
    """Close `horizon` trading days after `day`, vs close on `day`."""
    days = sorted(series)
    if day not in series:
        return None
    try:
        i = days.index(day)
    except ValueError:
        return None
    if i + horizon >= len(days):
        return None                      # window runs past the cache
    p0 = series[days[i]]
    p1 = series[days[i + horizon]]
    if not p0:
        return None
    return (p1 - p0) / p0


def main():
    buys = load_json(BUYS)
    cache = load_json(CACHE)
    series = series_map(cache)
    print("cached tickers with series: %d" % len(series))

    uni_rows = []
    pick_rows = []
    stats = {"days": 0, "picks": 0, "picks_priced": 0}

    for day in sorted(buys):
        entries = buys[day]
        # the day's own earmark: the baseline every comparison is made against
        day_names = set()
        for e in entries:
            t = (e.get("ticker") or "").strip()
            if t and t in series:
                day_names.add(t)
        if not day_names:
            continue

        priced = 0
        for t in sorted(day_names):
            r = fwd_return(series[t], day, HORIZON)
            if r is None:
                continue
            uni_rows.append((day, t, r))
            priced += 1
        if priced == 0:
            continue

        # The screen: $100k+ the same floor the published tool uses.
        chosen = {}
        for e in entries:
            t = (e.get("ticker") or "").strip()
            try:
                notional = float(e.get("notional_usd") or 0)
            except (TypeError, ValueError):
                continue
            if notional < MIN_NOTIONAL:
                continue
            if t not in series:
                continue
            if fwd_return(series[t], day, HORIZON) is None:
                continue
            chosen[t] = max(chosen.get(t, 0.0), notional)
        for t in sorted(chosen):
            pick_rows.append((day, t))
            stats["picks_priced"] += 1
        stats["picks"] += len([1 for e in entries
                               if float(e.get("notional_usd") or 0)
                               >= MIN_NOTIONAL])
        stats["days"] += 1

    with open(OUT_UNI, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "name", "fwd_ret"])
        for d, n, r in uni_rows:
            w.writerow([d, n, "%.6f" % r])

    with open(OUT_PICK, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "name"])
        for d, n in pick_rows:
            w.writerow([d, n])

    print("days written        : %d" % stats["days"])
    print("universe rows       : %d" % len(uni_rows))
    print("pick rows (priced)  : %d" % len(pick_rows))
    print("pick rows (raw)     : %d" % stats["picks"])
    print("wrote %s" % OUT_UNI)
    print("wrote %s" % OUT_PICK)


if __name__ == "__main__":
    main()
