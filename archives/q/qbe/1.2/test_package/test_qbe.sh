#!/usr/bin/env bash
# Consumer-side end-to-end test for the packaged qbe binary:
#   SSA -> assembly (qbe) -> executable (C compiler) -> native run -> compare.
set -eu
# `pipefail` is not POSIX; enable it when the running shell supports it so the
# script also works when driven through /bin/sh on CI workers.
(set -o pipefail) 2>/dev/null && set -o pipefail || true

QBE_BIN="${QBE_BIN:-qbe}"
CC_BIN="${QBE_TEST_CC:-${CC:-cc}}"
work_root="${TMPDIR:-$PWD}"
work_dir="$work_root/qbe-consumer-$$"
mkdir -p "$work_dir"
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

fail() {
	echo "qbe consumer test FAILED: $*" >&2
	exit 1
}

# 1) packaged binary is present and executable
[ -x "$QBE_BIN" ] || fail "missing packaged binary: $QBE_BIN"

# 2) the C compiler used to assemble/link the generated code is available
command -v "$CC_BIN" >/dev/null 2>&1 || CC_BIN=clang
command -v "$CC_BIN" >/dev/null 2>&1 || fail "no C compiler found (tried: $QBE_TEST_CC, cc, clang)"

# 3) -h prints the upstream usage
"$QBE_BIN" -h </dev/null | grep -q "\[OPTIONS\]" || fail "qbe -h usage output missing"

# 4) the default target matches the host architecture
case "$(uname -m)" in
aarch64 | arm64) expected_target=arm64 ;;
riscv64) expected_target=rv64 ;;
x86_64 | amd64) expected_target=amd64_sysv ;;
*) fail "unsupported host architecture: $(uname -m)" ;;
esac
target=$("$QBE_BIN" -t? </dev/null)
[ "$target" = "$expected_target" ] || fail "default target '$target' != expected '$expected_target'"

# 5) hello world: SSA -> assembly -> executable -> stdout comparison
cat >"$work_dir/hello.ssa" <<'SSA'
export function w $main() {
@start
	%r =w call $puts(l $s)
	ret 0
}
data $s = { b "hello from qbe", b 0 }
SSA
"$QBE_BIN" -o "$work_dir/hello.s" "$work_dir/hello.ssa"
[ -s "$work_dir/hello.s" ] || fail "qbe produced no assembly for hello.ssa"
hello_out=$(
	"$CC_BIN" -g -o "$work_dir/hello" "$work_dir/hello.s" &&
		"$work_dir/hello"
)
[ "$hello_out" = "hello from qbe" ] || fail "unexpected hello output: '$hello_out'"

# 6) computed return value: SSA -> assembly -> executable -> exit status
cat >"$work_dir/answer.ssa" <<'SSA'
export function w $main() {
@start
	%x =w add 40, 2
	ret %x
}
SSA
"$QBE_BIN" -o "$work_dir/answer.s" "$work_dir/answer.ssa"
"$CC_BIN" -g -o "$work_dir/answer" "$work_dir/answer.s"
set +e
"$work_dir/answer"
answer_rc=$?
set -e
[ "$answer_rc" -eq 42 ] || fail "computed exit status $answer_rc != 42"

# 7) invalid input is rejected with a nonzero exit code
printf 'this is not ssa\n' >"$work_dir/bad.ssa"
if "$QBE_BIN" -o "$work_dir/bad.s" "$work_dir/bad.ssa" >/dev/null 2>&1; then
	fail "invalid SSA input was accepted"
fi

echo "qbe consumer E2E passed: target=$target hello='$hello_out' exit=$answer_rc"
