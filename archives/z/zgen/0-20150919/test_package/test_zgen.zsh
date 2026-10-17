#!/usr/bin/env zsh
# zgen test_package — functional assertions executed by a real zsh.
#
# usage: zsh -f test_zgen.zsh <path-to-installed-zgen.zsh>
#
# zgen is an interpreted, architecture independent plugin manager, so running
# it under the build machine's zsh exercises the very same code that ships to
# the OHOS aarch64 target. ZGEN_DIR is redirected into a private sandbox
# directory passed through the environment, so the test never writes to $HOME.
# NOTE: no `setopt no_unset` here — zgen.zsh legitimately probes unset
# variables (`[[ -z "${ZGEN_INIT}" ]]`) to compute its defaults.
emulate -L zsh

local script="${1:?usage: test_zgen.zsh <zgen.zsh>}"
[[ -r "$script" ]] || { print -ru2 -- "[FAIL] cannot read $script"; exit 2; }

source "$script" || { print -ru2 -- "[FAIL] sourcing zgen.zsh failed"; exit 10; }

typeset -f zgen >/dev/null || { print -ru2 -- "[FAIL] zgen() undefined after source"; exit 11 }
print -- "[ok] zgen() defined after source"

local out rc
out="$(zgen 2>&1)"; rc=$?
[[ $rc -eq 1 ]] || { print -ru2 -- "[FAIL] bare 'zgen' rc=$rc, expected 1"; exit 12 }
[[ "$out" == *"usage: zgen"* ]] || { print -ru2 -- "[FAIL] bare 'zgen' printed: $out"; exit 13 }
print -- "[ok] 'zgen' prints usage and returns 1"

out="$(zgen list 2>&1)"
[[ "$out" == *"init.zsh missing"* ]] \
	|| { print -ru2 -- "[FAIL] 'zgen list' printed: $out"; exit 14 }
print -- "[ok] 'zgen list' reports the missing init.zsh"

zgen saved
rc=$?
[[ $rc -ne 0 ]] || { print -ru2 -- "[FAIL] 'zgen saved' returned 0 without init.zsh"; exit 15 }
print -- "[ok] 'zgen saved' returns non-zero without init.zsh"

out="$(zgen definitely-not-a-subcommand 2>&1)"
[[ "$out" == *"command not found"* ]] \
	|| { print -ru2 -- "[FAIL] unknown subcommand printed: $out"; exit 16 }
print -- "[ok] unknown subcommand is rejected"

typeset -f zgen-load zgen-save zgen-reset zgen-oh-my-zsh zgen-prezto >/dev/null \
	|| { print -ru2 -- "[FAIL] public zgen-* subcommand functions missing"; exit 17 }
print -- "[ok] public zgen-* subcommand functions exported"

[[ "$ZGEN_DIR" == "${ZGEN_EXPECTED_DIR:?ZGEN_EXPECTED_DIR must be injected by the caller}" ]] \
	|| { print -ru2 -- "[FAIL] ZGEN_DIR=$ZGEN_DIR escaped the sandbox"; exit 18 }
[[ "$ZGEN_INIT" == "$ZGEN_DIR/init.zsh" ]] \
	|| { print -ru2 -- "[FAIL] ZGEN_INIT=$ZGEN_INIT not derived from ZGEN_DIR"; exit 19 }
print -- "[ok] ZGEN_DIR/ZGEN_INIT honour the sandbox"

print -- "[PASS] zgen functional checks: 7 assertions"
