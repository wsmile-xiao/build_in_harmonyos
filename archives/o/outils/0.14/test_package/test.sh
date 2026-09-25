#!/usr/bin/env bash
# test_package/test.sh — outils 0.14 消费者回归测试
# 实际执行被测包安装的全部 17 个命令（13 个二进制 + 4 个 md5 别名）。
set -u

TMPDIR="${TMPDIR:-$HOME/tmp}"
W="$TMPDIR/outils-test-$$"
rm -rf "$W"
mkdir -p "$W"

PASS=0
FAIL=0
ok()  { echo "  PASS: $1"; PASS=$((PASS + 1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL + 1)); }
chk() { if [ "$1" -eq 0 ]; then ok "$2"; else bad "$2"; fi; }

echo "[1] checksum tools"
printf abc | md5 > "$W/md5.txt" 2>&1
grep -q "900150983cd24fb0d6963f7d28e17f72" "$W/md5.txt"; chk $? "md5 stdin"
printf abc | md5 -q > "$W/md5q.txt" 2>&1
[ "$(cat "$W/md5q.txt")" = "900150983cd24fb0d6963f7d28e17f72" ]; chk $? "md5 -q stdin"
printf abc | sha1 -q > "$W/sha1.txt" 2>&1
[ "$(cat "$W/sha1.txt")" = "a9993e364706816aba3e25717850c26c9cd0d89d" ]; chk $? "sha1 -q stdin"
printf abc | sha256 -q > "$W/sha256.txt" 2>&1
[ "$(cat "$W/sha256.txt")" = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" ]; chk $? "sha256 -q stdin"
printf abc | sha512 -q > "$W/sha512.txt" 2>&1
[ "$(cat "$W/sha512.txt")" = "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f" ]; chk $? "sha512 -q stdin"
printf abc > "$W/abc.txt"
cksum "$W/abc.txt" > "$W/cksum.txt" 2>&1
grep -q "^1219131554 3 " "$W/cksum.txt"; chk $? "cksum file (CRC32 + size)"
md5 "$W/abc.txt" > "$W/md5file.txt" 2>&1
grep -q "MD5 (.*abc.txt) = 900150983cd24fb0d6963f7d28e17f72" "$W/md5file.txt"; chk $? "md5 file mode"

echo "[2] text tools"
[ "$(jot 3 | tr '\n' ' ')" = "1 2 3 " ]; chk $? "jot 3"
printf 'a\nb\n' | lam - > "$W/lam.txt" 2>&1
[ "$(cat "$W/lam.txt")" = "$(printf 'a\nb')" ]; chk $? "lam -"
printf 'a b c\nd e f\n' | rs -c > "$W/rs.txt" 2>&1
grep -q "a b c" "$W/rs.txt"; chk $? "rs -c"
printf 'hello\n' | ts > "$W/ts.txt" 2>&1
grep -q "hello" "$W/ts.txt"; chk $? "ts timestamp"
printf 'a\001b\377c\n' > "$W/vis-in"
vis "$W/vis-in" > "$W/vis-out" 2>/dev/null
unvis "$W/vis-out" > "$W/vis-back" 2>/dev/null
cmp -s "$W/vis-in" "$W/vis-back"; chk $? "vis|unvis roundtrip"
printf 'text\n@(#)outils consumer test\n' > "$W/what-in"
what "$W/what-in" > "$W/what-out" 2>&1
grep -q "outils consumer test" "$W/what-out"; chk $? "what"
apply echo a b c > "$W/apply-out" 2>&1
grep -q "^a$" "$W/apply-out" && grep -q "^c$" "$W/apply-out"; chk $? "apply"
mkdir -p "$W/ld-src" "$W/ld-dst"
echo hi > "$W/ld-src/f1"
lndir "$W/ld-src" "$W/ld-dst" > /dev/null 2>&1
[ -e "$W/ld-dst/f1" ]; chk $? "lndir shadow dir"

echo "[3] signify"
( cd "$W" && signify -G -n -p k.pub -s k.sec && \
  printf message > msg && \
  signify -S -s k.sec -m msg -x k.sig && \
  signify -V -p k.pub -m msg -x k.sig ) > "$W/sig.txt" 2>&1
grep -q "Signature Verified" "$W/sig.txt"; chk $? "signify keygen/sign/verify"

echo "[4] calendar"
printf '01/01\tDirect Event\n' > "$W/cal-direct"
calendar -f "$W/cal-direct" -t 20260101 > "$W/cal1.txt" 2>&1
grep -q "Direct Event" "$W/cal1.txt"; chk $? "calendar -f direct"
printf '01/01\tIncluded Event\n' > "$W/cal-include"
printf '#include <cal-include>\n' > "$W/cal-main"
( cd "$W" && calendar -f cal-main -t 20260101 ) > "$W/cal2.txt" 2>&1
grep -q "Included Event" "$W/cal2.txt"; chk $? "calendar built-in #include expansion"
PKG_BIN="$(command -v calendar)"
PKG_PREFIX="$(dirname "$(dirname "$PKG_BIN")")"
CALENDAR_DIR="$PKG_PREFIX/share/calendar" calendar -f calendar.usholiday -t 20260704 > "$W/cal3.txt" 2>&1
grep -q "Independence Day" "$W/cal3.txt"; chk $? "calendar shipped data (usholiday)"

echo "[5] rdate"
rdate > "$W/rdate.txt" 2>&1
grep -q "usage" "$W/rdate.txt"; chk $? "rdate usage"

echo "==== outils test_package: PASS=$PASS FAIL=$FAIL ===="
if [ "$FAIL" -ne 0 ]; then exit 1; fi
exit 0
