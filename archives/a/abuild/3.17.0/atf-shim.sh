#!/bin/sh
# Minimal ATF (Automated Testing Framework) shim for abuild upstream tests.
# Provides the atf_check, atf_fail, atf_require_prog, atf_get_srcdir
# functions needed by abuild's ATF-based test suite, without requiring
# the full kyua/atf packages.

# Test state
_atf_pass=0
_atf_fail=0
_atf_skip=0
_atf_total=0
_atf_current_test=""
_atf_srcdir=""

# atf_get_srcdir — returns the directory containing the test script
atf_get_srcdir() {
    if [ -n "$_atf_srcdir" ]; then
        echo "$_atf_srcdir"
    else
        # Default: current directory
        echo "."
    fi
}

# atf_fail — fail the current test with a message
atf_fail() {
    echo "FAIL: $_atf_current_test: $*"
    _atf_fail=$((_atf_fail + 1))
    return 1
}

# atf_require_prog — skip test if program is not found
atf_require_prog() {
    for prog in "$@"; do
        if ! command -v "$prog" >/dev/null 2>&1; then
            echo "SKIP: $_atf_current_test: $prog not found"
            _atf_skip_flag=true
            return 1
        fi
    done
    return 0
}

# atf_check — run a command and verify exit code and output
# Usage: atf_check -s exit:0 -o match:"pattern" -e match:"pattern" command args...
# Supports: -s exit:<code> | -s not-exit:<code> | -s eq:<code> | -s ne:<code>
#           -o match:<pattern> | -o not-match:<pattern>
#           -o inline:<text>   | -o empty
#           -e match:<pattern> | -e not-match:<pattern>
#           -e inline:<text>   | -e empty
atf_check() {
    _atf_expected_exit=""
    _atf_expected_exit_neg=false
    _atf_stdout_patterns=""
    _atf_stderr_patterns=""
    _atf_stdout_inline=""
    _atf_stderr_inline=""
    _atf_stdout_empty=false
    _atf_stderr_empty=false
    _atf_stdout_not_match=""
    _atf_stderr_not_match=""

    # Parse options
    while [ $# -gt 0 ]; do
        case "$1" in
            -s)
                shift
                case "$1" in
                    exit:*) _atf_expected_exit="${1#exit:}"; _atf_expected_exit_neg=false ;;
                    not-exit:*) _atf_expected_exit="${1#not-exit:}"; _atf_expected_exit_neg=true ;;
                    eq:*) _atf_expected_exit="${1#eq:}"; _atf_expected_exit_neg=false ;;
                    ne:*) _atf_expected_exit="${1#ne:}"; _atf_expected_exit_neg=true ;;
                esac
                shift ;;
            -o)
                shift
                case "$1" in
                    match:*) _atf_stdout_patterns="$_atf_stdout_patterns ${1#match:}" ;;
                    not-match:*) _atf_stdout_not_match="$_atf_stdout_not_match ${1#not-match:}" ;;
                    inline:*) _atf_stdout_inline="${1#inline:}" ;;
                    empty) _atf_stdout_empty=true ;;
                esac
                shift ;;
            -e)
                shift
                case "$1" in
                    match:*) _atf_stderr_patterns="$_atf_stderr_patterns ${1#match:}" ;;
                    not-match:*) _atf_stderr_not_match="$_atf_stderr_not_match ${1#not-match:}" ;;
                    inline:*) _atf_stderr_inline="${1#inline:}" ;;
                    empty) _atf_stderr_empty=true ;;
                esac
                shift ;;
            *)
                break ;;
        esac
    done

    # Run the command. Use TMPDIR (or the shim's own directory as fallback)
    # instead of /tmp: OHOS /tmp is read-only and mktemp there fails.
    _atf_tmpdir="${TMPDIR:-$(dirname "$0")}"
    _atf_stdout_file=$(mktemp "$_atf_tmpdir/atf_stdout.XXXXXX")
    _atf_stderr_file=$(mktemp "$_atf_tmpdir/atf_stderr.XXXXXX")
    "$@" >"$_atf_stdout_file" 2>"$_atf_stderr_file"
    _atf_actual_exit=$?
    _atf_stdout=$(cat "$_atf_stdout_file")
    _atf_stderr=$(cat "$_atf_stderr_file")
    rm -f "$_atf_stdout_file" "$_atf_stderr_file"

    _atf_failed=false

    # Check exit code
    if [ -n "$_atf_expected_exit" ]; then
        if [ "$_atf_expected_exit_neg" = true ]; then
            if [ "$_atf_actual_exit" -eq "$_atf_expected_exit" ]; then
                echo "  FAIL: $_atf_current_test: expected exit != $_atf_expected_exit, got $_atf_actual_exit"
                _atf_failed=true
            fi
        else
            if [ "$_atf_actual_exit" -ne "$_atf_expected_exit" ]; then
                echo "  FAIL: $_atf_current_test: expected exit $_atf_expected_exit, got $_atf_actual_exit"
                _atf_failed=true
            fi
        fi
    fi

    # Check stdout
    if [ "$_atf_stdout_empty" = true ]; then
        if [ -n "$_atf_stdout" ]; then
            echo "  FAIL: $_atf_current_test: expected empty stdout, got: $_atf_stdout"
            _atf_failed=true
        fi
    fi

    if [ -n "$_atf_stdout_inline" ]; then
        if [ "$_atf_stdout" != "$_atf_stdout_inline" ]; then
            echo "  FAIL: $_atf_current_test: stdout mismatch"
            echo "    expected: $_atf_stdout_inline"
            echo "    got:      $_atf_stdout"
            _atf_failed=true
        fi
    fi

    for _p in $_atf_stdout_patterns; do
        if ! echo "$_atf_stdout" | grep -q "$_p"; then
            echo "  FAIL: $_atf_current_test: stdout does not match '$_p'"
            echo "    stdout: $_atf_stdout"
            _atf_failed=true
        fi
    done

    for _p in $_atf_stdout_not_match; do
        if echo "$_atf_stdout" | grep -q "$_p"; then
            echo "  FAIL: $_atf_current_test: stdout matches '$_p' (should not)"
            _atf_failed=true
        fi
    done

    # Check stderr
    if [ "$_atf_stderr_empty" = true ]; then
        if [ -n "$_atf_stderr" ]; then
            echo "  FAIL: $_atf_current_test: expected empty stderr, got: $_atf_stderr"
            _atf_failed=true
        fi
    fi

    if [ -n "$_atf_stderr_inline" ]; then
        if [ "$_atf_stderr" != "$_atf_stderr_inline" ]; then
            echo "  FAIL: $_atf_current_test: stderr mismatch"
            _atf_failed=true
        fi
    fi

    for _p in $_atf_stderr_patterns; do
        if ! echo "$_atf_stderr" | grep -q "$_p"; then
            echo "  FAIL: $_atf_current_test: stderr does not match '$_p'"
            _atf_failed=true
        fi
    done

    for _p in $_atf_stderr_not_match; do
        if echo "$_atf_stderr" | grep -q "$_p"; then
            echo "  FAIL: $_atf_current_test: stderr matches '$_p' (should not)"
            _atf_failed=true
        fi
    done

    if [ "$_atf_failed" = true ]; then
        return 1
    fi
    return 0
}

