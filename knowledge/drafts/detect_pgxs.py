#!/usr/bin/env python3
"""PGXS extension detector — knowledge-base skill for OHOS adaptation.

Scans an upstream source tree and decides whether it is a PostgreSQL
extension built with PGXS (PostgreSQL Extension Building Infrastructure).

A package matches when its build files reference PGXS, i.e. one of:
  * ``PGXS := $(shell $(PG_CONFIG) --pgxs)``   (canonical, GNU make)
  * ``include $(PGXS)``                        (canonical include line)
  * ``USE_PGXS`` in a configure/make build     (autotools wrappers)

C sources are confirmed by server-header includes
(``postgres.h`` / ``fmgr.h`` / ``PG_MODULE_MAGIC``), which distinguishes a
true server-side extension from a mere libpq client program.

Exit codes:  0 = PGXS extension detected, 1 = not detected, 2 = usage error.
With ``--json`` the verdict and evidence are printed as one JSON line so
CI wrappers can consume it without parsing free text.

Usage:
    python3 detect_pgxs.py <source-dir> [--json]

The script is self-contained (stdlib only), platform independent and
carries no hardcoded local paths.
"""
import json
import os
import re
import sys

PGXS_PATTERNS = [
    re.compile(r"PGXS\s*:=\s*\$\(shell\s+\$\(PG_CONFIG\)\s+--pgxs\)"),
    re.compile(r"^\s*include\s+\$\(PGXS\)", re.M),
    re.compile(r"\bUSE_PGXS\b"),
]

SERVER_HEADER_PATTERNS = [
    re.compile(r'#\s*include\s+["<](postgres\.h|c\.h|fmgr\.h|miscadmin\.h)[">]'),
    re.compile(r"\bPG_MODULE_MAGIC\b"),
]

MAKEFILE_GLOBS = ("Makefile", "GNUmakefile", "makefile", "*.mk", "Makefile.*")


def find_build_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".github", "build", "m4")]
        for fn in filenames:
            if (fn in MAKEFILE_GLOBS or fn.startswith("Makefile.")
                    or fn.endswith(".mk") or fn == "configure.ac"):
                out.append(os.path.join(dirpath, fn))
    return out


def find_c_sources(root, limit=200):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".github", "build")]
        for fn in filenames:
            if fn.endswith((".c", ".cpp", ".cc", ".h")):
                out.append(os.path.join(dirpath, fn))
                if len(out) >= limit:
                    return out
    return out


def detect(root):
    build_hits, src_hits = [], []
    for path in find_build_files(root):
        try:
            with open(path, "r", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for pat in PGXS_PATTERNS:
            m = pat.search(text)
            if m:
                build_hits.append((os.path.relpath(path, root),
                                   m.group(0)[:60]))
                break
    for path in find_c_sources(root):
        try:
            with open(path, "r", errors="replace") as fh:
                head = fh.read(65536)
        except OSError:
            continue
        for pat in SERVER_HEADER_PATTERNS:
            if pat.search(head):
                src_hits.append(os.path.relpath(path, root))
                break
    pgxs = bool(build_hits)
    server_src = bool(src_hits)
    verdict = pgxs and (server_src or not root_has_c(root))
    return {
        "pgxs_extension": verdict,
        "build_system": "pgxs" if pgxs else None,
        "pgxs_hits": build_hits[:5],
        "server_header_hits": src_hits[:5],
        "recommended_tool_requires": "postgresql/<server-version>",
        "recommended_make_vars": ['PG_CONFIG="<pg_config abs path>"',
                                  "enable_rpath="],
    }


def root_has_c(root):
    return bool(find_c_sources(root, limit=1))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    result = detect(root)
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result["pgxs_extension"]:
            print(f"PGXS extension detected: {root}")
            for rel, ev in result["pgxs_hits"]:
                print(f"  build evidence : {rel}: {ev}")
            for rel in result["server_header_hits"]:
                print(f"  source evidence: {rel}")
            print("  recipe template: knowledge/drafts/"
                  "PGXS-EXTENSION-OHOS-ADAPTATION/README.md")
        else:
            print("not a PGXS extension: {0}".format(root))
    return 0 if result["pgxs_extension"] else 1


if __name__ == "__main__":
    sys.exit(main())
