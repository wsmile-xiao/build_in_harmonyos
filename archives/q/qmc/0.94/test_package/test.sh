#!/usr/bin/env bash
set -euo pipefail

qmc_bin=${QMC_BIN:-qmc}

assert_result() {
    label=$1
    expected=$2
    expression=$3
    actual=$("$qmc_bin" -s "$expression")
    if [ "$actual" != "result: $expected" ]; then
        printf '%s: expected <%s>, got <%s>\n' "$label" "$expected" "$actual" >&2
        exit 1
    fi
    printf 'PASS %s\n' "$label"
}

version=$("$qmc_bin" --version)
case "$version" in
    *'Version:         0.94'*) printf 'PASS version\n' ;;
    *) printf 'version missing: %s\n' "$version" >&2; exit 1 ;;
esac

help_text=$("$qmc_bin" --help)
case "$help_text" in
    *'Simplification tool'*'--source EQU'*) printf 'PASS help\n' ;;
    *) printf 'help missing: %s\n' "$help_text" >&2; exit 1 ;;
esac

assert_result tautology 'a' 'a*/b+a*b'
assert_result identity 'a' 'a+0'
assert_result contradiction '0' 'a*/a'

truth_table=$("$qmc_bin" -g -s 'a+b')
case "$truth_table" in
    *'| 0 | 0 | 0 |'*'| 1 | 1 | 1 |'*'result: a+b'*)
        printf 'PASS truth table\n' ;;
    *) printf 'truth table incorrect: %s\n' "$truth_table" >&2; exit 1 ;;
esac

html_table=$("$qmc_bin" -G -s 'a+b')
case "$html_table" in
    *'<TABLE'*'<H3>Q=a+b</H3>'*) printf 'PASS HTML table\n' ;;
    *) printf 'HTML table incorrect: %s\n' "$html_table" >&2; exit 1 ;;
esac

invalid=$("$qmc_bin" -s 'a+[' 2>&1)
case "$invalid" in
    *'bad input'*) printf 'PASS invalid input\n' ;;
    *) printf 'invalid-input diagnostic missing: %s\n' "$invalid" >&2; exit 1 ;;
esac
