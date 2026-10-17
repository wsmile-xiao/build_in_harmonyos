#!/bin/sh
# zgen test_package — package layout and content assertions.
#
# Runs on any POSIX shell (no zsh required), so it also guards CI machines
# that have no zsh installed. Functional zsh assertions live in test_zgen.zsh.
set -eu

SHARE_DIR="${1:?usage: test.sh <zgen-share-dir> <zsh-site-functions-dir>}"
FPATH_DIR="${2:?usage: test.sh <zgen-share-dir> <zsh-site-functions-dir>}"

fail() { echo "[FAIL] $1" >&2; exit 1; }
ok() { echo "[ok] $1"; }

[ -f "$SHARE_DIR/zgen.zsh" ] || fail "zgen.zsh is missing in $SHARE_DIR"
ok "zgen.zsh installed"

[ -x "$SHARE_DIR/zgen.zsh" ] || fail "zgen.zsh is not executable"
ok "zgen.zsh has the executable bit"

[ -f "$SHARE_DIR/LICENSE" ] || fail "LICENSE is missing in $SHARE_DIR"
ok "LICENSE installed"

[ -f "$FPATH_DIR/_zgen" ] || fail "_zgen completion is missing in $FPATH_DIR"
ok "_zgen completion installed on FPATH"

head -n 1 "$SHARE_DIR/zgen.zsh" | grep -q '^#!/usr/bin/env zsh$' \
	|| fail "OHOS shebang patch not applied (expected '#!/usr/bin/env zsh')"
ok "OHOS shebang patch applied"

head -n 1 "$SHARE_DIR/zgen.zsh" | grep -q '^#!/bin/zsh$' \
	&& fail "upstream /bin/zsh shebang still present"
ok "no hardcoded /bin/zsh interpreter"

grep -q '^#compdef zgen' "$FPATH_DIR/_zgen" \
	|| fail "_zgen does not declare '#compdef zgen'"
ok "_zgen declares #compdef zgen"

for fn in zgen zgen-load zgen-save zgen-reset zgen-list zgen-saved \
	zgen-update zgen-selfupdate zgen-oh-my-zsh zgen-prezto zgen-clone; do
	grep -q "^${fn}() {" "$SHARE_DIR/zgen.zsh" \
		|| fail "function ${fn}() is not defined in zgen.zsh"
	ok "function ${fn}() defined"
done

echo "[PASS] zgen package layout: 18 assertions"
