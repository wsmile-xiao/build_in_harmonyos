#!/bin/sh
# Minimal ATF (Automated Testing Framework) shim for abuild upstream tests.
# Provides the atf_check, atf_fail, atf_require_prog, atf_get_srcdir
# functions needed by abuild's ATF-based test suite, without requiring
# the full kyua/atf packages.
#
# 2026-08-20 round fixes (verified against upstream tests/*_test sources):
#  1. match:/not-match: patterns are matched with `grep -E` (ERE).  Real atf
#     treats match: as an extended regex; the old BRE grep made upstream
#     patterns like `[0-9]+\.[0-9]+` and `(Generating|writing) RSA` fail
#     (BRE treats `+`, `(...)`, `|` as literals).
#  2. Multi-word patterns are kept intact (IFS=newline iteration) instead of
#     being word-split into one grep per word.
#  3. `-o/-e not-empty` and `-o/-e ignore` are supported (previously silently
#     dropped, which either missed real assertions or skipped them silently).
#  4. `inline:` interprets backslash escapes via printf %b and compares
#     exactly (trailing-newline aware), so `inline:'strip\n'` matches a
#     stdout of "strip\n" (abuild_strip relies on this).
#  5. Failure counting is per test case: atf_fail/atf_check mark the current
#     test as failed (_atf_fail_flag) and the runner increments _atf_fail
#     exactly once per failing test.  Previously atf_fail incremented the
#     counter AND the runner did too (double counting: 140 "failures" for 67
#     failing tests in the first real device run).
#  6. Every test case runs in a FRESH work directory with HOME pointing at
#     it, mirroring real atf-sh/kyua: the test program's top-level code is
#     re-sourced inside that workdir, so exports like
#     ABUILD_USERDIR="$HOME/.abuild" and REPODEST="$PWD"/packages are
#     recomputed per case.  Without this, cases polluted each other through
#     the shared cwd and $HOME: keygen wrote $HOME/.abuild/abuild.conf and
#     sign's "No private key found" cases then found a key (3 device
#     failures), fetch's leftover bin/curl made the wget-fallback cases
#     invoke curl, and abuild_test's shared {src}/packages made
#     abuild_reproducible delete other cases' artifacts.
#  7. match:/not-match: patterns are passed to grep via -e so that patterns
#     starting with '-' (e.g. "--insecure", "--no-check-certificate") are
#     not mistaken for grep options (toybox/BSD grep: "unknown option").
#  8. 2026-08-24: match:/not-match: output is matched against the RAW
#     captured stdout/stderr FILE, not `echo "$_atf_out" | grep`.  OHOS
#     toybox echo interprets backslash escapes, so a literal `\b` in the
#     captured output became a backspace before grep saw it.  The pattern is
#     passed through unmodified (upstream atf ERE semantics): the former
#     `\b` -> `\\b` sed turned abuild_deps' `\\b` into `\\\b` (literal `\` +
#     word-boundary assertion) which can never match.

# Test state
_atf_pass=0
_atf_fail=0
_atf_skip=0
_atf_total=0
_atf_current_test=""
_atf_srcdir=""
_atf_fail_flag=false
_atf_skip_flag=false

# A literal newline, used to split pattern lists without word-splitting them.
_atf_nl="
"

# Resolve core tool paths at load time. Upstream test scripts override PATH
# (e.g. abuild_fetch_test sets PATH="$PWD/bin:$(atf_get_srcdir)/.."), which
# would otherwise make mktemp/cat/rm/grep unfindable inside atf_check.
# OHOS toybox exposes these as aliases, so unalias them first or command -v
# returns "alias mktemp=mktemp" which cannot be executed as a command.
# NOTE: do NOT `unalias -a` — `type` itself is an alias on toybox
# (`alias type='\builtin whence -v'`), and function detection below relies on it.
unalias mktemp cat rm grep dirname cmp 2>/dev/null || true
_ATF_MKTEMP=$(command -v mktemp 2>/dev/null || echo mktemp)
_ATF_CAT=$(command -v cat 2>/dev/null || echo cat)
_ATF_RM=$(command -v rm 2>/dev/null || echo rm)
_ATF_GREP=$(command -v grep 2>/dev/null || echo grep)
_ATF_DIRNAME=$(command -v dirname 2>/dev/null || echo dirname)

# atf_get_srcdir — returns the directory containing the test script
atf_get_srcdir() {
    if [ -n "$_atf_srcdir" ]; then
        echo "$_atf_srcdir"
    else
        # Default: current directory
        echo "."
    fi
}

