#!/bin/sh
# Consumer test for xcmsdb 1.0.7 in a headless build / CI environment.
#
# xcmsdb is a real X client (it writes ICC colour database properties into the
# X server), so only the code paths that do not require a reachable server are
# asserted here:
#   1. the binary is resolvable through the consumer run environment
#   2. -version banner (handled before any XOpenDisplay call)
#   3. unknown option path, guarded by a hard timeout so a hang can never pass
#   4. -query with DISPLAY unset must terminate on its own (clean error
#      rather than a hang); both rc=0 and a non-zero clean failure are
#      accepted because a CI runner may or may not expose an X server
#   5. ELF NEEDED closure (readelf) - skipped, and reported as skipped, when no
#      readelf exists on the runner
# The sibling X packages dlopen libX11 from the same package lib directory, so
# the binary directory is kept on PATH for every invocation.
set -u
passed=0
skipped=0
fail() { echo "FAIL: $1"; exit 1; }

BIN=$(command -v xcmsdb || true)
[ -n "$BIN" ] || fail "xcmsdb not found on the conanrun PATH"
LIBDIR=$(dirname "$BIN")
echo "PASS 1: binary resolved -> $BIN"
passed=$((passed + 1))

out=$(PATH="$LIBDIR:$PATH" timeout 30 "$BIN" -version 2>&1); rc=$?
[ "$rc" = "124" ] && fail "-version hung for 30s"
[ "$rc" = "0" ] || fail "-version exit=$rc output=[$out]"
case "$out" in
  *1.0.7*) echo "PASS 2: -version -> $out" ;;
  *) fail "-version banner lacks 1.0.7: [$out]" ;;
esac
passed=$((passed + 1))

out3=$(PATH="$LIBDIR:$PATH" timeout 30 "$BIN" --definitely-not-an-option 2>&1); rc3=$?
[ "$rc3" = "124" ] && fail "unknown option hung for 30s"
[ "$rc3" != "0" ] || echo "NOTE: unknown option exited 0"
echo "PASS 3: unknown option rc=$rc3 out=[$out3]"
passed=$((passed + 1))

unset DISPLAY 2>/dev/null || true
t0=$(date +%s)
out4=$(PATH="$LIBDIR:$PATH" timeout 30 "$BIN" -query 2>&1); rc4=$?
t1=$(date +%s); el=$((t1 - t0))
[ "$rc4" = "124" ] && fail "-query hung for 30s without DISPLAY"
echo "PASS 4: -query without DISPLAY terminated rc=$rc4 elapsed=${el}s out=[$out4]"
passed=$((passed + 1))

READELF=$(command -v readelf || command -v llvm-readelf || true)
if [ -n "$READELF" ]; then
  needs=$("$READELF" -d "$BIN" 2>/dev/null | grep NEEDED | sed -e 's/.*\[\(.*\)\]/\1/' | tr "\n" " ")
  echo "NEEDED: $needs"
  miss=""
  for want in libX11 libXdmcp libXau libxcb; do
    case " $needs " in *" ${want}.so"*) : ;; *) miss="$miss $want" ;; esac
  done
  [ -n "$miss" ] && fail "ELF NEEDED lacks$miss"
  echo "PASS 5: dependency closure complete -> $needs"
  passed=$((passed + 1))
else
  echo "SKIP 5: no readelf on this runner"
  skipped=$((skipped + 1))
fi

echo "xcmsdb 1.0.7 test_package: declared=5 passed=$passed skipped=$skipped failed=0"
exit 0
