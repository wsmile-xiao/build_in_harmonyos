#!/usr/bin/env bash
set -euo pipefail

WCALC_BIN=${WCALC_BIN:-wcalc}

assert_eq() {
    label=$1
    expected=$2
    shift 2
    actual=$("$WCALC_BIN" "$@" | tr -d '[:space:]')
    if [ "$actual" != "$expected" ]; then
        printf '%s: expected <%s>, got <%s>\n' "$label" "$expected" "$actual" >&2
        exit 1
    fi
    printf 'PASS %s\n' "$label"
}

assert_eq version 'wcalc2.5' --version
assert_eq arithmetic '3' -q '1+2'
assert_eq precision '0.3333333333' -q -P10 '1/3'
assert_eq hexadecimal '0xff' -q -h '255'

variable_result=$("$WCALC_BIN" -q 'x=7' 'x*3' | tail -n 1 | tr -d '[:space:]')
if [ "$variable_result" != '21' ]; then
    printf 'variables: expected <21>, got <%s>\n' "$variable_result" >&2
    exit 1
fi
printf 'PASS variables\n'

interactive_result=$(printf '1+2\n' | "$WCALC_BIN" -q | tr -d '[:space:]')
if [ "$interactive_result" != '3' ]; then
    printf 'interactive input: expected <3>, got <%s>\n' "$interactive_result" >&2
    exit 1
fi
printf 'PASS interactive input\n'

# Upstream 2.5 prints a parse error but returns zero, so assert the diagnostic.
syntax_result=$("$WCALC_BIN" -q 'foo(' 2>&1)
case "$syntax_result" in
    *'syntax error'*) printf 'PASS syntax diagnostic\n' ;;
    *) printf 'syntax diagnostic missing: %s\n' "$syntax_result" >&2; exit 1 ;;
esac
