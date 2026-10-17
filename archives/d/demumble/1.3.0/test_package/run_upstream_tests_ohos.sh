#!/bin/sh
# POSIX-shell execution of all 42 cases in upstream demumble_test.py.
# HarmonyOS PC images do not include Python, so only the driver is translated;
# commands and expected outputs remain identical to the official v1.3.0 suite.
set -eu

DEMUMBLE=${1:-./demumble}
passed=0

fail() {
    echo "FAIL [$1]" >&2
    echo "expected: $2" >&2
    echo "actual:   $3" >&2
    exit 1
}

eq_args() {
    name=$1
    expected=$2
    shift 2
    actual=$("$DEMUMBLE" "$@") || fail "$name" "$expected" "command failed"
    [ "$actual" = "$expected" ] || fail "$name" "$expected" "$actual"
    passed=$((passed + 1))
}

eq_stdin() {
    name=$1
    input=$2
    expected=$3
    shift 3
    actual=$(printf '%s\n' "$input" | "$DEMUMBLE" "$@" 2>&1) || fail "$name" "$expected" "command failed"
    [ "$actual" = "$expected" ] || fail "$name" "$expected" "$actual"
    passed=$((passed + 1))
}

match_args() {
    name=$1
    pattern=$2
    shift 2
    actual=$("$DEMUMBLE" "$@" 2>&1) || fail "$name" "$pattern" "command failed"
    printf '%s\n' "$actual" | grep -Eq "$pattern" || fail "$name" "$pattern" "$actual"
    passed=$((passed + 1))
}

match_stdin_error() {
    name=$1
    input=$2
    pattern=$3
    shift 3
    actual=$(printf '%s\n' "$input" | "$DEMUMBLE" "$@" 2>&1) || true
    printf '%s\n' "$actual" | grep -Eq "$pattern" || fail "$name" "$pattern" "$actual"
    passed=$((passed + 1))
}

eq_args 01 'hello' hello
eq_args 02 'func(char*, int)
f()' _Z4funcPci _Z1fv
eq_stdin 03 '_Z4funcPci
_Z1fv' 'func(char*, int)
f()'
eq_args 04 'std::mem::align_of::<f64>
mylib::foo::bar' _RINvNtC3std3mem8align_ofdE _RNvNvC5mylib3foo3bar
eq_stdin 05 '_RINvNtC3std3mem8align_ofdE
_RNvNvC5mylib3foo3bar' 'std::mem::align_of::<f64>
mylib::foo::bar'
eq_args 06 'foo.bar' _TtP3foo3bar_
eq_stdin 07 '_TtP3foo3bar_' 'foo.bar'
eq_args 08 'Swift.String.count.getter : Swift.Int' '$sSS5countSivg'
eq_stdin 09 '$sSS5countSivg' 'Swift.String.count.getter : Swift.Int'
eq_args 10 'int __cdecl Fxi(int (__cdecl *)(int))' '?Fxi@@YAHP6AHH@Z@Z'
eq_args 11 'public: __cdecl S::S(struct S &&)' '??0S@@QEAA@$$QEAU0@@Z'
eq_args 12 '"hi"' '??_C@_02PCEFGMJL@hi?$AA@'
eq_args 13 'operator new(int)' __Znwi
eq_stdin 14 '__Znwi' 'operator new(int)'
eq_args 15 'hi
f()
ho
g()' -m hi _Z1fv ho _Z1gv
eq_stdin 16 'hi_ho _Z1fv ho _Z1gv ?hm' 'f()
g()
?hm' -m
eq_stdin 17 '_Z1fv!_Z1gv' 'f()
g()' -m
eq_stdin 18 '_Z1fv!foo_bar' 'f()' -m
eq_args 19 'int*' Pi
eq_stdin 20 'Pi' 'Pi'
eq_stdin 21 '___Z10blocksNRVOv_block_invoke' 'invocation function for block in blocksNRVO()'
eq_stdin 22 '.____Z10blocksNRVOv_block_invoke' '.invocation function for block in blocksNRVO()'
eq_stdin 23 '.____Z10blocksNRVOv_block_invoke' 'invocation function for block in blocksNRVO()' -m
eq_args 24 'zx::channel::~channel()' _ZN2zx7channelD4Ev
eq_args 25 '-b' -- -b
eq_args 26 '-m' -- -m
eq_args 27 '-h' -- -h
match_args 28 '.*usage: demumble.*' -h
match_args 29 '.*usage: demumble.*' --help
match_args 30 '.*\..*' --version
eq_args 31 'hello' -b hello
eq_args 32 '"f()" (_Z1fv)' -b _Z1fv
eq_stdin 33 '_Z1fv' '"f()" (_Z1fv)' -b
eq_stdin 34 '_Z1fv!foo_bar' '"f()" (_Z1fv)' -bm
eq_stdin 35 '_Z1fv!foo_bar' '"f()" (_Z1fv)' -mb
match_stdin_error 36 'bar' ".*unrecognized option .*--foo.*" --foo
match_stdin_error 37 'bar' ".*unrecognized option .*x.*-bx.*" -bx
eq_stdin 38 '_ZZ3fooiENK3$_0clEi' 'foo(int)::$_0::operator()(int) const'
eq_args 39 "class Net \`RTTI Type Descriptor Name'" '.?AVNet@@'
eq_stdin 40 'asdf?x@@3HAjkl' 'asdfint xjkl'
eq_stdin 41 'asdf?x@@3Hjkl' 'asdf?x@@3Hjkl'
eq_args 42 'int x
  unused suffix: jkl' '?x@@3HAjkl'

[ "$passed" -eq 42 ] || fail count 42 "$passed"
echo "upstream demumble tests passed ($passed/42)"