# atf_test_case — declare a test case (no-op in shim, used for metadata)
atf_test_case() {
    :
}

# atf_add_test_case — add a test case (used by atf_init_test_cases)
_atf_test_cases=""
atf_add_test_case() {
    _atf_test_cases="$_atf_test_cases $1"
}

# Run tests from a test script
# Usage: _atf_run_test <test_file_path> [test_source_dir]
_atf_run_test() {
    _atf_test_file="$1"
    _atf_srcdir="${2:-$(dirname "$_atf_test_file")}"

    if [ ! -f "$_atf_test_file" ]; then
        echo "SKIP: test file not found: $_atf_test_file"
        return
    fi

    echo "=== Running tests from: $(basename "$_atf_test_file") ==="

    # Reset test state
    _atf_test_cases=""
    _atf_pass=0
    _atf_fail=0
    _atf_skip=0
    _atf_total=0

    # Source the test script
    . "$_atf_test_file"

    # Call atf_init_test_cases to discover tests
    atf_init_test_cases

    # Run each test case
    for _tc in $_atf_test_cases; do
        _atf_current_test="$_tc"
        _atf_total=$((_atf_total + 1))
        _atf_test_body="${_tc}_body"
        _atf_skip_flag=false

        if type "$_atf_test_body" >/dev/null 2>&1; then
            if "$_atf_test_body"; then
                echo "  PASS: $_tc"
                _atf_pass=$((_atf_pass + 1))
            elif [ "$_atf_skip_flag" = true ]; then
                # atf_require_prog triggered a skip: count as skip, not fail.
                _atf_skip=$((_atf_skip + 1))
            else
                _atf_fail=$((_atf_fail + 1))
            fi
        else
            echo "  FAIL: $_tc: test body function not found"
            _atf_fail=$((_atf_fail + 1))
        fi
    done

    echo "  Tests: $_atf_total, Pass: $_atf_pass, Fail: $_atf_fail, Skip: $_atf_skip"
    echo ""

    if [ "$_atf_fail" -gt 0 ]; then
        return 1
    fi
    return 0
}

# Entry point: execute the command passed as arguments
eval "$@"