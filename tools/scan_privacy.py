#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Privacy + mojibake gate before this directory goes anywhere public.

Four things to find, because each one has bitten this project already:
  1. absolute paths / drive letters / username  -> identifies the author
  2. Cyrillic fragments                         -> encoding damage
  3. Japanese kana                              -> never legitimate here
  4. stray non-ASCII inside otherwise-English lines (glitch injection)

Chinese prose IS legitimate in this project (bilingual docs), so CJK is not
flagged wholesale - only unexpected scripts and per-line mixed anomalies.
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PATH_HINT = re.compile(r"[A-Za-z]:[\\/]|[\\/]Users[\\/]|PROJECT_OC|Jearko")
CYRILLIC = re.compile(r"[Ѐ-ӿ]+")
KANA = re.compile(r"[぀-ヿ]+")
HANGUL = re.compile(r"[가-힯]+")
# replacement char = actual corruption, never legitimate
REPL = re.compile(r"�+")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(
        description="private-data and mojibake scan before publishing")
    ap.add_argument("--root", default=ROOT,
                    help="directory to scan (default: package root)")
    args = ap.parse_args(argv)
    base = os.path.abspath(args.root)

    files = []
    for pat in ("**/*.py", "**/*.md", "**/*.csv", "**/*.txt"):
        files += [f for f in glob.glob(os.path.join(base, pat),
                                       recursive=True)]
    files = sorted(set(files))
    files = [f for f in files if "FRESH" not in f and "__pycache__" not in f]
    # Files whose job is to CONTAIN these patterns. scan_privacy.py holds the
    # patterns as regex literals; test_scanner.py holds them as fixture inputs.
    # Flagging either is guaranteed noise, every run, forever.
    EXEMPT = {os.path.join("tools", "scan_privacy.py"),
              os.path.join("tools", "test_scanner.py")}
    files = [f for f in files if os.path.relpath(f, base) not in EXEMPT]

    flagged = 0
    for f in files:
        rel = os.path.relpath(f, base)
        if os.path.getsize(f) == 0:
            continue
        try:
            text = io.open(f, encoding="utf-8").read()
        except UnicodeDecodeError:
            print("  NOT-UTF8: %s" % rel)
            flagged += 1
            continue

        # Lines that are themselves regex literals will always match: the
        # scanner looking for "D:\" will find it in the pattern that looks for
        # "D:\", and \d inside PASSED:\s*(\d+) reads as a drive letter. Check
        # the prose and the data, not the pattern library.
        PATTERN_LINE = re.compile(r"re\.(compile|search|findall|match|sub)\(")

        def scandable(line):
            return not PATTERN_LINE.search(line)

        problems = []

        hits = [p for ln in text.split("\n") if scandable(ln)
                for p in PATH_HINT.findall(ln)]
        if hits:
            problems.append("path-like %s" % sorted(set(hits))[:3])
        for label, rx in (("cyrillic", CYRILLIC), ("kana", KANA),
                          ("hangul", HANGUL), ("replacement-char", REPL)):
            m = [hit for ln in text.split("\n") if scandable(ln)
                 for hit in rx.findall(ln)]
            if m:
                problems.append("%s %s" % (label, m[:2]))

        if problems:
            flagged += 1
            print("  %s: %s" % (rel, "; ".join(problems)))

    print("")
    print("scanned %d files, flagged %d" % (len(files), flagged))
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
