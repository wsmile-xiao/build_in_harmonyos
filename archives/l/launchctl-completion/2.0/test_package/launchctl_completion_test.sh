#!/bin/bash
# launchctl_completion_test.sh — static smoke for the launchctl-completion
# 2.0 data package (upstream has no test suite: NO_UPSTREAM_TESTS, see
# MANIFEST.yml / EXCLUDED-TESTS.md / UPSTREAM-TESTS-EVIDENCE.json).
#
# Assertions are aligned one-to-one with the OHOS adaptation decisions
# (zero-test-upstream "adaptation-point smoke" pattern, lazycontainer
# precedent): every check guards a packaging decision, none depends on the
# macOS `launchctl` binary or any other external command.
#
# Environment contract (set by test_package/conanfile.py):
#   BASH_BIN   absolute path of the bash/5.3 dependency binary
#   PKG_ROOT   package folder of launchctl-completion/2.0
#   TEST_SRC   this test_package source folder (evidence files live here)
#
# OHOS discipline: every bash invocation goes through "$BASH_BIN" explicitly
# (never exec-by-shebang: knowledge E037/E363 — OHOS has no /usr/local/bin);
# nothing is written to /tmp (read-only erofs: knowledge E002/E325) — this
# runner creates no temporary files at all. The completion smoke drives the
# COMP_CWORD=1 path of _launchctl2, which is pure builtins (compgen): it
# returns before the script's log() helper or any external command runs.
set -u

PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); echo "PASS: $*"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL: $*"; }

require_env() {
    local missing=0
    for v in BASH_BIN PKG_ROOT TEST_SRC; do
        if [ -z "$(eval "printf '%s' \"\${$v:-}\"")" ]; then
            echo "FAIL: required env var $v is not set"
            missing=$((missing + 1))
        fi
    done
    [ "$missing" -eq 0 ] || exit 2
}
require_env

COMPLETION="$PKG_ROOT/share/bash-completion/completions/launchctl"
LICENSE="$PKG_ROOT/licenses/LICENSE"
EVIDENCE="$TEST_SRC/UPSTREAM-TESTS-EVIDENCE.json"

# SHA256 pins: byte-identity between the installed data files and upstream
# v2.0 (tarball sha256 990499494562cedf361482c5bf9f89b3a8b6a8aee92fda4e1ead
# aacb96688ecd, double-sourced against the Homebrew formula declaration).
EXPECTED_COMPLETION_SHA256="17df5430689d60d4bf7b555d0e00adf215b2c09037235d65abdc83a931249f0b"
EXPECTED_LICENSE_SHA256="898275fba946f95c028e23a6849c22e29eb47e772bfc84fc1c30a82e515e7e5b"

sha256_of() {
    # Portable across device toolchains: prefer sha256sum, fall back to
    # the openssl applet (both available in the OHOS environment).
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        openssl dgst -sha256 "$1" | sed 's/^.*= //'
    fi
}

echo "== launchctl-completion/2.0 static smoke =="

# ── Check 1: the harness bash satisfies the completion's hard floor.
# The script needs `compgen -V varname` (bash 5.3 NEWS) and `local -n`
# (bash >= 4.3). This pins the requires("bash/5.3") contract end-to-end.
BASH_VERSION_STR=$("$BASH_BIN" -c 'echo "$BASH_VERSION"')
BASH_MAJOR=${BASH_VERSION_STR%%.*}
BASH_MINOR=$(echo "$BASH_VERSION_STR" | cut -d. -f2 | cut -c1-2)
if [ "${BASH_MAJOR:-0}" -gt 5 ] || { [ "${BASH_MAJOR:-0}" -eq 5 ] && [ "${BASH_MINOR:-0}" -ge 3 ]; }; then
    ok "bash >= 5.3 (got $BASH_VERSION_STR at $BASH_BIN)"
else
    bad "bash >= 5.3 required, got $BASH_VERSION_STR at $BASH_BIN"
fi

# ── Check 2: syntax gate — `bash -n` on the installed completion file.
# (Must be bash, not zsh: the file is bash-only, `zsh -n` misreports bashisms.)
if "$BASH_BIN" -n "$COMPLETION" 2>/dev/null; then
    ok "bash -n syntax check: $COMPLETION"
else
    bad "bash -n syntax check failed: $COMPLETION"
fi

