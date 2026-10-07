#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the verdict sheet.

Wording rules learned the hard way (each ban below was paid for by a
measurement that failed to support the sentence):
  * no words that imply this recommends anything - recommend/advice/should
  * no words removed wholesale by a disproved claim: conviction,
    smart money, worth watching, alpha
  * no promises: guarantee, will return
  * every characterization must be traceable to a number printed above it

The document says what the evidence supports and where it stops. It does not
tell anyone what to do.
"""
from __future__ import annotations

import math

BANNED = [
    "recommend", "advice", "should", "guarantee", "will return",
    "conviction", "smart money", "worth watching", "alpha",
    "buy now", "signal", "outperform", "win rate",
]

# Bonferroni. If the client tried 10 formulations before settling, a 0.95 gate
# on one is not a 0.95 gate on the best of ten.
def adjusted_gate(variants, base=0.95):
    v = max(1, int(variants))
    return 1.0 - (1.0 - base) / float(v)


def verdict(result, variants=1):
    """One word from the number. No adjectives that were not measured."""
    pct = result["percentile"]
    gate = adjusted_gate(variants)
    days = result["days_used"]
    if days < 20:
        # too few days to say much of anything about anything
        return "NOT ESTABLISHED", (
            "%d pick day(s) is too few to separate selection from chance; "
            "this is a statement about sample size, not about the strategy."
            % days)
    if pct >= gate:
        return "SELECTION DETECTED", (
            "observed result sits at the %.1f%% mark of same-day random "
            "draws, above the %.3f gate for %d variant(s)."
            % (pct * 100.0, gate, max(1, variants)))
    if pct >= 0.90:
        return "NOT SHOWN", (
            "observed result is at the %.1f%% mark of same-day random draws, "
            "below the %.3f gate required here."
            % (pct * 100.0, gate))
    return "NOT SHOWN", (
        "observed result is indistinguishable from same-day random draws "
        "(%.1f%% mark)." % (pct * 100.0))


def render(result, cost=None, variants=1, input_name=""):
    L = []
    L.append("SELECTION VALIDATION REPORT")
    L.append("=" * 66)
    L.append("")
    L.append("What this document is: a comparison of what the screen picked")
    L.append("against what it COULD have picked on the same days.")
    # Deliberately not phrased as "not advice" / "not a recommendation":
    # those words are what this document is claiming NOT to be, but scanning
    # for them is a test in this package, and a disclaimer that trips the
    # scanner would be edited out by the next person rather than understood.
    L.append("It states what that comparison supports. It does not tell")
    L.append("anyone what to do with their money, and it does not predict")
    L.append("any future result.")
    L.append("")

    word, why = verdict(result, variants)
    L.append("VERDICT: %s" % word)
    L.append("  %s" % why)
    L.append("")

    L.append("INPUTS")
    L.append("  picks      : %s (%d rows)"
             % (result.get("picks", "?"), result.get("total_picks", 0)))
    L.append("  universe   : %s" % result.get("universe", "?"))
    L.append("  days used  : %d" % result["days_used"])
    if result.get("days_skipped"):
        L.append("  days skipped: %d" % len(result["days_skipped"]))
        for s in result["days_skipped"][:5]:
            L.append("     - %s: %s" % (s["date"], s["why"]))
    L.append("  picks/day  : %s" % result.get("picks_per_day"))
    L.append("  pool/day   : %s" % result.get("pool_per_day"))
    L.append("")

    L.append("THE COMPARISON")
    L.append("  Control = random draws of the same size, from the same day's")
    L.append("  list of available names. Same-day is the point: comparing")
    L.append("  against 'the market' would credit the screen for whatever")
    L.append("  the day itself did.")
    L.append("")
    L.append("  random draws        : %d (seed %s)"
             % (result["draws"], result["seed"]))
    L.append("  observed mean       : %+.4f%%"
             % (result["observed_mean"] * 100.0))
    L.append("  control mean        : %+.4f%%"
             % (result["control_mean"] * 100.0))
    L.append("  control spread (sd) : %.4f%%"
             % (result["control_sd"] * 100.0))
    L.append("  control range       : %+.4f%% to %+.4f%%"
             % (result["control_min"] * 100.0,
                result["control_max"] * 100.0))
    L.append("  observed percentile : %.4f" % result["percentile"])
    L.append("  gate (Bonferroni)   : %.4f for %d variant(s)"
             % (adjusted_gate(variants), max(1, variants)))
    L.append("")

    if cost:
        L.append("COST SENSITIVITY (applied to the picks, once per trade)")
        L.append("  %10s %14s" % ("cost bps", "mean net"))
        for row in cost["rows"]:
            if row["mean_after_cost"] is None:
                continue
            L.append("  %10.0f %+13.4f%%"
                     % (row["cost_bps"], row["mean_after_cost"] * 100.0))
        if cost.get("breakeven_bps") is not None:
            L.append("  last positive cost tested: %s bps"
                     % cost["breakeven_bps"])
        else:
            L.append("  no tested cost left the mean positive")
        L.append("  (grid only - the true breakeven lies between steps)")
        L.append("")

    L.append("WHAT THIS DOES NOT DO")
    L.append("  - does not say whether to run this strategy, or trade it")
    L.append("  - does not check look-ahead, survivorship, or fill")
    L.append("    assumptions in how the client built their own backtest")
    L.append("  - does not detect anything the input files do not contain")
    L.append("")

    if result["days_used"] < 20:
        L.append("SAMPLE SIZE")
        L.append("  %d day(s). Below 20, the percentile is close to a coin"
                 % result["days_used"])
        L.append("  flip regardless of what the screen does. Treat this run")
        L.append("  as a wiring check, not as evidence.")
        L.append("")
    elif abs(result["observed_mean"]) < 1e-12:
        L.append("NOTE")
        L.append("  observed mean is exactly zero. That usually means the")
        L.append("  input columns were not what you expected, not that the")
        L.append("  strategy is neutral.")
        L.append("")

    L.append("-" * 66)
    L.append("Every figure above is recomputable from the two input files and")
    L.append("the seed printed in this report.")
    return "\n".join(L)


def selfcheck(text):
    """Refuse to emit a report containing a banned claim."""
    low = text.lower()
    hits = [b for b in BANNED if b in low]
    return hits
