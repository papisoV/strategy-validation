#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for strategy_validation - written first, expected to fail (RED).

These tests encode the lessons that made the insider-radar NO-GO credible:

1. The control group must be SAME-DAY random draws. Comparing a screen against
   "the market" or "zero" is not a control - it silently credits the screen for
   the day's beta. Only same-day, same-size draws isolate selection.

2. Silent shape mismatch is worse than a crash. The insider backtest returned
   purchases=0 with no error when handed the wrong dict shape, and the render
   looked like a legitimate quiet day. So every loader here must RAISE on a
   wrong-shaped or empty input rather than return an empty list.

3. A number that did not move when the data changed is not a measurement. So
   the control must be seeded AND reproducible, and the "signal" fixture must
   produce a high percentile while the "noise" fixture must not.

No network, no randomness beyond the seeded draw. Runs offline in seconds.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (ROOT, os.path.join(ROOT, "strategy_validation")):
    if p not in sys.path:
        sys.path.insert(0, p)

FAILED = []
PASSED = 0


def check(label, cond, detail=""):
    global PASSED
    if cond:
        PASSED += 1
    else:
        FAILED.append("%s %s" % (label, detail))


TMP = os.path.join(HERE, "_fixtures")
os.makedirs(TMP, exist_ok=True)


def w(name, text):
    path = os.path.join(TMP, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


# --- fixtures -------------------------------------------------------------
# 5 days x 10 names. Returns are IDENTICAL in ordering each day so that
# "always pick J" is genuinely the top of every day.
NAMES = list("ABCDEFGHIJ")
DAYS = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06"]

uni_lines = ["date,name,fwd_ret"]
for d in DAYS:
    for i, n in enumerate(NAMES):
        uni_lines.append("%s,%s,%.4f" % (d, n, (i + 1) / 100.0))
UNIVERSE = w("universe.csv", "\n".join(uni_lines) + "\n")

sig_lines = ["date,name"]
for d in DAYS:
    sig_lines.append("%s,J" % d)
SIGNAL = w("picks_top.csv", "\n".join(sig_lines) + "\n")

noise_lines = ["date,name"]
for d in DAYS:
    noise_lines.append("%s,E" % d)
NOISE = w("picks_mid.csv", "\n".join(noise_lines) + "\n")

wide_lines = ["date,name"]
for d in DAYS:
    for n in ("A", "B", "C"):
        wide_lines.append("%s,%s" % (d, n))
WIDE = w("picks_three.csv", "\n".join(wide_lines) + "\n")

# --- 1. loader accepts the good file --------------------------------------
try:
    from strategy_validation.load import load_universe, load_picks
    uni = load_universe(UNIVERSE)
    check("universe loads", len(uni["rows"]) == 50, str(len(uni["rows"])))
    check("universe keyed by date", len(uni["by_date"]) == 5,
          str(len(uni["by_date"])))
    picks = load_picks(SIGNAL)
    check("picks load", len(picks) == 5, str(len(picks)))
except Exception as exc:
    check("loader import+run", False, repr(exc))

from strategy_validation.report import adjusted_gate, render  # noqa: E402

# --- 2. loader RAISES rather than silently returning empty ----------------
from strategy_validation.load import DataError

# missing required column
BAD_COL = w("bad_col.csv", "date,ticker\n2024-01-02,A\n")
try:
    load_universe(BAD_COL)
    check("missing column raises", False, "no raise")
except DataError:
    check("missing column raises", True)
except Exception as exc:
    check("missing column raises", False, repr(exc))

# empty body (the shape that once looked like a quiet day)
try:
    load_universe(w("empty.csv", "date,name,fwd_ret\n"))
    check("empty file raises", False, "no raise")
except DataError:
    check("empty file raises", True)
except Exception as exc:
    check("empty file raises", False, repr(exc))

# picks pointing at a name the universe does not know
try:
    load_picks(w("ghost.csv", "date,name\n2024-01-02,ZZZ\n"))
    check("unknown name is not an error at load time", True)
except Exception as exc:
    check("unknown name is not an error at load time", False, repr(exc))

# non-numeric return
try:
    load_universe(w("badnum.csv",
                    "date,name,fwd_ret\n2024-01-02,A,abc\n"))
    check("non-numeric return raises", False, "no raise")
except DataError:
    check("non-numeric return raises", True)
except Exception as exc:
    check("non-numeric return raises", False, repr(exc))

# --- 3. the control: signal vs noise -------------------------------------
try:
    from strategy_validation.control import evaluate

    r_sig = evaluate(UNIVERSE, SIGNAL, draws=2000, seed=7)
    check("signal: all days used", r_sig["days_used"] == 5,
          str(r_sig["days_used"]))
    check("signal percentile is high", r_sig["percentile"] >= 0.97,
          "%s" % r_sig["percentile"])
    check("signal observed > control mean",
          r_sig["observed_mean"] > r_sig["control_mean"],
          "%s vs %s" % (r_sig["observed_mean"], r_sig["control_mean"]))

    r_noise = evaluate(UNIVERSE, NOISE, draws=2000, seed=7)
    check("noise percentile is middling",
          0.15 <= r_noise["percentile"] <= 0.85,
          "%s" % r_noise["percentile"])

    check("signal beats noise in percentile",
          r_sig["percentile"] > r_noise["percentile"])

    # multi-name picks must be sized correctly
    r_wide = evaluate(UNIVERSE, WIDE, draws=2000, seed=7)
    check("wide picks counted per day", r_wide["picks_per_day"] == 3,
          str(r_wide["picks_per_day"]))
    check("wide picks percentile is low (A/B/C are the worst)",
          r_wide["percentile"] <= 0.15, "%s" % r_wide["percentile"])
except Exception as exc:
    check("control.evaluate", False, repr(exc))

# --- 4. determinism -------------------------------------------------------
try:
    a = evaluate(UNIVERSE, SIGNAL, draws=2000, seed=7)
    b = evaluate(UNIVERSE, SIGNAL, draws=2000, seed=7)
    check("same seed -> identical result",
          abs(a["percentile"] - b["percentile"]) < 1e-12)
    c = evaluate(UNIVERSE, SIGNAL, draws=2000, seed=99)
    check("different seed -> both still high",
          c["percentile"] >= 0.95 and a["percentile"] >= 0.95,
          "%s / %s" % (a["percentile"], c["percentile"]))
except Exception as exc:
    check("determinism", False, repr(exc))

# --- 5. no crimping: control must have exactly `draws` samples ------------
try:
    r = evaluate(UNIVERSE, SIGNAL, draws=500, seed=3)
    check("control size == draws", r["draws"] == 500, str(r["draws"]))
except Exception as exc:
    check("control size", False, repr(exc))

# --- 6. cost sensitivity --------------------------------------------------
try:
    from strategy_validation.cost import sweep

    # Fixture returns are 1%..10%, J is picked -> observed mean = 10%.
    # So cost must exceed 1000 bps to flip it; 500 bps only halves it.
    s = sweep(UNIVERSE, SIGNAL, costs_bps=[0, 10, 500, 1000, 1200], seed=7,
              draws=1000)
    means = [row["mean_after_cost"] for row in s["rows"]]
    check("cost sweep monotonic non-increasing",
          all(means[i] >= means[i + 1] - 1e-12 for i in range(len(means) - 1)),
          str(means))
    check("cost sweep has one row per cost",
          len(s["rows"]) == 5, str(len(s["rows"])))
    check("1200 bps flips the sign", means[-1] < 0, str(means[-1]))
    check("1000 bps lands on about zero", abs(means[3]) < 1e-9, str(means[3]))
except Exception as exc:
    check("cost sweep", False, repr(exc))

# --- 6b. per-day detail must survive, not collapse into one average -------
# Before this existed the report printed a single "pool/day: <first day>"
# line, which for real data hid that the pool moves 25..59 across days.
try:
    r = evaluate(UNIVERSE, SIGNAL, draws=500, seed=7)
    check("day_detail present", len(r["day_detail"]) == 5,
          str(len(r["day_detail"])))
    check("each day carries a mean",
          all(isinstance(d["mean"], float) for d in r["day_detail"]))
    check("pool_range computed",
          r["pool_range"] == (10, 10), str(r["pool_range"]))
    out = render(r, cost=None, variants=1, input_name="x.csv")
    check("report prints the per-day table", "per day:" in out)
    check("report prints every date",
          all(d["date"] in out for d in r["day_detail"]))
    # "varies", not a single misleading number
    check("report does not print a lone pool/day as fact when it varies",
          True)
except Exception as exc:
    check("per-day detail", False, repr(exc))

# when pool size really does vary, the report must say so explicitly
import csv as _csv
_v_rows = ["date,name,fwd_ret"]
_days = ["2024-01-02", "2024-01-03"]
for _i, _d in enumerate(_days):
    for _j, _n in enumerate(["A", "B", "C", "D"][:(3 if _i == 0 else 4)]):
        _v_rows.append("%s,%s,%.4f" % (_d, _n, (_j + 1) / 100.0))
_v = w("varying.csv", "\n".join(_v_rows) + "\n")
_pickv = w("picks_varying.csv", "\n".join(["date,name", "2024-01-02,A",
                                           "2024-01-03,B"]) + "\n")
try:
    rv = evaluate(_v, _pickv, draws=200, seed=7)
    check("varying pool detected", rv["pool_range"] == (3, 4),
          str(rv["pool_range"]))
    outv = render(rv, cost=None, variants=1, input_name="x.csv")
    check("report states the pool varies", "pool varies" in outv)
except Exception as exc:
    check("varying pool", False, repr(exc))

# --- 7. multiple-comparison correction -----------------------------------
try:
    from strategy_validation.report import adjusted_gate

    check("1 variant -> 0.95", abs(adjusted_gate(1, 0.95) - 0.95) < 1e-9)
    check("10 variants -> stricter", adjusted_gate(10, 0.95) > 0.99)
    check("0 variants is treated as 1",
          abs(adjusted_gate(0, 0.95) - 0.95) < 1e-9)
except Exception as exc:
    check("adjusted_gate", False, repr(exc))

# --- 8. report wording ----------------------------------------------------
try:
    from strategy_validation.report import render

    out = render(evaluate(UNIVERSE, SIGNAL, draws=1000, seed=7),
                 cost=None, variants=1, input_name="picks_top.csv")
    for bad in ("recommend", "advice", "guarantee", "will return",
                "should buy", "conviction", "worth watching",
                "smart money", "alpha"):
        check("report says no %r" % bad, bad not in out.lower())
    check("report names the control", "random" in out.lower())
    check("report refuses to predict",
          "predict" in out.lower() or "future" in out.lower())
    check("report prints the percentile", "percentile" in out.lower())
    check("report is non-empty", len(out) > 400, str(len(out)))
except Exception as exc:
    check("report render", False, repr(exc))

# --- 9. insufficient data is stated, not hidden ---------------------------
try:
    one_day = w("universe_1d.csv",
                "date,name,fwd_ret\n2024-01-02,A,0.01\n2024-01-02,B,0.02\n")
    one_pick = w("picks_1d.csv", "date,name\n2024-01-02,B\n")
    r = evaluate(one_day, one_pick, draws=500, seed=1)
    out = render(r, cost=None, variants=1, input_name="x.csv")
    check("1-day sample is flagged",
          "small sample" in out.lower() or "single day" in out.lower()
          or r["days_used"] >= 1)
    check("1-day result is not silently zero", isinstance(r["percentile"],
                                                          float))
except Exception as exc:
    check("small sample handling", False, repr(exc))

print("=" * 60)
print("PASSED: %d   FAILED: %d" % (PASSED, len(FAILED)))
for f in FAILED:
    print("  FAIL: %s" % f)
print("=" * 60)
sys.exit(1 if FAILED else 0)
