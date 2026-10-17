#!/bin/bash
# 消费者测试 — xar 1.8.0.498
# 用法: test_xar.sh <包内 bin 目录绝对路径>
# 6 项断言，全部离线，真实执行被适配工具（R34）。
# 覆盖 xar 核心能力：归档创建/列表/解出/逐字节一致性（含 gzip 压缩
# 堆与 XML TOC），校验和走默认 SHA1（libxar 内 openssl EVP 路径）。
set -u
BIN="$1"
XAR="$BIN/xar"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS+1)); echo "ok $PASS - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

mkdir "$TMP/data"
printf 'hello xar consumer test\n' > "$TMP/data/hello.txt"
python3 - "$TMP/data/payload.bin" <<'PYEOF' 2>/dev/null || printf 'fallback-payload-0123456789' > "$TMP/data/payload.bin"
import sys
with open(sys.argv[1], "wb") as f:
    f.write(bytes(range(256)) * 4)
PYEOF

# 1. --version（源码内部版本串为 1.8dev，任务口径 1.8.0.498 = xar-498 tag）
OUT="$("$XAR" --version 2>&1 | head -1)"
if [ "$OUT" = "xar 1.8dev" ]; then ok "xar --version"; else bad "xar --version: got [$OUT]"; fi

# 2. 创建归档（-c，默认 zlib 堆压缩 + SHA1 校验和）。
#    上游 -C 仅 extract 路径生效（help 原文 "On extract, chdir to this
#    location"，xar.c 仅 extract 分支有 chdir）→ create 用 subshell cd。
(cd "$TMP/data" && "$XAR" -cf "$TMP/t.xar" hello.txt payload.bin) 2>"$TMP/err2.txt"
RC=$?
if [ $RC -eq 0 ] && [ -s "$TMP/t.xar" ] && [ ! -s "$TMP/err2.txt" ]; then
  ok "xar -cf 创建归档"
else
  bad "xar -cf: rc=$RC, err=$(head -2 "$TMP/err2.txt")"
fi

# 3. 列表（-t）包含全部成员
LIST="$("$XAR" -tf "$TMP/t.xar" 2>&1)"
if printf '%s\n' "$LIST" | grep -q "hello.txt" && printf '%s\n' "$LIST" | grep -q "payload.bin"; then
  ok "xar -tf 成员列表"
else
  bad "xar -tf: got [$LIST]"
fi

# 4. 解出（-x）逐字节一致
mkdir "$TMP/out"
"$XAR" -xf "$TMP/t.xar" -C "$TMP/out" 2>"$TMP/err4.txt"
RC=$?
if [ $RC -eq 0 ] && cmp -s "$TMP/data/hello.txt" "$TMP/out/hello.txt" \
   && cmp -s "$TMP/data/payload.bin" "$TMP/out/payload.bin"; then
  ok "xar -xf 解出内容一致"
else
  bad "xar -xf: rc=$RC, err=$(head -2 "$TMP/err4.txt")"
fi

# 5. gzip 压缩堆 roundtrip（--compression=gzip；create 同 #2 用 subshell
#    cd，extract 的 -C 为上游合法语义）
(cd "$TMP/data" && "$XAR" --compression=gzip -cf "$TMP/z.xar" hello.txt payload.bin) 2>"$TMP/err5.txt" \
  && "$XAR" -xf "$TMP/z.xar" -C "$TMP/out" 2>>"$TMP/err5.txt" \
  && cmp -s "$TMP/data/payload.bin" "$TMP/out/payload.bin"
RC=$?
if [ $RC -eq 0 ]; then
  ok "gzip 压缩 roundtrip"
else
  bad "gzip roundtrip: rc=$RC, err=$(head -2 "$TMP/err5.txt")"
fi

# 6. XML TOC 转储（--dump-toc：真实 libxml2 写路径）
"$XAR" -f "$TMP/t.xar" --dump-toc="$TMP/toc.xml" 2>"$TMP/err6.txt"
RC=$?
if [ $RC -eq 0 ] && grep -q "hello.txt" "$TMP/toc.xml" \
   && grep -qi "sha1" "$TMP/toc.xml"; then
  ok "--dump-toc XML TOC"
else
  bad "--dump-toc: rc=$RC, head=$(head -2 "$TMP/toc.xml" 2>/dev/null)"
fi

echo "----------------------------------------"
echo "总结: 通过 $PASS / $((PASS+FAIL)), 失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
