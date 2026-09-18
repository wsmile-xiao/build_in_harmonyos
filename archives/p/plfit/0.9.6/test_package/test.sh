#!/usr/bin/env bash
# test_package/test.sh — CLI smoke test for the packaged plfit/plgen binaries.
# Runs in the conanrun environment (the installed bin/ directory is on PATH).
set -eu

work="$(pwd)/_plfit_cli"
rm -rf "$work"
mkdir -p "$work"

echo "[test] plfit -v / plgen -v"
plfit -v
plgen -v

echo "[test] discrete: plgen generates 2000 zeta samples (alpha=2.5, seed 42)"
plgen -s 42 2000 2.5 > "$work/discrete.txt"
[ "$(wc -l < "$work/discrete.txt")" -eq 2000 ] || {
    echo "FAIL: expected 2000 discrete samples"; exit 1; }

echo "[test] discrete: plfit fits the generated sample"
out="$(plfit -b "$work/discrete.txt")"
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q ' D ' || { echo "FAIL: no discrete (D) fit line"; exit 1; }
alpha="$(printf '%s\n' "$out" | head -1 | awk '{print $3}')"
awk -v a="$alpha" 'BEGIN { exit !(a > 2.0 && a < 3.0) }' || {
    echo "FAIL: discrete alpha $alpha outside (2.0, 3.0)"; exit 1; }

echo "[test] continuous: plgen generates 2000 Pareto samples (alpha=2.0, seed 7)"
plgen -c -s 7 2000 2.0 > "$work/continuous.txt"
[ "$(wc -l < "$work/continuous.txt")" -eq 2000 ] || {
    echo "FAIL: expected 2000 continuous samples"; exit 1; }

echo "[test] continuous: plfit fits the generated sample"
out="$(plfit -b "$work/continuous.txt")"
printf '%s\n' "$out"
printf '%s\n' "$out" | grep -q ' C ' || { echo "FAIL: no continuous (C) fit line"; exit 1; }
alpha="$(printf '%s\n' "$out" | head -1 | awk '{print $3}')"
awk -v a="$alpha" 'BEGIN { exit !(a > 1.5 && a < 2.5) }' || {
    echo "FAIL: continuous alpha $alpha outside (1.5, 2.5)"; exit 1; }

rm -rf "$work"
echo "plfit CLI smoke test: OK"
