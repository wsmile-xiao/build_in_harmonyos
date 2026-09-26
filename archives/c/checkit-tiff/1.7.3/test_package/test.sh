#!/usr/bin/env bash
# test_package/test.sh — 7 个 E2E 场景验证 checkit-tiff 消费者侧功能
# 全部断言都落在已安装包的真实二进制 / 配置 / TIFF fixture 上，任一场景
# 失败即 exit 非零，使 conan create 失败。场景清单与 test_package/MANIFEST.yml 一致：
# 1) 合法 baseline: baseline_minimal 配置 + 合法 TIFF 必须通过
# 2) mandatory tag 缺失被拒绝: 配置要求 tag 270，而该 TIFF 不含 270，必须拒绝
# 3) PCRE2 合法 regex 配置被解析器接受
# 4) 配置白名单拒绝: mandatory tag 9999 缺失必须拒绝
# 5) PCRE2 负匹配: regex 与实际值不符必须拒绝
# 6) PCRE2 非法 regex 必须被解析器拒绝
# 7) 反向对照: 合法语法必须仍被接受（防止工具不可用导致上面几条假通过）
set -euo pipefail

BIN="checkit_tiff"
CFG_DIR="${CHECKIT_TIFF_CFG_DIR:-/usr/local/share/checkit_tiff/example_configs}"
TIFF_PASS_DIR="${CHECKIT_TIFF_PASS_DIR:-/usr/local/share/checkit_tiff/tiffs_should_pass}"
TIFF_FAIL_DIR="${CHECKIT_TIFF_FAIL_DIR:-/usr/local/share/checkit_tiff/tiffs_should_fail}"

# 如果是 conan test_package 环境，路径在 package_folder/share/checkit_tiff/
if [ -n "${CONAN_PACKAGE_FOLDER:-}" ]; then
    CFG_DIR="${CONAN_PACKAGE_FOLDER}/share/checkit_tiff/example_configs"
    TIFF_PASS_DIR="${CONAN_PACKAGE_FOLDER}/share/checkit_tiff/tiffs_should_pass"
    TIFF_FAIL_DIR="${CONAN_PACKAGE_FOLDER}/share/checkit_tiff/tiffs_should_fail"
fi

echo "=== checkit-tiff test_package E2E tests ==="
echo "Binary: $BIN"
echo "Config dir: $CFG_DIR"
echo "Pass TIFF dir: $TIFF_PASS_DIR"
echo "Fail TIFF dir: $TIFF_FAIL_DIR"

# OHOS worker 的 /tmp 是只读文件系统（实测：/tmp/test_*.cfg: Read-only file system），
# 所以不能硬编码 /tmp。优先用环境提供的 TMPDIR，退回 $HOME，再退回包目录。
_workdir_base="${TMPDIR:-${HOME:-}}"
if [ -z "$_workdir_base" ] || ! ( mkdir -p "$_workdir_base" && [ -w "$_workdir_base" ] ) 2>/dev/null; then
    _workdir_base="${CONAN_PACKAGE_FOLDER:-$PWD}"
fi
WORKDIR="${_workdir_base%/}/checkit-tiff-e2e.$$"
mkdir -p "$WORKDIR"
CFG_POSITIVE="$WORKDIR/test_pcre2_positive.cfg"
CFG_WHITELIST="$WORKDIR/test_whitelist_reject.cfg"
CFG_NEGATIVE="$WORKDIR/test_pcre2_negative.cfg"
echo "Work dir: $WORKDIR"

# Helper: run checkit_tiff and check exit code
run_test() {
    local name="$1"
    local config="$2"
    local tiff="$3"
    local expect_pass="$4"  # "pass" or "fail"
    shift 4
    echo ""
    echo "--- Test: $name ---"
    echo "Config: $config"
    echo "TIFF: $tiff"
    echo "Expect: $expect_pass"
    if "$BIN" -c "$config" "$tiff" "$@"; then
        result=0
    else
        result=$?
    fi
    if [ "$expect_pass" = "pass" ] && [ $result -eq 0 ]; then
        echo "PASS"
        return 0
    elif [ "$expect_pass" = "fail" ] && [ $result -ne 0 ]; then
        echo "PASS (correctly rejected)"
        return 0
    else
        echo "FAIL: expected $expect_pass, got exit code $result"
        return 1
    fi
}

