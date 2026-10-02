#!/usr/bin/env bash
# test_package/test.sh — smoke + consumer round-trip for upx-ucl 4.2.4
# Runs in conanrun env (PATH includes installed bin/); invoked via
# CONFIG_SHELL injected by test_package conanfile (shebang itself unused).
set -euo pipefail

echo "[test] upx --version"
v="$(upx --version)"
echo "$v" | head -1
case "$v" in
  *upx\ 4.2.4*) echo "OK version string reports upx 4.2.4" ;;
  *) echo "FAIL unexpected version output"; exit 1 ;;
esac

echo "[test] pack/unpack round-trip on a copy of the upx binary"
td="$(mktemp -d)"
# HMDFS: mktemp -d 建立 0700 目录，去掉 group 写位后对本用户不可写
# （termrec/0.19 的 HMDFS mktemp 目录 mode 问题同源；此处用 chmod 770
# 恢复 group 写位）
chmod 770 "$td"
[ -w "$td" ] || { echo "FAIL temp dir not writable after chmod"; exit 1; }
trap 'rm -rf "$td"' EXIT
cp "$(command -v upx)" "$td/upx-copy"
# 1) pack a copy at compression level -3 (nrv2d is the default method
#    mapping; -3 is a level, not a method)
upx -3 -o "$td/upx-packed" "$td/upx-copy"
# 2) upstream integrity test on the packed image
upx -t "$td/upx-packed"
# 3) unpack and require byte-identical restore (upx-compare precedent)
upx -d -o "$td/upx-unpacked" "$td/upx-packed"
cmp "$td/upx-copy" "$td/upx-unpacked"
echo "OK pack -> test -> unpack -> cmp round-trip succeeded"
# 4) packed image is smaller than the original
o="$(wc -c < "$td/upx-copy")"; p="$(wc -c < "$td/upx-packed")"
echo "original=$o packed=$p"
[ "$p" -lt "$o" ] || { echo "FAIL packed image not smaller"; exit 1; }
echo "OK packed image is smaller"
echo "ALL TESTS PASSED"
