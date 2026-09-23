#!/bin/sh
# test_package/test.sh — bti 034 行为契约测试（离线、确定性，无网络）
#
# R34：这里是真实执行被测包安装出来的 bin/bti 并断言其真实输出，
# 不是 print-only / pass-only 空壳。
#
# 用法: sh test.sh <bti 可执行文件路径>
# 退出码 0 = 全部检查通过；非 0 = 有检查失败。
set -u

BTI="${1:?usage: test.sh <path-to-bti>}"

CHECKED=0
PASSED=0

ok() {
    CHECKED=$((CHECKED + 1))
    PASSED=$((PASSED + 1))
    echo "[PASS] $1"
}

no() {
    CHECKED=$((CHECKED + 1))
    echo "[FAIL] $1"
    echo "------- actual output -------"
    printf '%s\n' "$2"
    echo "-----------------------------"
}

# T1: --version 打印 configure 注入的上游版本号（证明二进制可执行 + 版本宏正确）
OUT=$("$BTI" --version 2>&1)
case "$OUT" in
    *"bti - version 034"*) ok "T1 --version => bti - version 034" ;;
    *) no "T1 --version 应输出 'bti - version 034'" "$OUT" ;;
esac

# T2: --help 输出完整用法（证明选项表与帮助文本被编进二进制）
OUT=$("$BTI" --help 2>&1)
case "$OUT" in
    *"Version: 034"*"Usage:"*"--dry-run"*) ok "T2 --help => Version/Usage/--dry-run 齐全" ;;
    *) no "T2 --help 输出不完整" "$OUT" ;;
esac

# T3: 配置文件缺失时给出可诊断错误（证明 config 解析路径真实执行）
OUT=$("$BTI" --config=/nonexistent/bti-test-missing.conf 2>&1)
case "$OUT" in
    *"is not found."*) ok "T3 缺失配置文件 => 可诊断错误" ;;
    *) no "T3 缺失配置文件未给出诊断" "$OUT" ;;
esac

# T4: 离线功能面 — dry-run 下真实走完 选项解析 → session 组装 → 推文拼装 →
#     请求构造（依赖 liboauth 的 oauth_url_escape/参数编码与 libcurl 链路），
#     仅跳过最终的 curl_easy_perform，因此可在无网络环境断言真实行为。
OUT=$(printf 'hello bti' | "$BTI" --debug --dry-run --account=someuser \
      --password=somepass --host=identi.ca --action=update 2>&1)
case "$OUT" in
    *"bti - version 034"*'data = status="hello bti"'*)
        ok "T4 离线 dry-run => 请求构造产出 status=\"hello bti\"" ;;
    *) no "T4 离线 dry-run 未走通请求构造" "$OUT" ;;
esac

echo "RESULT: ${PASSED}/${CHECKED} checks passed"
[ "$PASSED" -eq "$CHECKED" ] || exit 1
exit 0
