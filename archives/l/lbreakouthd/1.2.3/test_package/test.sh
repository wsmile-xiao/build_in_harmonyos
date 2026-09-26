#!/data/service/hnp/bin/bash
# test_package/test.sh — lbreakouthd headless smoke test.
#
# R34/PF3: this genuinely executes the packaged binary (not a print-only
# stub). The recipe is built with --disable-install so levels/themes ship at
# the package root; we copy them to a temp working dir and run
# bin/lbreakouthd there with SDL dummy video+audio drivers and the
# software-renderer fallback (patch 0004). The full game boots headless and
# the menu loop keeps running, so `timeout` returns 124 (still alive) or 0
# (clean exit) — proof that ELF loading, SDL init and config/hiscores/theme
# loading all work without crashing on OHOS. The package itself stays
# pristine (config/hiscores are only written to the temp dir).
set -u

BIN="${1:?usage: test.sh <path-to-lbreakouthd> <package-dir>}"
DATA_DIR="${2:-$(dirname "$(dirname "$BIN")")}"

[ -x "$BIN" ] || { echo "[test] binary not found or not executable: $BIN"; exit 1; }
[ -d "$DATA_DIR/levels" ] || { echo "[test] data dir missing levels/: $DATA_DIR"; exit 1; }

WORK="$(mktemp -d /storage/Users/currentUser/tmp/lbo-test.XXXXXX)" || WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cp -r "$DATA_DIR/levels" "$WORK/"
cp -r "$DATA_DIR/themes" "$WORK/"
[ -f "$DATA_DIR/lbreakouthd.hscr" ] && cp "$DATA_DIR/lbreakouthd.hscr" "$WORK/"

cd "$WORK" || { echo "[test] cannot cd to $WORK"; exit 1; }
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy

out="$(timeout 12 "$BIN" 2>&1)"
rc=$?

if [ "$rc" -ne 124 ] && [ "$rc" -ne 0 ]; then
    echo "[test] FAILED: lbreakouthd exited rc=$rc (crash during startup?)"
    echo "$out" | head -20
    exit 1
fi

if ! echo "$out" | grep -q "lbreakouthd 1.2.3"; then
    echo "[test] FAILED: version banner not printed"
    echo "$out" | head -20
    exit 1
fi

echo "$out" | grep -E "Initializing SDL|fell back to software renderer|Loading theme" | head -3
echo "[test] PASS: lbreakouthd headless run OK (rc=$rc, banner present, no crash)"
exit 0
