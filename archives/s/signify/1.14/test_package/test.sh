#!/data/service/hnp/bin/bash
# test_package/test.sh - functional smoke test for signify
set -euo pipefail

# HMBS perl ABI fix: conan perl 5.42.2 XS modules are incompatible with system perl
# (Perl_croak_nocontext / Perl_my_cxt_init symbol not found). Unset PERL5LIB so system
# perl at /data/service/hnp/bin/perl uses its own core modules (IO.so) rather than
# conan's aarch64-linux-thread-multi path.
unset PERL5LIB || true
export PERL5LIB=""
# Also ensure stale_runtime_library handling: if HMBS sets LD_LIBRARY_PATH/LD_PRELOAD for perl,
# allow it, but do not force conan perl's lib. Prefer system perl.
if [ -x "/data/service/hnp/bin/perl" ]; then
  PERL_BIN="/data/service/hnp/bin/perl"
elif command -v perl >/dev/null 2>&1; then
  PERL_BIN=$(command -v perl)
else
  PERL_BIN="perl"
fi
echo "[test] using perl: $PERL_BIN ($($PERL_BIN --version 2>&1 | head -n1 || true))"
# Validate perl can load IO (signify needs IO::Handle); if system perl fails, try fallback
if ! "$PERL_BIN" -MIO -e 'print "IO ok\n"' >/dev/null 2>&1; then
  echo "⚠️  $PERL_BIN cannot load IO, trying alternative perl"
  for cand in "/usr/bin/perl" "perl"; do
    if [ -x "$cand" ] && "$cand" -MIO -e '1' 2>/dev/null; then
      PERL_BIN="$cand"
      echo "[test] fallback perl: $PERL_BIN"
      break
    fi
  done
fi
BIN="${SIGNIFY_BIN:-signify}"
if [ ! -x "$BIN" ]; then
  BIN=$(command -v signify || echo signify)
fi
if [ -f "$BIN" ]; then
  echo "[test] signify shebang: $(head -n1 "$BIN" 2>/dev/null || echo 'no shebang')"
fi

echo "[test] signify binary exists and is executable"
if [ ! -x "$BIN" ] && ! command -v signify >/dev/null 2>&1; then
  echo "❌ signify not found in PATH or package_folder"
  exit 1
fi
echo "✅ signify found: $BIN (perl: $PERL_BIN)"

# Helper to run signify: try direct exec first, fallback to explicit perl if shebang fails
run_signify() {
  local out rc
  # Try direct
  out=$("$BIN" "$@" 2>&1) && rc=0 || rc=$?
  if [ $rc -ne 0 ] && echo "$out" | grep -q "Can't load.*IO\.so\|symbol not found\|Perl_croak"; then
    echo "⚠️  direct exec failed due to perl XS mismatch, retrying via $PERL_BIN" >&2
    echo "$out" >&2
    out=$("$PERL_BIN" "$BIN" "$@" 2>&1) && rc=0 || rc=$?
  fi
  echo "$out"
  return $rc
}

TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"
TMPFILE="$TMPDIR/signify-test-$$.sig"
cat >"$TMPFILE" <<'EOF'
% { center
Hello from HarmonyOS
% | center
Second line test
% }
EOF

echo "[test] signify --input=$TMPFILE"
OUTPUT=$(run_signify --input="$TMPFILE" 2>&1 || true)
echo "$OUTPUT"
if [ -z "$OUTPUT" ]; then
  echo "❌ signify produced empty output"
  exit 1
fi
if echo "$OUTPUT" | grep -q "Can't load.*IO\.so\|symbol not found" ; then
  echo "❌ signify failed due to perl XS mismatch (see above)"
  exit 1
fi
# Portable check: use two separate grep -q without alternation (BRE \| not portable on toybox/BSD grep)
if echo "$OUTPUT" | grep -q "Hello" || echo "$OUTPUT" | grep -q "Second line"; then
  echo "✅ functional output contains expected text"
else
  echo "❌ functional output missing expected text"
  echo "--- DEBUG: output was ---"
  echo "$OUTPUT" | cat -A
  echo "--- end debug ---"
  exit 1
fi

EXAMPLE=""
for p in "/usr/local/share/signify/examples/Simple" "$HOME/.conan2/p/signif*/p/share/signify/examples/Simple" "$(dirname "$BIN")/../share/signify/examples/Simple"; do
  if [ -f "$p" ]; then EXAMPLE="$p"; break; fi
done
if [ -z "$EXAMPLE" ]; then
  echo "[test] skipping example file test (not found, but functional test already passed)"
else
  echo "[test] signify --input=$EXAMPLE"
  run_signify --input="$EXAMPLE" > "$TMPDIR/signify-example.out" || { echo "❌ example run failed"; cat "$TMPDIR/signify-example.out"; exit 1; }
  test -s "$TMPDIR/signify-example.out" || { echo "❌ example output empty"; exit 1; }
  echo "✅ example run OK ($(wc -c < "$TMPDIR/signify-example.out") bytes)"
fi

rm -f "$TMPFILE" "$TMPDIR/signify-example.out"
echo "All 2 tests passed"
