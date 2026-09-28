#!/bin/sh
# laptop-detect 0.16-nmu1 consumer probe (25 assertions).
#
# Usage: sh test_laptop_detect.sh <bin_dir>
#
# Verifies the installed script's option semantics (exit-2 family), detection
# semantics (exit 0/1 with a consistent diagnostic), debug mode and the
# installation layout. The script is always invoked via `sh` — OHOS HMDFS
# forbids direct exec of shebang scripts (E046/E087), so the consumer contract
# on HarmonyOS PC is `sh laptop-detect ...`.

BIN="$1/laptop-detect"
PKG="$1/.."
TMPD="${TMPDIR:-/tmp}"
TMP="$TMPD/ldt_probe_$$"
PASS=0
FAIL=0
ERR1="$TMP/err1" ERRV="$TMP/errv" ERRD="$TMP/errd"

ok()  { PASS=$((PASS+1)); }
bad() { FAIL=$((FAIL+1)); echo "[FAIL] $1"; }

mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

# --- 安装布局与静态检查 -----------------------------------------------
[ -f "$BIN" ] && ok || bad "bin/laptop-detect present"
[ "$(sed -n '1p' "$BIN")" = "#!/bin/sh -e" ] && ok || bad "shebang #!/bin/sh -e"
grep -q '@VERSION@' "$BIN" && bad "no @VERSION@ residue" || ok
grep -q 'Version: 0.16-nmu1' "$BIN" && ok || bad "version string substituted"
[ -f "$PKG/share/man/man1/laptop-detect.1" ] && ok || bad "man page installed"
grep -q 'laptop\\-detect' "$PKG/share/man/man1/laptop-detect.1" \
    && ok || bad "man page content"
[ -f "$PKG/share/doc/laptop-detect/README" ] && ok || bad "README installed"
[ -f "$PKG/licenses/copyright" ] && ok || bad "license file installed"
grep -q 'Redistribution and use in source and binary forms' \
    "$PKG/licenses/copyright" && ok || bad "BSD-3-Clause full text"

# --- 选项语义（exit 2 族） ---------------------------------------------
out=$(sh "$BIN" -V 2>/dev/null); rc=$?
[ $rc -eq 2 ] && ok || bad "-V exits 2"
echo "$out" | grep -q '^Version: 0.16-nmu1$' && ok || bad "-V prints version"
out=$(sh "$BIN" -h 2>/dev/null); rc=$?
[ $rc -eq 2 ] && ok || bad "-h exits 2"
echo "$out" | grep -q 'Usage:' && ok || bad "-h prints usage"
echo "$out" | grep -q 'Possible return values' && ok || bad "-h documents return values"
out=$(sh "$BIN" --bogus 2>/dev/null); rc=$?
[ $rc -eq 2 ] && ok || bad "unknown option exits 2"
echo "$out" | grep -q 'UNKNOWN OPTION' && ok || bad "unknown option message"

# --- 判定语义（exit 0/1 + 一致诊断） ------------------------------------
sh "$BIN" >/dev/null 2>"$ERR1"; rc1=$?
{ [ $rc1 -eq 0 ] || [ $rc1 -eq 1 ]; } && ok || bad "plain run rc in {0,1}"
# 静默是设计语义：PRINTIT=/bin/true，诊断只在 -v 时输出。
[ ! -s "$ERR1" ] && ok || bad "plain run silent by design"
sh "$BIN" -v >/dev/null 2>"$ERRV"; rcv=$?
{ [ $rcv -eq 0 ] || [ $rcv -eq 1 ]; } && ok || bad "-v rc in {0,1}"
[ $rcv -eq $rc1 ] && ok || bad "-v rc matches plain run"
[ -s "$ERRV" ] && ok || bad "-v emits diagnostic"
case $rcv in
    0) grep -qi -e laptop -e portable -e notebook -e 'hand held' "$ERRV" \
           && ok || bad "-v rc=0 diagnostic names laptop class";;
    1) grep -qi 'no relevant hint' "$ERRV" && ok || bad "-v rc=1 diagnostic";;
esac

# --- 调试模式 -----------------------------------------------------------
sh "$BIN" -D >/dev/null 2>"$ERRD"; rcd=$?
[ $rcd -eq 0 ] && ok || bad "-D exits 0 (EXIT=/bin/true)"
grep -q '^+' "$ERRD" && ok || bad "-D emits xtrace lines"

# --- 确定性 -------------------------------------------------------------
sh "$BIN" >/dev/null 2>/dev/null; rc2=$?
[ $rc2 -eq $rc1 ] && ok || bad "deterministic across runs"

echo "laptop-detect probe: $PASS passed, $FAIL failed (rc1=$rc1)"
[ $FAIL -eq 0 ]
