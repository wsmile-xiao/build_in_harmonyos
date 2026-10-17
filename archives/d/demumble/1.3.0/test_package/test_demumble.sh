#!/bin/sh
set -eu

DEMUMBLE=${1:-demumble}

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_output() {
    description=$1
    expected=$2
    shift 2
    actual=$("$@") || fail "$description (command failed)"
    [ "$actual" = "$expected" ] || {
        echo "expected: $expected" >&2
        echo "actual:   $actual" >&2
        fail "$description"
    }
}

assert_output "plain text remains unchanged" "hello" "$DEMUMBLE" hello
assert_output "Itanium C++ symbol" "func(char*, int)" "$DEMUMBLE" _Z4funcPci
assert_output "Rust v0 symbol" "std::mem::align_of::<f64>" "$DEMUMBLE" _RINvNtC3std3mem8align_ofdE
assert_output "D symbol" "foo.bar" "$DEMUMBLE" _TtP3foo3bar_
assert_output "Swift symbol" "Swift.String.count.getter : Swift.Int" "$DEMUMBLE" '$sSS5countSivg'
assert_output "MSVC symbol" "int __cdecl Fxi(int (__cdecl *)(int))" "$DEMUMBLE" '?Fxi@@YAHP6AHH@Z@Z'
assert_output "macOS leading underscore" "operator new(int)" "$DEMUMBLE" __Znwi
assert_output "brief output" '"f()" (_Z1fv)' "$DEMUMBLE" -b _Z1fv
assert_output "option terminator" "-h" "$DEMUMBLE" -- -h

stdin_output=$(printf '%s\n' 'I like _Znw' | "$DEMUMBLE") || fail "stdin filter (command failed)"
[ "$stdin_output" = "I like operator new" ] || fail "stdin filter"

help_output=$("$DEMUMBLE" --help 2>&1) || fail "help (command failed)"
printf '%s\n' "$help_output" | grep -q 'usage: demumble' || fail "help text"

echo "demumble consumer tests passed (11 assertions)"
