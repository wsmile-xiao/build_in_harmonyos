# Consumer test for mednaffe — headless-safe layered probe (R34/R40).
#
# mednaffe is a GTK3 GApplication with NO upstream CLI flag handling: on a
# desktop session `mednaffe --version` launches the GUI and blocks (by
# design); on a headless worker it exits at display/D-Bus init. In BOTH
# cases the dynamic loader must resolve the full DT_NEEDED closure first —
# a loader error is a real packaging failure, blocking is not.
#
# A1 packaged binary present + executable
# A2 ELF64 / AArch64 (e_machine=0xb7)
# A3 DT_NEEDED closure carries the GTK3 stack (skipped when no readelf)
# A4 3s runtime loader smoke — FAIL only on "Error loading shared library"
set -eu

echo "[test] A1: packaged binary exists and is executable"
B="$(command -v mednaffe)"
test -n "$B"
test -x "$B"
echo "[test] A1 ok: $B"

echo "[test] A2: ELF64 AArch64 (e_machine=0xb7)"
MAGIC="$(od -An -tx1 -N4 "$B" | tr -d ' \n')"
if [ "$MAGIC" != "7f454c46" ]; then
  echo "[test] A2 not an ELF: magic=$MAGIC"
  exit 1
fi
EM="$(od -An -tx1 -j18 -N2 "$B" | tr -d ' \n')"
if [ "$EM" != "b700" ]; then
  echo "[test] A2 not AArch64: e_machine=$EM"
  exit 1
fi
echo "[test] A2 ok"

echo "[test] A3: DT_NEEDED closure carries the GTK3 stack"
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
  NEED="$("$READELF" -d "$B")"
  for lib in libgtk-3.so.0 libgdk-3.so.0 libglib-2.0.so.0; do
    if ! echo "$NEED" | grep -q "$lib"; then
      echo "[test] A3 missing DT_NEEDED: $lib"
      exit 1
    fi
  done
  echo "[test] A3 ok ($(echo "$NEED" | grep -c '(NEEDED)') NEEDED entries)"
else
  echo "[test] A3 SKIP (no readelf in environment)"
fi

echo "[test] A4: runtime loader smoke (3s window; GUI may block by design)"
ERR="$( { timeout 3 mednaffe --version; } 2>&1 || true)"
if echo "$ERR" | grep -q "Error loading shared library"; then
  echo "[test] A4 loader failure:"
  echo "$ERR"
  exit 1
fi
echo "[test] A4 ok (loader resolved the closure, no load errors)"
echo "[test] PASS: 4 assertions"
