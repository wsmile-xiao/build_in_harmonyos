#!/usr/bin/env python3
"""config.guess build-type detector — knowledge-base skill for OHOS.

Detects legacy autotools packages whose bundled config.guess predates
OHOS/aarch64 support.  Running their ``./configure`` on OHOS PC fails
with::

    configure: error: cannot guess build type; you must specify one

This script checks two signal classes and needs no human input:

  1. source signals  — a bundled ``config.guess`` whose script header
     (the $timestamp / "Generated from" line) is older than the
     aarch64-linux-gnu addition, or which simply lacks any
     ``aarch64``/``arm64`` branch;
  2. log signals     — a captured configure log line matching the
     canonical failure message.

Exit codes: 0 = legacy config.guess detected (mitigation applies),
1 = not detected, 2 = usage error.  ``--json`` prints one JSON verdict.

Usage:
    python3 detect_config_guess.py <source-dir> [--log <configure.log>] [--json]

Mitigation (see README): pass an explicit well-formed triplet
``--build=aarch64-unknown-linux-gnu`` (and ``--host=`` when the package
is not cross-aware); alternatively refresh config.guess/config.sub from
a modern automake (knowledge entry E007 patch route).

stdlib only, no hardcoded local paths.
"""
import glob
import json
import os
import re
import sys

LOG_SIGNATURES = [
    re.compile(r"cannot guess build type", re.I),
    re.compile(r"unable to guess system type", re.I),
    re.compile(r"config\.guess.*(failed|not found|cannot)", re.I),
]

# config.guess embeds a version line such as:
#   timestamp='2009-04-27'
TS = re.compile(r"timestamp=['\"]?(\d{4})-(\d{2})-(\d{2})")
# aarch64/arm64 recognition appeared around 2014-2016 in config.guess
LEGACY_YEAR = 2016


def scan_source(root):
    hits = []
    for path in glob.glob(os.path.join(root, "**", "config.guess"),
                          recursive=True):
        try:
            text = open(path, "r", errors="replace").read(65536)
        except OSError:
            continue
        m = TS.search(text)
        year = int(m.group(1)) if m else None
        has_arm64 = ("aarch64" in text) or ("arm64" in text)
        if (year is not None and year < LEGACY_YEAR) or not has_arm64:
            hits.append({
                "file": os.path.relpath(path, root),
                "timestamp": f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None,
                "recognizes_aarch64": has_arm64,
            })
    return hits


def scan_log(path):
    try:
        text = open(path, "r", errors="replace").read()
    except OSError:
        return []
    return [p.pattern for p in LOG_SIGNATURES if p.search(text)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    root = args[0]
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    log_idx = sys.argv.index("--log") if "--log" in sys.argv else -1
    log_hits = scan_log(sys.argv[log_idx + 1]) if log_idx >= 0 else []

    src_hits = scan_source(root)
    detected = bool(src_hits) or bool(log_hits)

    verdict = {
        "legacy_config_guess": detected,
        "source_evidence": src_hits[:5],
        "log_evidence": log_hits[:3],
        "mitigation": [
            "configure --build=aarch64-unknown-linux-gnu "
            "[--host=aarch64-unknown-linux-gnu]",
            "or refresh config.guess/config.sub from modern automake "
            "(knowledge entry E007 patch route)",
        ],
    }
    if "--json" in sys.argv:
        print(json.dumps(verdict, ensure_ascii=False))
    else:
        if detected:
            print(f"LEGACY config.guess detected in {root}")
            for h in src_hits:
                print(f"  {h['file']}: timestamp={h['timestamp']} "
                      f"aarch64={h['recognizes_aarch64']}")
            for p in log_hits:
                print(f"  log: {p}")
            for m in verdict["mitigation"]:
                print(f"  fix: {m}")
        else:
            print(f"no legacy config.guess signals in {root}")
    return 0 if detected else 1


if __name__ == "__main__":
    sys.exit(main())
