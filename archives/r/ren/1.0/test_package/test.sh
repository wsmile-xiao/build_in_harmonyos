#!/usr/bin/env bash
# test_package/test.sh — functional checks for the packaged ren executable
set -euo pipefail

ren_bin="${1:?missing ren binary}"
work_parent="${2:?missing work directory}"

if [ ! -x "$ren_bin" ]; then
    echo "[fail] missing or non-executable package binary: $ren_bin" >&2
    exit 1
fi

# AArch64 runners execute the package directly; other hosts must emulate it.
runner=()
case "$(uname -m)" in
    aarch64|arm64) ;;
    *)
        if ! qemu_aarch64="$(command -v qemu-aarch64)"; then
            echo "[fail] qemu-aarch64 is required to run the AArch64 package on $(uname -m)" >&2
            exit 1
        fi
        runner=("$qemu_aarch64")
        ;;
esac

work="$(mktemp -d "$work_parent/ren-test.XXXXXX")"
trap 'rm -rf "$work"' EXIT
out="$work/stdout"
err="$work/stderr"

passed=0
ok() {
    passed=$((passed + 1))
    echo "        [ok] $*"
}
fail() {
    echo "        [fail] $*" >&2
    exit 1
}
run_ren() {
    "${runner[@]}" "$ren_bin" "$@"
}
# new_case <name>: fresh scenario directory, made the current directory.
# stdout/stderr captures live one level up so patterns never match them.
new_case() {
    mkdir "$work/$1"
    cd "$work/$1"
}
# content_is <file> <expected>
content_is() {
    [ -f "$1" ] && [ "$(cat "$1")" = "$2" ]
}
# expect_fail <stderr text> <ren args...>: ren must exit 1 with that message
expect_fail() {
    local msg="$1"
    shift
    local rc=0
    run_ren "$@" >"$out" 2>"$err" || rc=$?
    [ "$rc" -eq 1 ] || fail "ren $* exited $rc, expected 1"
    grep -qF -- "$msg" "$err" || fail "ren $* stderr lacks: $msg"
}

echo "[step] ren functional checks"

new_case usage
expect_fail "Usage: ren" 'only-one-argument'
ok "wrong argument count prints usage and exits 1"

new_case star
printf 'A' > a.txt
printf 'B' > b.txt
printf 'L' > keep.log
printf 'H' > .hidden.txt
run_ren -v '*.txt' '#1.md' >"$out"
content_is a.md A && content_is b.md B || fail "'*.txt' matches were not renamed"
[ ! -e a.txt ] && [ ! -e b.txt ] || fail "old names still exist"
content_is keep.log L && content_is .hidden.txt H || fail "non-matching or dot file was touched"
grep -qxF 'a.txt -> a.md' "$out" && grep -qxF 'b.txt -> b.md' "$out" \
    || fail "-v did not report both renames"
ok "'*.txt' -> '#1.md' keeps contents, skips dot files, -v reports renames"

new_case manpage
printf 'D' > abc.txt.doc
run_ren 'abc*.*.*' 'xyz#1.#3'
content_is xyz.doc D && [ ! -e abc.txt.doc ] || fail "man page example did not give xyz.doc"
ok "ren(1) example 'abc*.*.*' 'xyz#1.#3' renames abc.txt.doc to xyz.doc"

new_case cycle
printf 'AB' > ab
printf 'BA' > ba
cd "$work"
run_ren 'cycle/??' '#2#1'
content_is cycle/ab BA && content_is cycle/ba AB || fail "two-file cycle was not swapped"
leftovers=(cycle/renTMP*)
[ ! -e "${leftovers[0]}" ] || fail "temporary cycle name was left behind"
ok "path prefix + '??' -> '#2#1' swaps a rename cycle via a temporary name"

new_case chain
printf '1' > a
printf '2' > aa
run_ren '*' '#1a'
content_is aa 1 && content_is aaa 2 && [ ! -e a ] || fail "chain a -> aa -> aaa lost data"
ok "'*' -> '#1a' orders the chain a -> aa -> aaa without data loss"

new_case collision
printf '1' > c.1
printf '2' > c.2
expect_fail "Two or more files would have to be renamed to 'same'" 'c.*' 'same'
content_is c.1 1 && content_is c.2 2 && [ ! -e same ] || fail "collision renamed files"
ok "colliding replacement names abort before any rename"

new_case keep
printf 'OLD' > old
printf 'NEW' > new
run_ren -k 'old' 'new'
content_is old OLD && content_is new NEW || fail "-k deleted an existing file"
ok "-k skips a rename that would delete an existing file"

new_case abort
printf 'OLD' > old
printf 'NEW' > new
expect_fail "new would have to be removed." -a 'old' 'new'
content_is old OLD && content_is new NEW || fail "-a changed files"
ok "-a aborts when a rename would delete an existing file"

new_case delete
printf 'OLD' > old
printf 'NEW' > new
run_ren -d -v 'old' 'new' >"$out" 2>"$err"
content_is new OLD && [ ! -e old ] || fail "-d did not replace the existing file"
grep -qxF 'old -> new' "$out" && grep -qF '(*)' "$err" || fail "-v did not mark the deleting rename"
ok "-d performs the deleting rename and -v marks it with (*)"

new_case ask
printf 'OLD' > old
printf 'NEW' > new
printf 'n\n' | run_ren 'old' 'new' 2>"$err"
content_is old OLD && content_is new NEW || fail "answer n still renamed"
grep -qF 'old -> new ; remove old new?' "$err" || fail "delete prompt missing"
printf 'maybe\ny\n' | run_ren 'old' 'new' 2>"$err"
content_is new OLD && [ ! -e old ] || fail "answer y did not rename"
grep -qF 'Yes or No?' "$err" || fail "invalid answer was not re-prompted"
ok "interactive mode honours n, re-prompts on other input and honours y"

new_case badpattern
printf 'F' > f1
expect_fail "must not contain a path" 'f*' 'dir/#1'
expect_fail "No wildcards allowed in replacement pattern." 'f*' 'g*'
expect_fail "bad substring numer" 'f*' 'g#2'
content_is f1 F || fail "invalid pattern renamed a file"
ok "path, wildcard and out-of-range #n replacements are rejected"

new_case nomatch
printf 'Z' > z
expect_fail "No match." 'q*' 'r'
expect_fail "would have to be renamed to empty string" 'z*' '#1'
content_is z Z || fail "failed run renamed a file"
ok "no-match and empty-name cases fail without renaming"

new_case escape
printf 'E' > e1
run_ren 'e*' 'x\#1'
content_is 'x#1' E && [ ! -e e1 ] || fail "escaped # was not literal"
ok "'\\#' inserts a literal # into the replacement name"

echo "[ok] ren: ${passed}/13 functional checks passed"
[ "$passed" -eq 13 ]
