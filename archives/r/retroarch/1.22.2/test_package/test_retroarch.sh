#!/bin/sh
# Consumer test for the packaged RetroArch binary on OpenHarmony PC.
# Each check is a real process run; failures are counted, not ignored.
#
# R40 note: RetroArch is a graphics/multimedia frontend; this package is a
# headless, no-GPU-target build (see notes.md). The checks below cover the
# CLI surface only -- 「适配完整性需人工确认」: loading a libretro core and
# rendering requires GPU/audio backends that the OHOS target does not
# provide, and must be confirmed manually once such backends exist.
set -euo pipefail

BIN="${RETROARCH_BIN:?RETROARCH_BIN must point at the packaged retroarch}"
pass=0
fail=0
tmp="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-.}/ra_test_$$")"
mkdir -p "$tmp"

grep_check() {
   desc="$1"; pattern="$2"; shift 2
   if "$@" >"$tmp/out" 2>&1 && grep -q "$pattern" "$tmp/out"; then
      echo "ok  - $desc"
      pass=$((pass + 1))
   else
      echo "FAIL- $desc (missing '$pattern')"
      sed 's/^/      /' "$tmp/out" || true
      fail=$((fail + 1))
   fi
}

# 1) version banner
grep_check "--version prints version 1.22.2" "1.22.2" "$BIN" --version
# 2) help banner
grep_check "--help lists usage" "Usage:" "$BIN" --help
# 3) compiled feature list is produced
grep_check "--features prints compiled-in features" "Features:" "$BIN" --features
# 4) an unknown option is rejected with a non-zero exit
if "$BIN" --definitely-not-an-option >"$tmp/out" 2>&1; then
   echo "FAIL- unknown option accepted (expected non-zero exit)"
   fail=$((fail + 1))
else
   echo "ok  - unknown option rejected"
   pass=$((pass + 1))
fi

echo "RETROARCH_CONSUMER_SUMMARY pass=$pass fail=$fail"
rm -rf "$tmp"
[ "$fail" -eq 0 ]
