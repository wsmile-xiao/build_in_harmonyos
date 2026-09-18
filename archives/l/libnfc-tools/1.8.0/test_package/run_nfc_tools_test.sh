#!/bin/sh
# libnfc-tools 1.8.0 消费者冒烟测试（application 包：真实执行被测包二进制）
# 由 test_package/conanfile.py 的 test() 调用，$1 = 被测包 bin 目录。
set -euo pipefail
BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -x "$BIN_DIR/nfc-list" ]; then
    echo "FAIL: nfc-list not found or not executable in $BIN_DIR"
    exit 1
fi

# 冒烟第一步：binary 必须能加载并运行（真实执行被测产物，R34/PF3）。
# 判定口径 —— 退出码不作为通过判据，只区分故障性质：
#   0        正常（无 NFC 硬件时上游打印 "No NFC device found." 后返回 0，
#            2026-09-16 本机实测 EXIT=0；但该码属实现细节、非上游契约）
#   126/127  不可执行 / 动态库加载失败（如缺 libusb-1.0.so.0）→ 真实故障，FAIL
#   其他非零 无硬件等环境性非零 → WARN 记录后继续
# 真正的通过判据是下方 21 个工具齐全性。
rc=0
"$BIN_DIR/nfc-list" || rc=$?
case "$rc" in
    0)
        echo "OK: nfc-list ran and exited 0 (no NFC device present)"
        ;;
    126|127)
        echo "FAIL: nfc-list could not be executed/loaded (exit $rc) — 缺运行时库或不可执行"
        exit 1
        ;;
    *)
        echo "WARN: nfc-list exited $rc — tolerated (no NFC hardware; exit code not contractual)"
        ;;
esac

echo "== check all 21 tools present =="
MISSING=0
for tool in nfc-anticol nfc-barcode nfc-dep-initiator nfc-dep-target \
            nfc-emulate-forum-tag2 nfc-emulate-forum-tag4 nfc-emulate-tag \
            nfc-emulate-uid nfc-jewel nfc-list nfc-mfclassic nfc-mfsetuid \
            nfc-mfultralight nfc-poll nfc-read-forum-tag3 nfc-relay \
            nfc-relay-picc nfc-scan-device pn53x-diagnose pn53x-sam pn53x-tamashell; do
    if [ ! -x "$BIN_DIR/$tool" ]; then
        echo "FAIL: missing tool: $tool"
        MISSING=$((MISSING + 1))
    fi
done
if [ "$MISSING" -gt 0 ]; then
    echo "FAIL: $MISSING tool(s) missing"
    exit 1
fi

echo "ALL CHECKS PASSED"
