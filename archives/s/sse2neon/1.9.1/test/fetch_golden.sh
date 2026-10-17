#!/bin/sh
# fetch_golden.sh — sse2neon 1.9.1 differential golden 测试资产获取脚本（R06 制品端点交付）
#
# golden 二进制数据（132 个 .golden 文件）不随 PR 提交（CI diff 无法应用大量二进制补丁），
# 改由分析端制品端点按需下载 + SHA-256 核验后使用。本脚本提供可复现入口。
#
# 用法: sh fetch_golden.sh [目标目录]
#   默认目标目录: 本文件所在目录/golden
#   下载制品:  sse2neon-1.9.1-golden-x86.tar.gz (132 个 .golden, x86 SSE 生成, PRNG seed=123456)
#   制品 SHA-256: 0a055220636fa0d611c51577e169dfc4b7f24578e2011388be5aad37d82c758e
#   逐文件清单整体 SHA-256: cdd8d4e8db1271a5950d2b805d72d68a69fa21e705e357906706eaf4d721f5b1
#   下载后必须 sha256sum 与上值一致再解包；随后:
#     cd <上游源码根> && make check-differential GOLDEN_DIR=<目标目录> （建议 -ffp-contract=off 编译测试目标）

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET_DIR="${1:-$SCRIPT_DIR/golden}"
ARTIFACT_URL="http://192.168.31.248:8080/artifacts/sse2neon/sse2neon-1.9.1-golden-x86.tar.gz"
MANIFEST_URL="http://192.168.31.248:8080/artifacts/sse2neon/golden.sha256"
EXPECTED_SHA256="0a055220636fa0d611c51577e169dfc4b7f24578e2011388be5aad37d82c758e"
EXPECTED_MANIFEST_SHA256="cdd8d4e8db1271a5950d2b805d72d68a69fa21e705e357906706eaf4d721f5b1"

echo "[fetch_golden] target dir: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

TMP_ART="$TARGET_DIR/sse2neon-1.9.1-golden-x86.tar.gz"
TMP_MAN="$TARGET_DIR/golden.sha256"

curl -fsS --connect-timeout 5 --max-time 30 -o "$TMP_ART" "$ARTIFACT_URL"
curl -fsS --connect-timeout 5 --max-time 30 -o "$TMP_MAN" "$MANIFEST_URL"

ACTUAL_ART=$(sha256sum "$TMP_ART" | awk '{print $1}')
ACTUAL_MAN=$(sha256sum "$TMP_MAN" | awk '{print $1}')
echo "[fetch_golden] artifact sha256: $ACTUAL_ART"
echo "[fetch_golden] manifest  sha256: $ACTUAL_MAN"

if [ "$ACTUAL_ART" != "$EXPECTED_SHA256" ]; then
    echo "[fetch_golden] ERROR: artifact SHA-256 mismatch (expect $EXPECTED_SHA256)" >&2
    exit 1
fi
if [ "$ACTUAL_MAN" != "$EXPECTED_MANIFEST_SHA256" ]; then
    echo "[fetch_golden] ERROR: manifest SHA-256 mismatch (expect $EXPECTED_MANIFEST_SHA256)" >&2
    exit 1
fi

tar xzf "$TMP_ART" -C "$TARGET_DIR" --strip-components=1
rm -f "$TMP_ART" "$TMP_MAN"

COUNT=$(find "$TARGET_DIR" -maxdepth 1 -name '*.golden' | wc -l)
echo "[fetch_golden] extracted $COUNT .golden files into $TARGET_DIR"
if [ "$COUNT" -ne 132 ]; then
    echo "[fetch_golden] ERROR: expected 132 .golden files, got $COUNT" >&2
    exit 1
fi
echo "[fetch_golden] OK — 132 .golden files ready (per-file checksum verify: cd $TARGET_DIR && sha256sum -c golden.sha256)"
