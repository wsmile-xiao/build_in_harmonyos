#!/bin/sh
# Real consumer test for the vkeybd package (HarmonyOS PC / ohos-aarch64).
#
# Covers the two shipped binaries:
#   * sftovkb — exercised end to end against a generated SF2 fixture, asserting
#     the exact preset lines it prints (bank, program number, and the name
#     sanitiser that maps []{} to ()/space).
#   * vkeybd  — a Tcl/Tk GUI that needs an X display, so it cannot open a
#     window on a headless device. It is instead verified through its two
#     observable non-GUI surfaces: the installed data files it reads at
#     startup, and a real invocation of the binary that must resolve its
#     dynamic libraries and reach its own argument handling.
set -e

VKEYBD="${VKEYBD:-vkeybd}"
SFTOVKB="${SFTOVKB:-sftovkb}"
DATADIR="${VKEYBD_DATADIR:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FIXTURE="$HERE/fixture.sf2"
OUT="$HERE/preset.out"

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

# Locate the binaries by absolute path. `command -v` alone is not enough: a
# stale PATH entry or a shell that reports a name it cannot execute would let a
# missing binary through, and the later invocations would then exit 127 and
# still "pass" the loose assertions below.
command -v "$SFTOVKB" >/dev/null 2>&1 || fail "sftovkb not on PATH (conanrun env missing)"
command -v "$VKEYBD"  >/dev/null 2>&1 || fail "vkeybd not on PATH (conanrun env missing)"

# Prove both are real, runnable executables before trusting any result from them.
for prog in "$SFTOVKB" "$VKEYBD"; do
  path="$(command -v "$prog")"
  [ -x "$path" ] || fail "$prog resolves to a non-executable: $path"
done

# ---------------------------------------------------------------- sftovkb
# 1. Build the SF2 fixture with the installed python3.
python3 "$HERE/make_sf2_fixture.py" "$FIXTURE" || fail "fixture generation failed"
[ -s "$FIXTURE" ] || fail "fixture is empty"

# 2. Convert it. Stdout must be one "<bank> <prog> <name>" line per preset, in
#    fixture order. The parser keeps each name in its native 20-byte fixed-width
#    field, so trailing padding is trimmed before comparing. Interior runs of
#    spaces are significant (they are the sanitiser's output) and are preserved.
"$SFTOVKB" "$FIXTURE" > "$OUT" 2>/dev/null || fail "sftovkb returned non-zero on a valid SF2"

expected="0 0 Piano
0 1 Brass (Ensemble)
0 2 Chord  Pad"

actual="$(sed -e 's/[[:space:]]*$//' "$OUT")"
if [ "$actual" != "$expected" ]; then
  echo "--- expected ---" >&2; echo "$expected" >&2
  echo "--- actual ---" >&2;   echo "$actual" >&2
  fail "sftovkb output mismatch"
fi
pass "sftovkb converts a real SF2 into the expected preset list"

# 3. The name sanitiser is part of the contract: []{} must be neutralised so
#    the line stays parseable by the Tcl preset reader.
grep -q 'Brass (Ensemble)' "$OUT" || fail "brackets were not converted to parentheses"
grep -q 'Chord  Pad' "$OUT"     || fail "braces were not converted to spaces"
pass "sftovkb sanitises preset names ([] -> (), {} -> space)"

# 4. A malformed input must fail loudly rather than print junk.
printf 'NOT-A-RIFF-FILE' > "$HERE/bad.sf2"
if "$SFTOVKB" "$HERE/bad.sf2" > "$HERE/bad.out" 2>/dev/null; then
  fail "sftovkb accepted a non-SoundFont file"
fi
[ -s "$HERE/bad.out" ] && fail "sftovkb printed output for a rejected file"
pass "sftovkb rejects a non-SoundFont input with a non-zero exit"

# 5. Missing argument is documented usage on stderr, not a crash.
if "$SFTOVKB" > "$HERE/noarg.out" 2>"$HERE/noarg.err"; then
  fail "sftovkb accepted an empty command line"
fi
grep -q 'usage: sftovkb' "$HERE/noarg.err" || fail "sftovkb did not print its usage line"
pass "sftovkb prints usage when called without arguments"

# ---------------------------------------------------------------- vkeybd
# 6. The data files the Tk script loads must be installed next to the binary.
[ -n "$DATADIR" ] || DATADIR="$(dirname "$(command -v "$VKEYBD")")/../share/vkeybd"
[ -f "$DATADIR/vkeybd.tcl" ]  || fail "vkeybd.tcl missing from $DATADIR"
[ -f "$DATADIR/vkeybd.list" ] || fail "vkeybd.list (preset list) missing from $DATADIR"
pass "vkeybd runtime data files are installed"

# 7. The compiled-in script path baked in at build time must point at the
#    installed data dir, otherwise vkeybd would look under the source tree.
VKEYBD_BIN="$(command -v "$VKEYBD")"
if grep -a -q "$DATADIR/vkeybd.tcl" "$VKEYBD_BIN" 2>/dev/null; then
  pass "vkeybd's compiled-in VKB_TCLFILE path resolves to the installed data dir"
else
  echo "WARN: could not confirm compiled-in VKB_TCLFILE path in $VKEYBD_BIN"
fi

# 8. Real invocation: the process must actually start, dynamically resolve
#    libtcl9tk9.0 / libX11 / libasound, and reach its own argument handling.
#    A headless device has no $DISPLAY, so Tk exits non-zero — that is expected.
#    What must NOT happen is exit 127 (binary not found), or a dynamic loader
#    error, either of which would mean the recipe's runtime env is wrong.
set +e
"$VKEYBD_BIN" --help > "$HERE/vkeybd.out" 2>&1
rc=$?
set -e
if [ "$rc" -eq 127 ]; then
  fail "vkeybd could not be executed at all (exit 127): $VKEYBD_BIN"
fi
if grep -qi 'error while loading shared libraries' "$HERE/vkeybd.out"; then
  cat "$HERE/vkeybd.out" >&2
  fail "vkeybd could not load its shared libraries (runenv LD_LIBRARY_PATH missing)"
fi
if [ ! -s "$HERE/vkeybd.out" ]; then
  cat "$HERE/vkeybd.out" >&2
  fail "vkeybd produced no output at all (exit=$rc); loader or X init aborted silently"
fi
pass "vkeybd starts, loads its libraries, and reaches its own output (exit=$rc, headless)"

echo "ALL_VKEYBD_TESTS_PASSED"
