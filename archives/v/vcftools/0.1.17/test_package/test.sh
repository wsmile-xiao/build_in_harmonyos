#!/usr/bin/env bash
# Consumer test for the packaged C++ binary and Perl command-line tools.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

version_output="$(vcftools --version 2>&1)"
case "$version_output" in
  *"VCFtools (0.1.17)"*) ;;
  *)
    echo "unexpected vcftools version output: $version_output" >&2
    exit 1
    ;;
esac

rm -f "$SCRIPT_DIR/result.frq" "$SCRIPT_DIR/result.log"
vcftools --vcf "$SCRIPT_DIR/test.vcf" --freq --out "$SCRIPT_DIR/result"

grep -F "A:0.25" "$SCRIPT_DIR/result.frq" >/dev/null
grep -F "G:0.75" "$SCRIPT_DIR/result.frq" >/dev/null

vcf-validator "$SCRIPT_DIR/test.vcf"
