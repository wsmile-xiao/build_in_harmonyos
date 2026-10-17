#!/bin/sh
# Exercise the packaged gti launcher with deterministic fake git processes.

set -eu
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

GTI_BIN="${1:-}"
TEST_SHELL="${2:-/bin/sh}"
CASE_ID="${3:-all}"
assertions=0
passed_cases=0

fail()
{
    echo "[fail] $1"
    exit 1
}

assert_equal()
{
    expected="$1"
    actual="$2"
    description="$3"
    assertions=$((assertions + 1))
    if [ "$actual" != "$expected" ]; then
        fail "$description: expected '$expected', got '$actual'"
    fi
}

assert_file()
{
    file_path="$1"
    assertions=$((assertions + 1))
    if [ ! -f "$file_path" ]; then
        fail "missing packaged file: $file_path"
    fi
}

assert_executable()
{
    file_path="$1"
    assertions=$((assertions + 1))
    if [ ! -x "$file_path" ]; then
        fail "$file_path not found or not executable"
    fi
}

read_log()
{
    key="$1"
    sed -n "s/^${key}=//p" "$log_file"
}

if [ -z "$GTI_BIN" ]; then
    fail "gti binary path is required"
fi
if [ ! -x "$TEST_SHELL" ]; then
    fail "test shell not found or not executable: $TEST_SHELL"
fi
case "$CASE_ID" in
    all|A1|A2|A3|A4|A5) ;;
    *) fail "unknown test case selector: $CASE_ID" ;;
esac

should_run()
{
    [ "$CASE_ID" = "all" ] || [ "$CASE_ID" = "$1" ]
}

tmpdir="${TMPDIR:-/tmp}/gti-test-$$"
mkdir -p "$tmpdir"
trap 'rm -rf "$tmpdir"' 0 HUP INT TERM

log_file="$tmpdir/fake-git.log"
fake_git="$tmpdir/fake-git"
printf '#!%s\n' "$TEST_SHELL" >"$fake_git"
cat >>"$fake_git" <<'EOF'
: "${GTI_TEST_LOG:?GTI_TEST_LOG is required}"
{
    printf 'argc=%s\n' "$#"
    index=1
    for arg in "$@"; do
        printf 'arg%s=%s\n' "$index" "$arg"
        index=$((index + 1))
    done
} >"$GTI_TEST_LOG"
exit "${GTI_TEST_EXIT:-0}"
EOF
chmod +x "$fake_git"

if should_run A1; then
    assert_executable "$GTI_BIN"
    assert_file "./share/man/man6/gti.6"
    assert_file "./share/bash-completion/completions/gti.bash"
    assert_file "./share/zsh/site-functions/_gti"
    assert_file "./licenses/LICENSE"
    : >"$log_file"
    set +e
    GIT="$fake_git" GTI_TEST_LOG="$log_file" GTI_SPEED=1000000000 \
        "$GTI_BIN" --version >/dev/null 2>&1
    case_rc=$?
    set -e
    assert_equal "0" "$case_rc" "A1 exit status"
    assert_equal "1" "$(read_log argc)" "A1 argument count"
    assert_equal "--version" "$(read_log arg1)" "A1 forwarded argument"
    passed_cases=$((passed_cases + 1))
    echo "[ok] A1: GIT override received --version"
fi

if should_run A2; then
    : >"$log_file"
    set +e
    GIT="$fake_git" GTI_TEST_LOG="$log_file" GTI_SPEED=1000000000 \
        "$GTI_BIN" push origin "feature branch" >/dev/null 2>&1
    case_rc=$?
    set -e
    assert_equal "0" "$case_rc" "A2 exit status"
    assert_equal "3" "$(read_log argc)" "A2 argument count"
    assert_equal "push" "$(read_log arg1)" "A2 first argument"
    assert_equal "origin" "$(read_log arg2)" "A2 second argument"
    assert_equal "feature branch" "$(read_log arg3)" "A2 spaced argument"
    passed_cases=$((passed_cases + 1))
    echo "[ok] A2: multiple push arguments were preserved"
fi

if should_run A3; then
    fake_bin="$tmpdir/bin"
    mkdir -p "$fake_bin"
    cp "$fake_git" "$fake_bin/git"
    chmod +x "$fake_bin/git"
    : >"$log_file"
    set +e
    (
        unset GIT
        PATH="$fake_bin:$PATH" GTI_TEST_LOG="$log_file" GTI_SPEED=1000000000 \
            "$GTI_BIN" status --short >/dev/null 2>&1
    )
    case_rc=$?
    set -e
    assert_equal "0" "$case_rc" "A3 exit status"
    assert_equal "2" "$(read_log argc)" "A3 argument count"
    assert_equal "status" "$(read_log arg1)" "A3 first argument"
    assert_equal "--short" "$(read_log arg2)" "A3 second argument"
    passed_cases=$((passed_cases + 1))
    echo "[ok] A3: PATH lookup launched git"
fi

if should_run A4; then
    : >"$log_file"
    set +e
    GIT="$fake_git" GTI_TEST_LOG="$log_file" GTI_TEST_EXIT=23 GTI_SPEED=1000000000 \
        "$GTI_BIN" fetch >/dev/null 2>&1
    case_rc=$?
    set -e
    assert_equal "23" "$case_rc" "A4 propagated exit status"
    assert_equal "1" "$(read_log argc)" "A4 argument count"
    assert_equal "fetch" "$(read_log arg1)" "A4 forwarded argument"
    passed_cases=$((passed_cases + 1))
    echo "[ok] A4: child exit status 23 was propagated"
fi

if should_run A5; then
    empty_bin="$tmpdir/empty-bin"
    mkdir -p "$empty_bin"
    set +e
    (
        unset GIT
        PATH="$empty_bin" GTI_SPEED=1000000000 \
            "$GTI_BIN" status >/dev/null 2>&1
    )
    case_rc=$?
    set -e
    assert_equal "1" "$case_rc" "A5 missing git exit status"
    passed_cases=$((passed_cases + 1))
    echo "[ok] A5: missing git executable returned failure"
fi

if [ "$CASE_ID" = "all" ]; then
    expected_cases=5
    expected_assertions=21
else
    expected_cases=1
    case "$CASE_ID" in
        A1) expected_assertions=8 ;;
        A2) expected_assertions=5 ;;
        A3) expected_assertions=4 ;;
        A4) expected_assertions=3 ;;
        A5) expected_assertions=1 ;;
    esac
fi

if [ "$passed_cases" -ne "$expected_cases" ]; then
    fail "expected $expected_cases added consumer scenario(s), got $passed_cases"
fi
if [ "$assertions" -ne "$expected_assertions" ]; then
    fail "expected $expected_assertions assertions, got $assertions"
fi

echo "[ok] $passed_cases/$expected_cases added consumer scenario(s) passed ($assertions assertions)"
