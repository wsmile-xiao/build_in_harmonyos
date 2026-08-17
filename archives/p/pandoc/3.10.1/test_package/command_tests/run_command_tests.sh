#!/data/service/hnp/bin/bash
# test_package/command_tests/run_command_tests.sh
#
# 上游命令测试套件精选用例执行器（AI 补充设计测试用例，可执行、可复现）。
#
# 用例文件格式与上游 pandoc test/Tests/Command.hs 驱动格式一致：
#   ```
#   % pandoc <args>
#   <输入行>
#   ^D
#   <期望输出行>
#   ```
# 本脚本逐个解析用例文件，用交付的 pandoc 二进制实际执行，并将实际输出
# 与上游期望输出做字节级比对（统一 strip 行尾空白与末尾空行后比对，
# 与上游 Command.hs 的容差方式一致）。
#
# 用法：bash run_command_tests.sh [用例目录]
#   - 用例目录默认取本脚本同目录下 cases/
#   - pandoc 二进制从 PATH 取（conanrun 环境已注入），可用 PANDOC 环境变量覆盖
# 退出码：全部通过返回 0，任一失败返回 1。

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASES_DIR="${1:-${SCRIPT_DIR}/cases}"
PANDOC="${PANDOC:-pandoc}"

if ! command -v "$PANDOC" >/dev/null 2>&1; then
    echo "❌ 找不到 pandoc 二进制（PATH 中无 '$PANDOC'）"
    exit 2
fi

pass=0
fail=0
failed_cases=()

for case_file in "${CASES_DIR}"/*; do
    [ -f "$case_file" ] || continue
    name="$(basename "$case_file")"

    # ── 解析用例 ──
    cmd_line="$(grep -m1 '^% pandoc ' "$case_file" || true)"
    if [ -z "$cmd_line" ]; then
        echo "⚠ 跳过（无 % pandoc 命令）：$name"
        continue
    fi
    args="${cmd_line#% pandoc }"
    cmd_ln="$(grep -n -m1 '^% pandoc ' "$case_file" | cut -d: -f1)"
    end_ln="$(grep -n -m1 '^\^D$' "$case_file" | cut -d: -f1)"
    if [ -z "$cmd_ln" ] || [ -z "$end_ln" ] || [ "$end_ln" -le "$cmd_ln" ]; then
        echo "⚠ 跳过（结构异常）：$name"
        continue
    fi

    # 输入 = 命令行之后、^D 之前
    input="$(sed -n "$((cmd_ln + 1)),$((end_ln - 1))p" "$case_file")"
    # 期望输出 = ^D 之后（剔除收尾围栏行 ``` 与末尾空行）
    expected="$(sed -n "$((end_ln + 1)),\$p" "$case_file" \
        | sed '/^[[:space:]]*$/d' \
        | sed '$ { /^`\+$/d; }')"

    # ── 执行 ──
    actual="$(printf '%s\n' "$input" | "$PANDOC" $args 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "❌ FAIL $name (rc=$rc): pandoc $args"
        fail=$((fail + 1))
        failed_cases+=("$name")
        continue
    fi

    # ── 字节级比对（strip 行尾空白与末尾空行） ──
    norm_actual="$(printf '%s' "$actual" | sed 's/[[:space:]]*$//' | sed '/^[[:space:]]*$/d')"
    if [ "$norm_actual" = "$expected" ]; then
        echo "✅ PASS $name: pandoc $args"
        pass=$((pass + 1))
    else
        echo "❌ FAIL $name: pandoc $args（输出与上游期望不一致）"
        diff <(printf '%s\n' "$expected") <(printf '%s\n' "$norm_actual") \
            | head -10 | sed 's/^/    /'
        fail=$((fail + 1))
        failed_cases+=("$name")
    fi
done

total=$((pass + fail))
echo ""
echo "=============================================="
echo "结果: PASS=$pass FAIL=$fail SKIP=$(ls "${CASES_DIR}" 2>/dev/null | wc -l) - ${total}"
if [ "$fail" -gt 0 ]; then
    printf '失败用例: %s\n' "${failed_cases[*]}"
    exit 1
fi
echo "✅ 命令测试套件全部通过"
exit 0