# 1) 合法 baseline: baseline_minimal config + minimal_valid_baseline.tiff 必须通过
run_test "合法 baseline" \
    "$CFG_DIR/cit_tiff_baseline_minimal.cfg" \
    "$TIFF_PASS_DIR/minimal_valid_baseline.tiff" \
    "pass"

# 2) mandatory tag 缺失被拒绝: 配置用 PCRE2 规则要求 tag 270 (ImageDescription)
#    匹配 regex("^test.*")，而 minimal_valid_baseline.tiff 不含 tag 270，
#    因此 checkit_tiff 必须以非零码拒绝——这是真实的「规则被正确执行」证据，
#    不是恒真断言：若工具错误地放行，run_test 会判定 FAIL。
cat > "$CFG_POSITIVE" <<'EOF'
270; mandatory; regex("^test.*")
EOF
run_test "mandatory tag 270 缺失被拒绝 (PCRE2 规则生效)" \
    "$CFG_POSITIVE" \
    "$TIFF_PASS_DIR/minimal_valid_baseline.tiff" \
    "fail"

# 为了真正测试 PCRE2 正匹配，我们需要检查 checkit_check_config 能否解析 regex。
# 注意：checkit_check_config 只从 stdin 读配置语法，完全忽略命令行参数
# （上游 t/Testcall.pm 也是用管道喂给它的）；而且解析器需要行尾换行才能判定
# 一个 regex 是否非法。若按 argv 传参，stdin 为空时连垃圾输入都会返回 0，
# 断言会变成永远为真的空壳测试。所以这里统一用 printf '%s\n' 管道输入。
echo ""
echo "--- Test: PCRE2 配置语法验证 (正匹配) ---"
if printf '%s\n' '270; mandatory; regex("^test.*")' | checkit_check_config >/dev/null 2>&1; then
    echo "PASS: regex config accepted"
else
    echo "FAIL: regex config rejected"
    exit 1
fi

# 3) 配置白名单拒绝: mandatory tag 缺失必须拒绝
# minimal_valid_baseline.tiff 有所有 mandatory tags，所以应该通过
# 我们用一个缺少 mandatory tag 的配置来测试拒绝
cat > "$CFG_WHITELIST" <<'EOF'
9999; mandatory; any
EOF
run_test "配置白名单拒绝 (缺少 mandatory tag 9999)" \
    "$CFG_WHITELIST" \
    "$TIFF_PASS_DIR/minimal_valid_baseline.tiff" \
    "fail"

# 4) PCRE2 负匹配: regex 不匹配时必须拒绝
cat > "$CFG_NEGATIVE" <<'EOF'
256; mandatory; regex("^9999$")
EOF
run_test "PCRE2 负匹配 (ImageWidth 不匹配 regex)" \
    "$CFG_NEGATIVE" \
    "$TIFF_PASS_DIR/minimal_valid_baseline.tiff" \
    "fail"

# 额外: 验证 checkit_check_config 拒绝无效 regex
# 同样必须走 stdin + 换行：argv 会被忽略，缺换行则非法的 "[invalid" 会被误判为合法
echo ""
echo "--- Test: PCRE2 配置语法验证 (负匹配/无效 regex) ---"
if printf '%s\n' '256; mandatory; regex("[invalid")' | checkit_check_config >/dev/null 2>&1; then
    echo "FAIL: invalid regex should be rejected"
    exit 1
else
    echo "PASS: invalid regex correctly rejected"
fi

# 反向对照: 确认上面的拒绝不是因为工具缺失/整体不可用，而是真的在校验语法
echo ""
echo "--- Test: checkit_check_config 可用性对照 (合法语法必须被接受) ---"
if printf '%s\n' '256; mandatory; any' | checkit_check_config >/dev/null 2>&1; then
    echo "PASS: checkit_check_config is functioning"
else
    echo "FAIL: checkit_check_config rejected a valid grammar"
    exit 1
fi

# 清理
rm -rf "$WORKDIR"

echo ""
echo "=== All E2E tests passed ==="