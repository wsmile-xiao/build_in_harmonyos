"""Validate the installed preseq CLI's real histogram output."""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_output.py TABLE")
    output = Path(sys.argv[1])
    if not output.is_file():
        raise SystemExit("preseq consumer produced no output")
    lines = output.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise SystemExit("preseq consumer table has no data rows")
    if not lines[0].startswith("TOTAL_READS\tEXPECTED_DISTINCT"):
        raise SystemExit("preseq consumer output is not a complexity table")
    if len(lines[1].split("\t")) < 2:
        raise SystemExit("preseq consumer data row has too few columns")
    print("PRESEQ_OUTPUT_ASSERTIONS_PASS")


if __name__ == "__main__":
    main()
