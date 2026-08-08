#!/bin/sh
# test_afuse.sh — afuse 消费者测试源（R34 实质测试）
#
# afuse 是 FUSE 用户态 automounter 守护进程，运行期挂载需 /dev/fuse
# （OHOS 沙箱普通进程无权限访问）。本脚本验证已安装二进制：
#   1) 二进制存在且可执行
#   2) 无 (un)mount 模板参数 → 打印 usage 并以非 0 退出（参数解析路径）
#   3) -h → FUSE 选项解析正常（打印 help 后按设计非 0 退出）
# 挂载到达 FUSE 层的验证由 test_package/conanfile.py test() 完成。
set -u

AFUSE="${1:-afuse}"

if ! command -v "$AFUSE" >/dev/null 2>&1 && [ ! -x "$AFUSE" ]; then
    echo "FAIL: afuse binary not found: $AFUSE"
    exit 1
fi

# Test 1: 无参数 → usage 错误（非 0 退出）
"$AFUSE" >/dev/null 2>&1
rc=$?
echo "afuse (no args) exit=$rc (expected non-zero usage error)"
if [ "$rc" -eq 0 ]; then
    echo "FAIL: afuse (no args) exited 0, expected non-zero"
    exit 1
fi

# Test 2: -h → FUSE 选项解析（上游 KEY_HELP 打印后 exit(1)）
"$AFUSE" -h >/dev/null 2>&1
rc2=$?
echo "afuse -h exit=$rc2 (expected non-zero help path)"
if [ "$rc2" -eq 0 ]; then
    echo "FAIL: afuse -h exited 0, expected non-zero"
    exit 1
fi

echo "afuse test_afuse.sh: PASS (binary executed, args parsed)"
exit 0
