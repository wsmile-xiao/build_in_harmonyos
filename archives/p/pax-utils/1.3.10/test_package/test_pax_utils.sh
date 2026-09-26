#!/bin/sh
# Consumer test for pax-utils/1.3.10 — drives the *installed* tools from bin/.
# POSIX sh (device runs mksh, CI worker runs bash).  Every assertion spawns a
# real process, so the suite fails hard as soon as bin/ is removed (L1e/R34).
#
#   usage: sh test_pax_utils.sh <package bin dir> <package folder>
set -u

BINDIR="${1:-}"
PKG="${2:-}"
TOTAL=0
PASS=0
FAIL=0

ok()  { TOTAL=$((TOTAL + 1)); PASS=$((PASS + 1)); printf '[PASS] %s\n' "$1"; }
bad() { TOTAL=$((TOTAL + 1)); FAIL=$((FAIL + 1)); printf '[FAIL] %s\n' "$1"; }
eq()  { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1: want [$2] got [$3]"; fi; }
has() { case "$3" in *"$2"*) ok "$1" ;; *) bad "$1: [$2] absent from [$3]" ;; esac; }

if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/scanelf" ]; then
  printf '[FAIL] bin/scanelf is installed and executable (bin dir = [%s])\n' "$BINDIR"
  printf 'TOTAL=1 PASS=0 FAIL=1\n'
  exit 1
fi

SCANELF="$BINDIR/scanelf"
DUMPELF="$BINDIR/dumpelf"
PSPAX="$BINDIR/pspax"
SCANMACHO="$BINDIR/scanmacho"
# lddtree/symtree are shell scripts that call scanelf/nm by name.
PATH="$BINDIR:$PATH"
export PATH

# /tmp is read-only on HarmonyOS: keep scratch under the current directory.
WORK=$PWD/.paxutils-$$
mkdir -p "$WORK" 2>/dev/null || WORK=$HOME/.paxutils-$$
mkdir -p "$WORK" || { printf 'TOTAL=1 PASS=0 FAIL=1\n'; exit 1; }
cd "$WORK" || exit 1
cleanup() { cd .. 2>/dev/null || cd /; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

for tool in scanelf dumpelf pspax scanmacho; do
  if [ -x "$BINDIR/$tool" ]; then ok "bin/$tool installed and executable"; else
    bad "bin/$tool installed and executable"
  fi
done
for data in lddtree symtree; do
  if [ -f "$BINDIR/$data" ]; then ok "bin/$data installed"; else bad "bin/$data installed"; fi
done
if [ -n "$PKG" ] && [ -f "$PKG/licenses/COPYING" ]; then
  ok "GPL-2.0 license file packaged"
else
  bad "GPL-2.0 license file packaged"
fi

out=$("$SCANELF" -V 2>&1); rc=$?
eq 'scanelf -V exits 0' '0' "$rc"
has 'scanelf -V reports the upstream version' 'pax-utils-1.3.10' "$out"
out=$("$DUMPELF" -V 2>&1)
has 'dumpelf -V reports the upstream version' 'pax-utils-1.3.10' "$out"
out=$("$PSPAX" -V 2>&1)
has 'pspax -V reports the upstream version' 'pax-utils-1.3.10' "$out"

"$SCANELF" -h >help.out 2>&1; rc=$?
eq 'scanelf -h prints usage and exits 0' '0' "$rc"
has 'scanelf usage mentions ELF' 'ELF' "$(cat help.out)"

# Symbol lookup with the format string upstream's own scanelf test uses.
out=$("$SCANELF" -qsmain -F'%s %f' "$SCANELF" 2>&1); rc=$?
eq 'scanelf -qsmain exits 0' '0' "$rc"
eq 'scanelf resolves the main symbol of the installed binary' 'main scanelf' "$out"

"$SCANELF" -p "$SCANELF" >pax.out 2>&1; rc=$?
eq 'scanelf -p (PaX markings) runs on aarch64 ELF' '0' "$rc"

out=$("$SCANELF" -qsmain -F'%s %f' "$WORK/definitely-not-here" 2>&1)
case "$out" in
  *"main "*) bad 'negative control: missing file must not yield a symbol match' ;;
  *) ok 'negative control: missing file must not yield a symbol match' ;;
esac

# dumpelf decodes the ELF header: e_machine must be 183 (EM_AARCH64).
out=$("$DUMPELF" "$SCANELF" 2>&1); rc=$?
eq 'dumpelf parses the installed scanelf' '0' "$rc"
has 'dumpelf prints the ELF header' '.e_machine' "$out"
has 'dumpelf reports EM_AARCH64 (183) not x86' '183' "$out"

# Both tools exit 0 even on unreadable input (their main() returns EXIT_SUCCESS
# unconditionally), so the negative controls compare output, not exit codes.
printf 'not an elf at all\n' > plain.txt
bad_out=$("$DUMPELF" plain.txt 2>&1)
case "$bad_out" in
  *".e_machine"*) bad 'negative control: non-ELF input must not decode an ELF header' ;;
  *) ok 'negative control: non-ELF input must not decode an ELF header' ;;
esac

# pspax reads /proc — a real HarmonyOS procfs capability check.
out=$("$PSPAX" 2>&1); rc=$?
eq 'pspax runs and exits 0' '0' "$rc"
has 'pspax prints a PID header (procfs readable)' 'PID' "$out"

# lddtree resolves the dynamic dependencies of the installed binary.  Invoked
# through its shebang the way a user would; the packaged implementation is the
# shell one (see conanfile.py), which drives scanelf.
out=$("$BINDIR/lddtree" "$SCANELF" 2>&1); rc=$?
eq 'lddtree runs as an installed executable' '0' "$rc"
has 'lddtree resolves the OHOS musl libc dependency' 'libc.so' "$out"

"$SCANELF" -R -qsmain -F'%s %f' "$BINDIR" >recursive.out 2>&1
if grep -q 'main ' recursive.out; then ok 'scanelf -R walks bin/ and matches symbols'; else
  bad 'scanelf -R walks bin/ and matches symbols'
fi
if grep -q 'main dumpelf' recursive.out && grep -q 'main pspax' recursive.out; then
  ok 'recursive results name each tool separately (format reflects the file)'
else
  bad 'recursive results name each tool separately (format reflects the file)'
fi

printf 'TOTAL=%s PASS=%s FAIL=%s\n' "$TOTAL" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
