#!/bin/sh
# fdk-aac 2.0.3.2 consumer E2E 测试入口
# 用法: test.sh <BIN_DIR> <SRC_DIR>
#   BIN_DIR = test_package 构建输出目录(probe 与 test-encode-decode 所在)
#   SRC_DIR = test_package 源目录(upstream-test/ 与 ref-*.txt 所在)
#
# 三个阶段:
#   1. 消费者探针 fdk_aac_probe(18 项结构断言 + 聚合 SHA-1,永远执行)
#   2. 上游官方测试套件(官方 run-test.sh 语义,官方 wav fixture 存在时执行)
#   3. 合成 wav 烟测(无官方 fixture 时兜底,验证官方工具可运行、哈希行形状正确)
set -u

BIN_DIR="$1"
SRC_DIR="$2"
if [ -z "$BIN_DIR" ]; then BIN_DIR="."; fi
if [ -z "$SRC_DIR" ]; then SRC_DIR="."; fi

fail=0

echo "== phase 1: consumer probe (structural E2E) =="
"$BIN_DIR/fdk_aac_probe"
rc=$?
if [ $rc -ne 0 ]; then
    echo "probe FAILED rc=$rc"
    exit $rc
fi

echo "== phase 2: upstream official test suite (run-test.sh semantics) =="
if [ -f "$BIN_DIR/Sample01_4.wav" ] && [ -f "$BIN_DIR/Sample01_4-mono.wav" ]; then
    if command -v md5sum >/dev/null 2>&1; then
        got=$(md5sum "$BIN_DIR/Sample01_4.wav" | awk '{print $1}')
        if [ "$got" != "a5c105544c64ce92c6c5c06d280e6b9c" ]; then
            echo "FAIL: Sample01_4.wav md5 mismatch ($got)"
            fail=1
        fi
        got=$(md5sum "$BIN_DIR/Sample01_4-mono.wav" | awk '{print $1}')
        if [ "$got" != "3bfccac9f2e527ba3ef888874f09a409" ]; then
            echo "FAIL: Sample01_4-mono.wav md5 mismatch ($got)"
            fail=1
        fi
    else
        echo "WARN: md5sum unavailable, skipping fixture checksum"
    fi
    if [ $fail -eq 0 ]; then
        cd "$BIN_DIR" || exit 1
        ./test-encode-decode Sample01_4.wav > log-stereo.txt 2>err-stereo.txt
        rc1=$?
        ./test-encode-decode Sample01_4-mono.wav > log-mono.txt 2>err-mono.txt
        rc2=$?
        echo "stereo exit=$rc1, mono exit=$rc2"
        echo "--- err-stereo ---"; cat err-stereo.txt
        echo "--- err-mono ---"; cat err-mono.txt
        if [ $rc1 -ne 0 ] || [ $rc2 -ne 0 ]; then
            echo "FAIL: test-encode-decode nonzero exit"
            fail=1
        fi
        # Windows/MinGW printf 输出 CRLF,归一化为 LF 后与官方 ref 位元比对
        tr -d '\r' < log-stereo.txt > log-stereo.lf.txt && mv log-stereo.lf.txt log-stereo.txt
        tr -d '\r' < log-mono.txt > log-mono.lf.txt && mv log-mono.lf.txt log-mono.txt
        # 官方 ref 生成于 x86:FDK 在 ARM64 使用 16-bit 系数表 + 32x16 定点
        # 乘法(FDK_archdef.h 的 ARCH_PREFER_MULT_32x16 等),码流跨架构设计上
        # 非位元一致。x86 必须与 ref 位元一致;其他架构以上游工具自身质量
        # 门禁(退出码=0 且各模式 avg_diff 阈值内)为准 + 哈希行形状校验。
        if ! diff -u log-stereo.txt "$SRC_DIR/upstream-test/ref-stereo.txt"; then
            if [ "$(uname -m 2>/dev/null)" = "x86_64" ] || [ "$(uname -m 2>/dev/null)" = "i686" ] || [ "$(uname -m 2>/dev/null)" = "i386" ]; then
                echo "FAIL: stereo hash diff vs official ref (x86 须位元一致)"
                fail=1
            else
                echo "NOTE: $(uname -m) 哈希与 x86 官方 ref 不同(上游定点表位宽平台差异),以上游工具质量门禁为准"
                if ! grep -q '^encode hash: [0-9a-f]\{40\}$' log-stereo.txt || ! grep -q '^decode hash: [0-9a-f]\{40\}$' log-stereo.txt; then
                    echo "FAIL: stereo hash line shape"
                    fail=1
                fi
            fi
        fi
        if ! diff -u log-mono.txt "$SRC_DIR/upstream-test/ref-mono.txt"; then
            if [ "$(uname -m 2>/dev/null)" = "x86_64" ] || [ "$(uname -m 2>/dev/null)" = "i686" ] || [ "$(uname -m 2>/dev/null)" = "i386" ]; then
                echo "FAIL: mono hash diff vs official ref (x86 须位元一致)"
                fail=1
            else
                echo "NOTE: $(uname -m) 哈希与 x86 官方 ref 不同(上游定点表位宽平台差异),以上游工具质量门禁为准"
                if ! grep -q '^encode hash: [0-9a-f]\{40\}$' log-mono.txt || ! grep -q '^decode hash: [0-9a-f]\{40\}$' log-mono.txt; then
                    echo "FAIL: mono hash line shape"
                    fail=1
                fi
            fi
        fi
    fi
else
    echo "SKIP: official wav fixtures absent (device/CI 验证时置入 BIN_DIR)"
fi

echo "== phase 3: synthetic wav smoke of official tool =="
if [ $fail -eq 0 ] && command -v python3 >/dev/null 2>&1; then
    cd "$BIN_DIR" || exit 1
    python3 "$SRC_DIR/gen_fixture.py" probe-input.wav
    ./test-encode-decode probe-input.wav > log-probe.txt 2>err-probe.txt
    rc=$?
    tr -d '\r' < log-probe.txt > log-probe.lf.txt && mv log-probe.lf.txt log-probe.txt
    echo "synthetic exit=$rc"
    cat err-probe.txt
    if [ $rc -ne 0 ]; then
        echo "FAIL: synthetic wav encode/decode nonzero exit"
        fail=1
    elif [ "$(grep -c '^encode hash: [0-9a-f]\{40\}$' log-probe.txt)" != "1" ] \
      || [ "$(grep -c '^decode hash: [0-9a-f]\{40\}$' log-probe.txt)" != "1" ]; then
        echo "FAIL: hash line shape mismatch"
        cat log-probe.txt
        fail=1
    else
        cat log-probe.txt
    fi
else
    echo "SKIP: python3 unavailable or phase 2 failed"
fi

if [ $fail -ne 0 ]; then
    echo "TEST FAILED"
    exit 1
fi
echo "ALL OK"
exit 0
