#!/usr/bin/env python3
"""Record-level comparison of a lucy debug report against the upstream golden file.

Why not a plain ``diff``?
-------------------------
``abi.c`` resolves ambiguous bases (N, B, R, Y, ...) of the 2nd (ABI) sequence
with libc ``random()``.  glibc and musl implement ``random()`` with different
generators, so the "salvage" decisions taken during the secondary sequence
extension step differ between the maintainer's Linux box and OHOS/musl.
``README.FIRST`` FAQ #6 documents this effect and states explicitly that
sequences carrying no ambiguous base still produce identical output on every
platform ("the only differences ... you will see a lot of N's scattered around
their sequences.  This is the reason of the difference").

This checker therefore enforces the documented invariant instead of accepting a
blanket diff:

  * both reports must hold the same record names in the same order;
  * every record whose 2nd-sequence entry carries **no** ambiguous base must
    match the golden file byte for byte;
  * records **with** an ambiguous base may differ only in the fields that the
    ABI extension step feeds into -- CLZ / CLB / CLR / CLV.  CLN must match
    everywhere.

Usage:
    golden-compare.py <golden.debug> <produced.info> <second-sequence-file>

Exit status: 0 = pass, 1 = mismatch, 2 = usage/input error.
"""
from __future__ import annotations

import re
import sys

# Tab-separated field layout of one lucy debug line:
#  0 name | 1 CLR | 2 3 clr | 4 CLB | 5 6 clb | 7 CLN | 8 9 cln
#         | 10 CLZ | 11 12 clz | 13 CLV | 14 15 clv
FIELDS = {
    "CLR": (2, 3),
    "CLB": (5, 6),
    "CLN": (8, 9),
    "CLZ": (11, 12),
    "CLV": (14, 15),
}
# Fields the ABI (2nd sequence) extension step can legitimately move.
ABI_SENSITIVE = ("CLZ", "CLB", "CLR", "CLV")
# Ambiguous IUPAC nucleotide codes that trigger the random() based resolution.
AMBIGUOUS = re.compile(r"[NBRYKMSWDHV]")


def load_report(path: str):
    """Return (ordered_names, {name: fields})."""
    names, rows = [], {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 16:
                continue          # header / comment / trailing blank
            names.append(parts[0])
            rows[parts[0]] = parts
    return names, rows


def ambiguous_records(path: str) -> set[str]:
    """Names of 2nd-sequence records containing at least one ambiguous base."""
    found: set[str] = set()
    name = None
    chunks: list[str] = []
    with open(path, encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if line.startswith(">"):
                if name and AMBIGUOUS.search("".join(chunks)):
                    found.add(name)
                name = line[1:].split()[0] if len(line) > 1 else ""
                chunks = []
            else:
                chunks.append(line)
    if name and AMBIGUOUS.search("".join(chunks)):
        found.add(name)
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2

    golden_path, produced_path, second_path = argv[1:4]
    try:
        golden_names, golden = load_report(golden_path)
        produced_names, produced = load_report(produced_path)
        ambiguous = ambiguous_records(second_path)
    except OSError as exc:
        print(f"[error] cannot read input: {exc}")
        return 2

    failures: list[str] = []

    # ── record set / ordering ────────────────────────────────────────────────
    if golden_names != produced_names:
        only_golden = [n for n in golden_names if n not in produced]
        only_produced = [n for n in produced_names if n not in golden]
        failures.append(
            "record list differs: golden=%d produced=%d missing=%s extra=%s"
            % (len(golden_names), len(produced_names),
               only_golden[:5], only_produced[:5])
        )

    identical = 0
    abi_noise: list[tuple[str, list[str]]] = []

    for name in golden_names:
        if name not in produced:
            continue
        ref, new = golden[name], produced[name]
        if ref == new:
            identical += 1
            continue

        if name not in ambiguous:
            failures.append(
                f"{name}: 2nd-sequence has no ambiguous base but the record "
                f"differs from the golden file"
            )
            continue

        moved = [
            key for key, (left, right) in FIELDS.items()
            if ref[left] != new[left] or ref[right] != new[right]
        ]
        illegal = [key for key in moved if key not in ABI_SENSITIVE]
        if illegal:
            failures.append(
                f"{name}: ABI-sensitive record differs outside the allowed "
                f"fields ({', '.join(illegal)})"
            )
            continue

        abi_noise.append((name, moved))

    # ── report ──────────────────────────────────────────────────────────────
    total = len(golden_names)
    print(f"  golden records          : {total}")
    print(f"  identical to golden     : {identical}")
    print(f"  ABI random() noise      : {len(abi_noise)}"
          "  (documented platform effect, README.FIRST FAQ #6)")
    print(f"  ambiguous-base records  : {len(ambiguous)} / {total}")
    for name, moved in abi_noise:
        print(f"      {name:<12} fields moved: {', '.join(moved)}")
    print(f"  hard failures           : {len(failures)}")
    for item in failures:
        print(f"      [FAIL] {item}")

    if failures:
        print("RESULT=FAIL")
        return 1
    print("RESULT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