# atf_fail — fail the current test with a message.
# Marks the current test as failed (counted once by the runner).
atf_fail() {
    echo "FAIL: $_atf_current_test: $*"
    _atf_fail_flag=true
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
#           -o match:<pattern> | -o not-match:<pattern>       (ERE, like atf)
#           -o inline:<text>   | -o empty | -o not-empty | -o ignore
#           -e match:<pattern> | -e not-match:<pattern>
#           -e inline:<text>   | -e empty | -e not-empty | -e ignore
atf_check() {
    _atf_expected_exit=""
    _atf_expected_exit_neg=false
    _atf_stdout_patterns=""
    _atf_stderr_patterns=""
    _atf_stdout_not_match=""
    _atf_stderr_not_match=""
    _atf_stdout_inline=""
    _atf_stderr_inline=""
    _atf_stdout_empty=false
    _atf_stderr_empty=false
    _atf_stdout_not_empty=false
    _atf_stderr_not_empty=false

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
                    match:*) _atf_stdout_patterns="$_atf_stdout_patterns$_atf_nl${1#match:}" ;;
                    not-match:*) _atf_stdout_not_match="$_atf_stdout_not_match$_atf_nl${1#not-match:}" ;;
                    inline:*) _atf_stdout_inline="${1#inline:}" ;;
                    empty) _atf_stdout_empty=true ;;
                    not-empty) _atf_stdout_not_empty=true ;;
                    ignore) : ;;
                    *) echo "  WARN: $_atf_current_test: unsupported -o option '$1' ignored" ;;
                esac
                shift ;;
            -e)
                shift
                case "$1" in
                    match:*) _atf_stderr_patterns="$_atf_stderr_patterns$_atf_nl${1#match:}" ;;
                    not-match:*) _atf_stderr_not_match="$_atf_stderr_not_match$_atf_nl${1#not-match:}" ;;
                    inline:*) _atf_stderr_inline="${1#inline:}" ;;
                    empty) _atf_stderr_empty=true ;;
                    not-empty) _atf_stderr_not_empty=true ;;
                    ignore) : ;;
                    *) echo "  WARN: $_atf_current_test: unsupported -e option '$1' ignored" ;;
                esac
                shift ;;
            *)
                break ;;
        esac
    done

    # Run the command. Use TMPDIR (or the shim's own directory as fallback)
    # instead of /tmp: OHOS /tmp is read-only and mktemp there fails.
    _atf_tmpdir="${TMPDIR:-$("$_ATF_DIRNAME" "$0")}"

    # Verify the temp dir is usable before creating files: a failed mktemp
    # would otherwise surface as confusing "cat: ''" / "rm: missing operand"
    # errors that blame the tested command instead of the harness.
    if [ ! -d "$_atf_tmpdir" ] || [ ! -w "$_atf_tmpdir" ]; then
        echo "  FAIL: $_atf_current_test: temp dir not usable: $_atf_tmpdir"
        _atf_fail_flag=true
        return 1
    fi
    _atf_stdout_file=$("$_ATF_MKTEMP" "$_atf_tmpdir/atf_stdout.XXXXXX") || {
        echo "  FAIL: $_atf_current_test: mktemp failed for stdout in $_atf_tmpdir"
        _atf_fail_flag=true
        return 1
    }
    _atf_stderr_file=$("$_ATF_MKTEMP" "$_atf_tmpdir/atf_stderr.XXXXXX") || {
        echo "  FAIL: $_atf_current_test: mktemp failed for stderr in $_atf_tmpdir"
        "$_ATF_RM" -f "$_atf_stdout_file"
        _atf_fail_flag=true
        return 1
    }
    "$@" >"$_atf_stdout_file" 2>"$_atf_stderr_file"
    _atf_actual_exit=$?
    _atf_stdout=$("$_ATF_CAT" "$_atf_stdout_file")
    _atf_stderr=$("$_ATF_CAT" "$_atf_stderr_file")

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

    if [ "$_atf_stdout_not_empty" = true ]; then
        if [ -z "$_atf_stdout" ]; then
            echo "  FAIL: $_atf_current_test: expected non-empty stdout, got empty"
            _atf_failed=true
        fi
    fi

    # inline: interpret backslash escapes (printf %b), then compare exactly,
    # ignoring trailing newlines on both sides ($(cat) already strips them
    # from the captured output; strip them from the expected value too).
    if [ -n "$_atf_stdout_inline" ]; then
        _atf_expected_inline=$(printf '%b' "$_atf_stdout_inline")
        while [ "${_atf_expected_inline%"$_atf_nl"}" != "$_atf_expected_inline" ]; do
            _atf_expected_inline="${_atf_expected_inline%"$_atf_nl"}"
        done
        if [ "$_atf_stdout" != "$_atf_expected_inline" ]; then
            echo "  FAIL: $_atf_current_test: stdout mismatch"
            echo "    expected: $_atf_stdout_inline"
            echo "    got:      $_atf_stdout"
            _atf_failed=true
        fi
    fi

    # set -f disables glob expansion so patterns like "*" / "?" / "[" are
    # passed to grep literally instead of being expanded to matching files.
    # IFS=newline keeps multi-word patterns intact (upstream match: uses a
    # single ERE — word-splitting would weaken it into per-word greps).
    # Patterns are matched against the RAW captured output FILE (not
    # `echo "$_atf_stdout" | grep`): the OHOS toybox `echo` interprets
    # backslash escapes, so a literal `\b` inside the captured output was
    # silently turned into a backspace before grep ever saw it.  Matching
    # the file keeps the output bytes verbatim.  The pattern itself is
    # passed to grep EXACTLY as the test wrote it (upstream atf ERE
    # semantics): patterns like abuild_deps' `...It's \\b'...` already use
    # `\\` to mean a literal backslash, so any sed re-escaping only breaks
    # them (2026-08-24: the former `\b` -> `\\b` sed turned the pattern's
    # `\\b` into `\\\b`, i.e. literal `\` + a `\b` word-boundary assertion
    # that can never match between two non-word characters).
    _atf_oldifs=$IFS
    IFS=$_atf_nl
    set -f
    for _p in $_atf_stdout_patterns; do
        [ -n "$_p" ] || continue
        if ! "$_ATF_GREP" -E -q -e "$_p" "$_atf_stdout_file"; then
            echo "  FAIL: $_atf_current_test: stdout does not match '$_p'"
            echo "    stdout: $_atf_stdout"
            _atf_failed=true
        fi
    done

    for _p in $_atf_stdout_not_match; do
        [ -n "$_p" ] || continue
        if "$_ATF_GREP" -E -q -e "$_p" "$_atf_stdout_file"; then
            echo "  FAIL: $_atf_current_test: stdout matches '$_p' (should not)"
            _atf_failed=true
        fi
    done
    set +f
    IFS=$_atf_oldifs

    # Check stderr
    if [ "$_atf_stderr_empty" = true ]; then
        if [ -n "$_atf_stderr" ]; then
            echo "  FAIL: $_atf_current_test: expected empty stderr, got: $_atf_stderr"
            _atf_failed=true
        fi
    fi

    if [ "$_atf_stderr_not_empty" = true ]; then
        if [ -z "$_atf_stderr" ]; then
            echo "  FAIL: $_atf_current_test: expected non-empty stderr, got empty"
            _atf_failed=true
        fi
    fi

    if [ -n "$_atf_stderr_inline" ]; then
        _atf_expected_inline=$(printf '%b' "$_atf_stderr_inline")
        while [ "${_atf_expected_inline%"$_atf_nl"}" != "$_atf_expected_inline" ]; do
            _atf_expected_inline="${_atf_expected_inline%"$_atf_nl"}"
        done
        if [ "$_atf_stderr" != "$_atf_expected_inline" ]; then
            echo "  FAIL: $_atf_current_test: stderr mismatch"
            echo "    expected: $_atf_stderr_inline"
            echo "    got:      $_atf_stderr"
            _atf_failed=true
        fi
    fi

    _atf_oldifs=$IFS
    IFS=$_atf_nl
    set -f
    for _p in $_atf_stderr_patterns; do
        [ -n "$_p" ] || continue
        if ! "$_ATF_GREP" -E -q -e "$_p" "$_atf_stderr_file"; then
            echo "  FAIL: $_atf_current_test: stderr does not match '$_p'"
            echo "    stderr: $_atf_stderr"
            _atf_failed=true
        fi
    done

    for _p in $_atf_stderr_not_match; do
        [ -n "$_p" ] || continue
        if "$_ATF_GREP" -E -q -e "$_p" "$_atf_stderr_file"; then
            echo "  FAIL: $_atf_current_test: stderr matches '$_p' (should not)"
            _atf_failed=true
        fi
    done
    set +f
    IFS=$_atf_oldifs

    "$_ATF_RM" -f "$_atf_stdout_file" "$_atf_stderr_file"

    if [ "$_atf_failed" = true ]; then
        _atf_fail_flag=true
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

    # Run each test case.  A test is counted as failed exactly once:
    # - body returned non-zero (atf_check/atf_fail/return 1), or
    # - atf_fail/atf_check marked _atf_fail_flag even though the body
    #   happened to return 0 afterwards.
    # atf_fail no longer increments the counter itself (that double counted
    # every failing test: 140 counted failures for 67 failing tests).
    #
    # Per-test-case isolation (real atf-sh/kyua semantics, atf-test-case(4)):
    # each test case body runs in a FRESH work directory with HOME pointing
    # at it, and the test program's top-level code is re-sourced inside that
    # workdir so exports like ABUILD_USERDIR="$HOME/.abuild" and
    # REPODEST="$PWD/packages" are recomputed for THIS case.  abuild's tests
    # depend on this: sign/keygen manage keys under $HOME/.abuild, fetch
    # creates bin/ in $PWD, abuild_test copies testrepo/ into $PWD and
    # builds into $REPODEST.  Without isolation every case shared the same
    # cwd and HOME: keygen wrote $HOME/.abuild/abuild.conf and sign's
    # "No private key found" cases then found a key (3 device failures),
    # fetch's leftover bin/curl made the wget-fallback cases invoke curl,
    # and abuild_test's shared {src}/packages made abuild_reproducible
    # delete other cases' artifacts (56 device failures total).
    _atf_cases=$_atf_test_cases
    # ATF_EXCLUDE_CASES: space-separated case names to drop from the
    # execution set entirely (NOT counted in Tests/Pass/Fail — the summary
    # line then reflects exactly the cases that ran).  Used for upstream
    # cases that are impossible on the OHOS platform (audited in
    # test_package/MANIFEST.yml): they are neither run nor counted, exactly
    # like the libgsf iconv case precedent.
    if [ -n "${ATF_EXCLUDE_CASES:-}" ]; then
        _atf_filtered=""
        for _tc in $_atf_cases; do
            case " $ATF_EXCLUDE_CASES " in
                *" $_tc "*)
                    echo "  SKIP: $_tc (excluded via ATF_EXCLUDE_CASES)"
                    ;;
                *)
                    _atf_filtered="$_atf_filtered $_tc"
                    ;;
            esac
        done
        _atf_cases=$_atf_filtered
    fi
    for _tc in $_atf_cases; do
        _atf_current_test="$_tc"
        _atf_total=$((_atf_total + 1))
        _atf_test_body="${_tc}_body"
        _atf_skip_flag=false
        _atf_fail_flag=false

        # Fresh workdir for this test case (under TMPDIR so it is writable).
        # Normalize to an absolute path via $PWD after cd: mktemp may return
        # a relative path when TMPDIR is relative/empty, and abuild's tests
        # rely on $PWD == $HOME (e.g. sign's init_keys copies testdata/.abuild
        # into $PWD while ABUILD_USERDIR="$HOME/.abuild"; abump's
        # ABUILD_USERDIR="$HOME/.abuild" with testdata/.abuild copied to .).
        _atf_workdir=$("$_ATF_MKTEMP" -d "${TMPDIR:-.}/atf-case.XXXXXX" 2>/dev/null) || _atf_workdir=""
        _atf_oldpwd=$PWD
        _atf_oldhome=${HOME:-}
        if [ -n "$_atf_workdir" ] && [ -d "$_atf_workdir" ]; then
            if cd "$_atf_workdir" 2>/dev/null; then
                _atf_workdir=$PWD
                HOME="$_atf_workdir"
                export HOME
                # Re-evaluate the test program's top-level exports against
                # this case's workdir (fresh .abuild, fresh REPODEST, ...).
                . "$_atf_test_file" 2>/dev/null || true
            else
                _atf_workdir=""
            fi
        fi

        if type "$_atf_test_body" >/dev/null 2>&1; then
            if "$_atf_test_body"; then
                if [ "$_atf_fail_flag" = true ]; then
                    echo "  FAIL: $_tc (atf_fail/atf_check reported failure)"
                    _atf_fail=$((_atf_fail + 1))
                else
                    echo "  PASS: $_tc"
                    _atf_pass=$((_atf_pass + 1))
                fi
            elif [ "$_atf_skip_flag" = true ]; then
                # atf_require_prog triggered a skip: count as skip, not fail.
                echo "  SKIP: $_tc"
                _atf_skip=$((_atf_skip + 1))
            else
                echo "  FAIL: $_tc"
                _atf_fail=$((_atf_fail + 1))
            fi
        else
            echo "  FAIL: $_tc: test body function not found"
            _atf_fail=$((_atf_fail + 1))
        fi

        # Restore the outer environment and clean up the case workdir.
        cd "$_atf_oldpwd" 2>/dev/null || true
        if [ -n "$_atf_oldhome" ]; then
            HOME="$_atf_oldhome"
        else
            unset HOME
        fi
        export HOME
        if [ -n "$_atf_workdir" ] && [ -d "$_atf_workdir" ]; then
            "$_ATF_RM" -rf "$_atf_workdir" 2>/dev/null || true
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
