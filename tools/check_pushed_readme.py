#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the README GitHub actually serves, not the one on disk.

Local files being clean does not prove what arrived. Git apply + transport
can and does mangle encodings, and a mojibake'd public README is the kind of
thing nobody tells you about. So fetch it back through the API and scan it.
"""
from __future__ import annotations

import base64
import io
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

REPO = "papisoV/strategy-validation"


def main():
    r = subprocess.run(
        ["gh", "api", "repos/%s/readme" % REPO, "--jq", ".content"],
        capture_output=True)
    if r.returncode != 0:
        print("FETCH FAILED: %s"
              % r.stderr.decode("utf-8", errors="replace")[:300])
        return 1
    raw = "".join(r.stdout.decode("utf-8", errors="replace").split())
    try:
        text = base64.b64decode(raw).decode("utf-8")
    except Exception as exc:
        print("DECODE FAILED: %r" % (exc,))
        return 1

    print("README bytes served by GitHub: %d" % len(text))

    cyr = re.findall(r"[Ѐ-ӿ]+", text)
    kana = re.findall(r"[぀-ヿ]+", text)
    repl = re.findall(r"�+", text)
    paths = re.findall(r"[A-Za-z]:[\\/]|PROJECT_OC|Jearko", text)
    cjk = re.findall(r"[一-鿿]+", text)

    print("cyrillic fragments     : %s" % (cyr[:3] or "none"))
    print("kana fragments         : %s" % (kana[:3] or "none"))
    print("replacement chars      : %s" % (repl[:3] or "none"))
    print("absolute-path-like     : %s" % (sorted(set(paths))[:3] or "none"))
    print("CJK (expected none)    : %s" % (cjk[:3] or "none"))

    required = ("SELECTION DETECTED", "NOT SHOWN", "NOT ESTABLISHED",
                "0.2495", "1.0000", "60 days", "39 assertions")
    missing = [t for t in required if t not in text]

    print("")
    bad = bool(cyr or kana or repl or paths or cjk or missing)
    if missing:
        print("MISSING FROM SERVED README: %s" % missing)
    print("=" * 60)
    if bad:
        print("SERVED README FAILED THE SCAN")
        return 1
    print("SERVED README CLEAN: no corruption, all %d required tokens present"
          % len(required))
    return 0


if __name__ == "__main__":
    sys.exit(main())
