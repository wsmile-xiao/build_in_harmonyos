#!/usr/bin/env bash
# R34: real smoke test for powerlevel10k 1.20.0 — consumer perspective.
#
# The theme is pure zsh: nothing to execute directly; it is sourced by the
# user's zshrc.  This suite exercises the installed share/powerlevel10k tree:
#
#   A. layout integrity (upstream files present, nothing lost in packaging)
#   B. zsh -n syntax checks on the core scripts (parse only, no execution)
#   C. real theme load inside a clean zsh (GITSTATUS_AUTO_INSTALL=0 so the
#      test never tries to download/build gitstatusd): exit code 0, the
#      p10k entry function defined, and a vcs backend ready — either the
#      gitstatusd path (gitstatus_query, on hosts whose zsh ships the
#      zsh/files module) or the native vcs_info fallback
#      (_p9k_vcs_info_init).  The daemon is intentionally not packaged
#      (see ../notes.md), so on this platform the fallback is the expected
#      backend — both loaded states are valid.
set -u

PASS=0
FAIL=0

THEME_DIR="${1:?usage: test.sh <package share/powerlevel10k dir>}"
ZSH_BIN="${ZSH:-zsh}"

pass() { PASS=$((PASS + 1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "FAIL: $1"; }

command -v "$ZSH_BIN" >/dev/null 2>&1 || {
    echo "FAIL: zsh interpreter not found (ZSH_BIN='$ZSH_BIN')"
    exit 1
}

# ── A. layout integrity (8 assertions) ──────────────────────────
for f in \
    powerlevel10k.zsh-theme \
    prompt_powerlevel10k_setup \
    internal/p10k.zsh \
    internal/wizard.zsh \
    internal/configure.zsh \
    config/p10k-rainbow.zsh \
    gitstatus/gitstatus.plugin.zsh \
    LICENSE
do
    if [ -f "$THEME_DIR/$f" ]; then
        pass "present: $f"
    else
        fail "missing: $f"
    fi
done

# ── B. zsh syntax checks (3 assertions) ─────────────────────────
for f in powerlevel10k.zsh-theme internal/p10k.zsh gitstatus/gitstatus.plugin.zsh; do
    if "$ZSH_BIN" -n "$THEME_DIR/$f" 2>/dev/null; then
        pass "zsh -n: $f"
    else
        fail "zsh -n: $f (syntax error)"
    fi
done

# ── C. real load test (3 assertions) ────────────────────────────
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

LOAD_OUT="$(GITSTATUS_AUTO_INSTALL=0 P10K_THEME_DIR="$THEME_DIR" \
    "$ZSH_BIN" -df +m -c '
        source "$P10K_THEME_DIR/powerlevel10k.zsh-theme"
        print -r -- "p10k=$(( ${+functions[p10k]} ))"
        print -r -- "vcs_info_fallback=$(( ${+functions[_p9k_vcs_info_init]} ))"
        print -r -- "gitstatus=$(( ${+functions[gitstatus_query]} ))"
    ' 2>"$SCRATCH/load.stderr")"
LOAD_RC=$?

if [ "$LOAD_RC" -eq 0 ]; then
    pass "theme load: exit 0"
else
    fail "theme load: exit $LOAD_RC (stderr: $(tail -2 "$SCRATCH/load.stderr" 2>/dev/null | tr '\n' ' '))"
fi

# the p10k entry function must be defined after sourcing the theme
if echo "$LOAD_OUT" | grep -q '^p10k=1$'; then
    pass "p10k function defined after load"
else
    fail "p10k function NOT defined (load stdout: $(echo "$LOAD_OUT" | tr '\n' ' '))"
fi

# a vcs backend must be ready: gitstatusd path (gitstatus_query) OR the
# native vcs_info fallback (_p9k_vcs_info_init)
VCS_READY=0
echo "$LOAD_OUT" | grep -q '^vcs_info_fallback=1$' && VCS_READY=1
echo "$LOAD_OUT" | grep -q '^gitstatus=1$' && VCS_READY=1
if [ "$VCS_READY" -eq 1 ]; then
    pass "vcs backend ready ($(echo "$LOAD_OUT" | grep -oE '^(vcs_info_fallback|gitstatus)=[01]' | tr '\n' ' '))"
else
    fail "no vcs backend (neither gitstatus nor vcs_info fallback armed)"
fi

echo "powerlevel10k smoke test: pass=$PASS fail=$FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "--- load stderr (diagnostics) ---"
    tail -5 "$SCRATCH/load.stderr" 2>/dev/null | sed 's/^/    /'
    exit 1
fi
echo "powerlevel10k: OK"
exit 0
