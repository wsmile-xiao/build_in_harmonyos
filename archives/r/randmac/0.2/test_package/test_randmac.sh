#!/bin/sh
# randmac 0.2 消费者测试（真机运行）。
# R34：以使用者身份真实运行被测二进制并断言行为——MAC 格式、OUI 覆盖、
# strcase 依赖的大小写无关分支（-o qemu/-o QEMU/-o xen）、EUI-64 输出、
# 本地/组播/单播位与 --help 退出码。$1 = 被测包 bin 目录。

BIN="$1/randmac"
fails=0
n=0

ok() { n=$((n+1)); echo "PASS: $1"; }
bad() { n=$((n+1)); echo "FAIL: $1"; fails=$((fails+1)); }

MAC_RE='^([0-9a-f]{2}:){5}[0-9a-f]{2}$'

# 1. 默认输出为合法 MAC
out=$("$BIN" 2>/dev/null) && echo "$out" | grep -Eq "$MAC_RE" \
    && ok "default prints valid MAC ($out)" || bad "default prints valid MAC"

# 2. -q：qemu OUI 52:54:00
out=$("$BIN" -q 2>/dev/null) && echo "$out" | grep -Eq '^52:54:00(:[0-9a-f]{2}){3}$' \
    && ok "-q uses qemu OUI" || bad "-q uses qemu OUI"

# 3. -xU：xen OUI + 大写十六进制
out=$("$BIN" -xU 2>/dev/null) && echo "$out" | grep -Eq '^00:16:3E(:[0-9A-F]{2}){3}$' \
    && ok "-xU uses xen OUI uppercase" || bad "-xU uses xen OUI uppercase"

# 4. -l：本地管理位（首字节 & 0x02）
out=$("$BIN" -l 2>/dev/null); first=${out%%:*}
case "$first" in
    *2|*3|*6|*7|*a|*b|*e|*f) ok "-l sets local bit" ;;
    *) bad "-l sets local bit" ;;
esac

# 5. -m：组播位（首字节 & 0x01）
out=$("$BIN" -m 2>/dev/null); first=${out%%:*}
case "$first" in
    *1|*3|*5|*7|*9|*b|*d|*f) ok "-m sets multicast bit" ;;
    *) bad "-m sets multicast bit" ;;
esac

# 6. -u：单播（首字节 & 0x01 == 0）
out=$("$BIN" -u 2>/dev/null); first=${out%%:*}
case "$first" in
    *0|*2|*4|*6|*8|*a|*c|*e) ok "-u keeps unicast" ;;
    *) bad "-u keeps unicast" ;;
esac

# 7. -e：EUI-64（8 组，含 ff:fe 中缀）
out=$("$BIN" -e 2>/dev/null)
echo "$out" | grep -Eq '^([0-9a-f]{2}:){7}[0-9a-f]{2}$' && echo "$out" | grep -q ':ff:fe:' \
    && ok "-e emits EUI-64" || bad "-e emits EUI-64"

# 8. -h：帮助文本且退出码 0
"$BIN" -h >/dev/null 2>&1 && "$BIN" -h 2>/dev/null | grep -q 'Usage' \
    && ok "-h prints usage" || bad "-h prints usage"

# 9. -o 十六进制串：覆盖 OUI
"$BIN" -o 001122 2>/dev/null | grep -Eq '^00:11:22:' \
    && ok "-o hex sets OUI" || bad "-o hex sets OUI"

# 10. -o 冒号形式
"$BIN" -o 00:11:22 2>/dev/null | grep -Eq '^00:11:22:' \
    && ok "-o colon form sets OUI" || bad "-o colon form sets OUI"

# 11. -o qemu：strcase 小写分支命中 52:54:00（真实依赖路径）
"$BIN" -o qemu 2>/dev/null | grep -Eq '^52:54:00:' \
    && ok "-o qemu resolves via strcase" || bad "-o qemu resolves via strcase"

# 12. -o QEMU：上游使用 strcase()（大小写敏感版，strcase_tolower 才忽略
#     大小写），大写不入 qemu/xen 分支，落到 hex 解析报错退出（非 0）
if "$BIN" -o QEMU >/dev/null 2>&1; then
    bad "-o QEMU rejected by case-sensitive strcase"
else
    ok "-o QEMU rejected by case-sensitive strcase"
fi

# 13. -o xen：第二个 strcase 分支
"$BIN" -o xen 2>/dev/null | grep -Eq '^00:16:3e:' \
    && ok "-o xen resolves via strcase" || bad "-o xen resolves via strcase"

echo "checks=$n failures=$fails"
[ "$fails" -eq 0 ]
