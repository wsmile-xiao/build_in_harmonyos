#!/data/service/hnp/bin/bash
# test_package/test.sh — utalk 1.0.2 consumer tests (executed in `conanrun` env)
# $1 = installed `utalk` binary path.
#
# Cases:
#   T1 binary present and executable
#   T2 `utalk --help` prints the usage screen
#   T3 no-argument invocation prints the usage screen
#   T4 refuses to run without a controlling tty (drives termio/termcap init)
#   T5 [OHOS] ELF is AArch64 and ncurses is statically linked (R26), libc.so (musl) present
#   T6 [OHOS] ncurses screen initialises on a pty (banner + server wait => terminfo works)
set -u

bin="$1"
pass=0
fail=0
skip=0
ok()   { echo "  [PASS] $1"; pass=$((pass + 1)); }
bad()  { echo "  [FAIL] $1"; fail=$((fail + 1)); }
skipc(){ echo "  [SKIP] $1"; skip=$((skip + 1)); }

echo "== utalk consumer tests =="
echo "binary: $bin"

# T1 -------------------------------------------------------------------------
if [ -x "$bin" ]; then
  ok "T1 binary present and executable"
else
  bad "T1 binary missing or not executable: $bin"
  echo "UTALK_TEST_RESULT pass=$pass fail=$fail skip=$skip"
  exit 1
fi

# T2 -------------------------------------------------------------------------
help_out=$("$bin" --help 2>&1); rc=$?
if printf '%s' "$help_out" | grep -q "utalk \[options\]"; then
  ok "T2 --help prints usage (exit=$rc)"
else
  bad "T2 --help usage missing (exit=$rc): $help_out"
fi

# T3 -------------------------------------------------------------------------
noarg=$("$bin" 2>&1); rc=$?
if printf '%s' "$noarg" | grep -q "utalk \[options\]"; then
  ok "T3 no-argument prints usage (exit=$rc)"
else
  bad "T3 no-argument usage missing (exit=$rc)"
fi

# T4 -------------------------------------------------------------------------
notty=$("$bin" -s 0 </dev/null 2>&1); rc=$?
if printf '%s' "$notty" | grep -q "only run on a tty"; then
  ok "T4 refuses non-tty execution as expected (exit=$rc)"
else
  bad "T4 expected 'only run on a tty', got (exit=$rc): $notty"
fi

# T5 [OHOS] ------------------------------------------------------------------
READELF=$(command -v llvm-readelf 2>/dev/null || command -v readelf 2>/dev/null || echo /data/service/hnp/bin/llvm-readelf)
hdr=$("$READELF" -h "$bin" 2>/dev/null || true)
needed=$("$READELF" -d "$bin" 2>/dev/null | grep NEEDED || true)
if printf '%s' "$hdr" | grep -q "AArch64"; then
  ok "T5a [OHOS] ELF machine is AArch64"
else
  bad "T5a ELF is not AArch64"
fi
if printf '%s' "$needed" | grep -q "libncurses"; then
  bad "T5b ncurses is linked dynamically (R26 violation): $needed"
else
  ok "T5b [OHOS] ncurses statically linked (no libncurses NEEDED)"
fi
if printf '%s' "$needed" | grep -q "libc.so"; then
  ok "T5c [OHOS] dynamic dependency libc.so (OHOS musl libc)"
else
  bad "T5c unexpected dynamic dependencies: $needed"
fi

# T6 / T7 [OHOS] -------------------------------------------------------------
# The package bundles the ncurses terminfo database; locate it next to bin/.
pkgsroot="$(cd "$(dirname "$bin")/.." 2>/dev/null && pwd)"
term="${TERMINFO:-$pkgsroot/share/terminfo}"
[ -d "$term" ] || term="$pkgsroot/lib/terminfo"

# T7: bundled terminfo present (OHOS ships almost no terminfo)
if [ -e "$term/x/xterm-256color" ] || [ -e "$term/78/xterm-256color" ]; then
  ok "T7 [OHOS] bundled terminfo database present ($term)"
else
  bad "T7 bundled terminfo database missing ($term)"
fi

# T6: ncurses screen initialises on a pty
SCRIPT_BIN=$(command -v script 2>/dev/null || echo /data/service/hnp/bin/script)
TIMEOUT_BIN=$(command -v timeout 2>/dev/null || echo /usr/bin/timeout)
if [ -x "$SCRIPT_BIN" ] && [ -x "$TIMEOUT_BIN" ]; then
  tmpd="${TMPDIR:-${HOME:-$pkgsroot}/tmp}"
  mkdir -p "$tmpd" 2>/dev/null || tmpd="$pkgsroot"
  out="$tmpd/utalk_pty.$$"
  outlog="$tmpd/utalk_pty_console.$$"
  TERM=xterm-256color TERMINFO="$term" \
    "$TIMEOUT_BIN" 8 "$SCRIPT_BIN" -q -c "\"$bin\" -s 0" "$out" \
    </dev/null >"$outlog" 2>&1 || true
  if grep -q "utalk version 1.0.2" "$out" 2>/dev/null && \
     grep -q "waiting for connection" "$out" 2>/dev/null; then
    ok "T6 [OHOS] ncurses screen banner + server wait rendered (terminfo OK)"
  elif grep -qi "pty" "$outlog" 2>/dev/null; then
    # No pty can be allocated in this environment (sandbox/container limit);
    # this is a harness limitation, not a utalk defect -> skip, not fail.
    skipc "T6 pty screen test unavailable: $(head -1 "$outlog" 2>/dev/null)"
  else
    bad "T6 pty run did not render the utalk screen (out=$out)"
    echo "  --- pty capture (first 200 bytes) ---"
    head -c 200 "$out" 2>/dev/null | cat -v || true
    echo ""
    echo "  --- script console (first 200 bytes) ---"
    head -c 200 "$outlog" 2>/dev/null | cat -v || true
    echo ""
    echo "  -------------------------------------"
  fi
  rm -f "$out" "$outlog" 2>/dev/null || true
else
  skipc "T6 pty screen test ('script'/'timeout' not available)"
fi

echo "UTALK_TEST_RESULT pass=$pass fail=$fail skip=$skip"
[ "$fail" -eq 0 ] || exit 1
echo "utalk tool consumer tests PASSED"