# ── Check 3: load + registration assertion (replicates the upstream
# Homebrew formula test block: source the file, `complete -p launchctl`).
REG_OUT=$("$BASH_BIN" -c '
    source "$1"
    complete -p launchctl
' _ "$COMPLETION" 2>/dev/null)
if [ "$REG_OUT" = "complete -F _launchctl2 launchctl" ]; then
    ok "registration: complete -p launchctl == '$REG_OUT'"
else
    bad "registration: expected 'complete -F _launchctl2 launchctl', got '$REG_OUT'"
fi

# ── Check 4: the completion function is defined after sourcing.
FUNC_TYPE=$("$BASH_BIN" -c '
    source "$1" 2>/dev/null
    type -t _launchctl2
' _ "$COMPLETION" 2>/dev/null)
if [ "$FUNC_TYPE" = "function" ]; then
    ok "_launchctl2 is defined (type -t == function)"
else
    bad "_launchctl2 not defined after sourcing (type -t: '$FUNC_TYPE')"
fi

# ── Check 5: static first-level completion smoke. COMP_CWORD=1 hits the
# pure-builtin literal branch (`compgen -V COMPREPLY -W "${subcommands[*]}"`)
# and returns before any dynamic source (launchctl/dscl//Library/Launch*)
# or the unguarded `launchctl list` call sites could run. Completing the
# empty word must yield exactly the 44 upstream subcommand literals.
REPLIES=$("$BASH_BIN" -c '
    source "$1" 2>/dev/null
    COMP_WORDS=(launchctl "")
    COMP_CWORD=1
    _launchctl2 2>/dev/null
    printf "%s\n" "${COMPREPLY[@]}"
' _ "$COMPLETION" 2>/dev/null | sort)
REPLY_COUNT=$(printf '%s\n' "$REPLIES" | grep -c .)
if [ "$REPLY_COUNT" -eq 44 ]; then
    ok "static first-level completion yields exactly 44 subcommands"
else
    bad "static first-level completion: expected 44 subcommands, got $REPLY_COUNT"
fi
MISSING_MEMBERS=$(printf '%s\n' bootstrap bootout kickstart list help version | while read -r m; do
    printf '%s\n' "$REPLIES" | grep -qx "$m" || echo "$m"
done)
if [ -z "$MISSING_MEMBERS" ]; then
    ok "key subcommand members present (bootstrap/bootout/kickstart/list/help/version)"
else
    bad "subcommand members missing: $MISSING_MEMBERS"
fi

# ── Check 6: install layout matches the Homebrew/Conan contract.
if [ -f "$COMPLETION" ]; then
    ok "install layout: share/bash-completion/completions/launchctl exists"
else
    bad "install layout: $COMPLETION missing"
fi

# ── Check 7: installed completion content is byte-identical to upstream.
ACTUAL_SHA=$(sha256_of "$COMPLETION")
if [ "$ACTUAL_SHA" = "$EXPECTED_COMPLETION_SHA256" ]; then
    ok "installed completion sha256 == upstream pin ($ACTUAL_SHA)"
else
    bad "installed completion sha256 $ACTUAL_SHA != upstream pin $EXPECTED_COMPLETION_SHA256"
fi

# ── Check 8: license retained (Conan licenses/ convention), byte-identical.
ACTUAL_LIC_SHA=$(sha256_of "$LICENSE")
if [ "$ACTUAL_LIC_SHA" = "$EXPECTED_LICENSE_SHA256" ]; then
    ok "licenses/LICENSE sha256 == upstream pin ($ACTUAL_LIC_SHA)"
else
    bad "licenses/LICENSE sha256 $ACTUAL_LIC_SHA != upstream pin $EXPECTED_LICENSE_SHA256"
fi

# ── Check 9: NO_UPSTREAM_TESTS machine-readable evidence file is present
# and carries the gate status + discovery marker (lazycontainer precedent:
# machine-readable, re-checkable from the audit trail).
if [ -f "$EVIDENCE" ] \
   && grep -q '"status"[[:space:]]*:[[:space:]]*"not_applicable"' "$EVIDENCE" \
   && grep -q '"discovery"[[:space:]]*:[[:space:]]*"NO_UPSTREAM_TESTS"' "$EVIDENCE" \
   && grep -q '"discovered"[[:space:]]*:[[:space:]]*0' "$EVIDENCE"; then
    ok "NO_UPSTREAM_TESTS evidence file present with gate markers"
else
    bad "NO_UPSTREAM_TESTS evidence file missing or malformed: $EVIDENCE"
fi

# ── Summary (machine-readable tail, lazycontainer precedent).
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\": true, \"passed\": $([ "$FAIL" -eq 0 ] && echo true || echo false), \"discovered\": 10, \"passedCount\": $PASS, \"failedCount\": $FAIL, \"upstreamTests\": \"NO_UPSTREAM_TESTS (upstream v2.0 ships LICENSE + one script; no test suite)\"}"
echo "== smoke summary: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
