#!/bin/sh
set -eu

METAMATH_BIN="$1"
DATABASE="$2"

output=$("$METAMATH_BIN" "READ \"$DATABASE\"" "VERIFY PROOF *" "EXIT")

printf '%s\n' "$output" | grep -F "Metamath - Version 0.198" >/dev/null
printf '%s\n' "$output" | grep -F "The source has 6 statements" >/dev/null
printf '%s\n' "$output" | grep -F "All proofs in the database were verified" >/dev/null

echo "PASS: metamath version, source parsing, and proof verification"
