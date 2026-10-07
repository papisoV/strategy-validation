#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loaders. They raise rather than return empty.

The mistake this file exists to prevent: two functions named evaluate()
returned different shapes; the wrong one was passed in, the pipeline reported
zero purchases, and the render looked exactly like a genuinely quiet day.
Nothing crashed. So here, every bad input is a DataError, never a [] .
"""
from __future__ import annotations

import csv
import os
from collections import OrderedDict

UNIVERSE_COLS = {"date", "name", "fwd_ret"}
PICK_COLS = {"date", "name"}


class DataError(Exception):
    """Input was structurally wrong or empty. Never silently recover."""


def _read(path, need, what):
    if not os.path.isfile(path):
        raise DataError("%s file not found: %s" % (what, path))
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        # An empty file is not "a day with nothing in it". It is a broken file.
        raise DataError(
            "%s has a header but no data rows: %s" % (what, path))
    cols = {(k or "").strip() for k in rows[0].keys()}
    missing = need - cols
    if missing:
        raise DataError(
            "%s missing column(s) %s; need %s (got %s)"
            % (what, sorted(missing), sorted(need), sorted(cols)))
    return rows


def load_universe(path):
    """Every name available each day, with the outcome being judged.

    Returns {"rows": [...], "by_date": OrderedDict[date -> [(name, ret), ...]]}
    """
    rows = _read(path, UNIVERSE_COLS, "universe")
    out = []
    for i, r in enumerate(rows, start=2):
        date = (r.get("date") or "").strip()
        name = (r.get("name") or "").strip()
        raw = (r.get("fwd_ret") or "").strip()
        if not date or not name:
            raise DataError("universe line %d: empty date or name" % i)
        try:
            ret = float(raw)
        except ValueError:
            raise DataError(
                "universe line %d: fwd_ret is not a number (%r)" % (i, raw))
        out.append({"date": date, "name": name, "ret": ret})

    by_date = OrderedDict()
    for r in out:
        by_date.setdefault(r["date"], []).append(r["name"])
    return {"rows": out, "by_date": by_date,
            "dates": sorted(by_date), "path": path}


def load_picks(path):
    """The names the client's screen actually chose, one row per pick."""
    rows = _read(path, PICK_COLS, "picks")
    out = []
    for i, r in enumerate(rows, start=2):
        date = (r.get("date") or "").strip()
        name = (r.get("name") or "").strip()
        if not date or not name:
            raise DataError("picks line %d: empty date or name" % i)
        out.append({"date": date, "name": name})
    return [dict(p, path=path) for p in out]
