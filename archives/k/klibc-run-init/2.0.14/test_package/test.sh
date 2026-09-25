#!/data/service/hnp/bin/bash
# test_package/test.sh — klibc-run-init 负向 smoke 测试
# run-init 没有 --version/--help；无参调用时向 stderr 打印 Usage 并退出码 1。
# 真实删根/MS_MOVE/chroot 路径需要 root 加 PID-1 上下文，在 CI 中不安全；
# -n dry-run 仍会执行 chroot（runinitlib.c run_init()），同样不在 CI 执行。
set -u

prog="$1"

if [ -z "$prog" ] || [ ! -x "$prog" ]; then
    echo "FAIL: packaged run-init is missing or not executable: $prog"
    exit 1
fi

err=./run-init-usage.err
rm -f "$err"

# 注意：if 条件为假且无 else 分支时 if 构造会把状态码重置为 0（POSIX），
# 因此用 || rc=$? 捕获真实退出码。
rc=0
"$prog" 2>"$err" || rc=$?

if [ "$rc" -eq 0 ]; then
    echo "FAIL: run-init with no args should exit 1 (usage), got exit 0"
    rm -f "$err"
    exit 1
fi

if [ "$rc" -ne 1 ]; then
    echo "FAIL: expected exit code 1, got $rc (exec-denied means missing .codesign)"
    cat "$err"
    rm -f "$err"
    exit 1
fi

if ! grep -q "Usage:" "$err"; then
    echo "FAIL: usage message not printed on stderr"
    cat "$err"
    rm -f "$err"
    exit 1
fi

rm -f "$err"
echo "PASS: run-init negative smoke (usage on stderr + exit code 1)"
exit 0
