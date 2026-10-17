#!/data/service/hnp/bin/bash
# test_package/cli_smoke.sh — g810-led CLI 冒烟测试
# 在 conanrun 环境运行（PATH 含安装的 bin/）
set -euo pipefail

echo "[cli] g810-led -h"
# -h 实际返回 0，|| true 仅防御 set -e
OUT=$(g810-led -h 2>&1) || true
echo "$OUT" | head -4
echo "$OUT" | grep -q "Version : 0.4.3" && echo "CLI-VERSION-OK" || {
    echo "CLI-VERSION-FAIL: version string not found"
    exit 1
}

echo "[cli] g810-led --list-keyboards"
RC=0; g810-led --list-keyboards >/dev/null 2>&1 || RC=$?
echo "list-keyboards exit=$RC"
# 无键盘设备时预期退出码 1（listKeyboards 空列表返回 1）
[ "$RC" -eq 1 ] && echo "CLI-LIST-OK" || {
    echo "CLI-LIST-FAIL: expected exit 1 without device, got $RC"
    exit 1
}

echo "[cli] g810-led -a invalidcolor"
RC=0; g810-led -a invalidcolor >/dev/null 2>&1 || RC=$?
echo "invalid-color exit=$RC"
# 无设备时任何 -a 命令先 open 失败，预期退出码 2（main.cpp return 2）
[ "$RC" -eq 2 ] && echo "CLI-ERR-OK" || {
    echo "CLI-ERR-FAIL: expected exit 2 (open failed) for color cmd, got $RC"
    exit 1
}

echo "[cli] g810-led -a ff00ff (valid color, no device)"
RC=0; g810-led -a ff00ff >/dev/null 2>&1 || RC=$?
echo "valid-color-nodevice exit=$RC"
[ "$RC" -eq 2 ] && echo "CLI-NODEV-OK" || {
    echo "CLI-NODEV-FAIL: expected exit 2 (open failed), got $RC"
    exit 1
}

echo "CLI-SMOKE-OK"
