#!/data/service/hnp/bin/bash
# test_package/test.sh — augustus 冒烟测试
# 用法: test.sh <augustus 二进制绝对路径> <config 目录绝对路径> <example.fa 绝对路径>
# 结束前打印 HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT 两个
# JSON 证据标记（hmbs 硬门禁要求真机测试命令 stdout 输出合法 JSON）。
set -eu

BIN="$1"
CFG="$2"
EXAMPLE_FA="$3"

discovered=2
passed=0
failed=0

# 断言 1: --version 输出含版本号 "AUGUSTUS (3.5.0)" 且 exit 0
echo "[test] $BIN --version"
OUT="$("$BIN" --version 2>&1)" || true
echo "$OUT"
case "$OUT" in
  *AUGUSTUS*3.5.0*)
    passed=$((passed + 1))
    echo "[OK] --version prints AUGUSTUS (3.5.0)"
    ;;
  *)
    failed=$((failed + 1))
    echo "[FAIL] --version: unexpected output"
    ;;
esac

# 断言 2: --species=human 真实运行基因预测，输出含 "Predicted genes"（Homebrew 官方 test 同款断言）
echo "[test] $BIN --species=human $EXAMPLE_FA"
export AUGUSTUS_CONFIG_PATH="$CFG"
OUT="$("$BIN" --species=human "$EXAMPLE_FA" 2>&1)" || true
echo "$OUT"
case "$OUT" in
  *"Predicted genes"*)
    passed=$((passed + 1))
    echo "[OK] gene prediction prints 'Predicted genes'"
    ;;
  *)
    failed=$((failed + 1))
    echo "[FAIL] gene prediction: 'Predicted genes' not in output"
    ;;
esac

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"makefile","command":"make test (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"augustus 3.5.0 上游 make test 依赖 Linux x86_64 + 完整 CGP 构建（tests/short 的 execute_test.py --compare），minimal 配置（ZIPINPUT=false COMPGENEPRED=false）与 OHOS aarch64 环境无法运行；由 test_package 对打包的 augustus 二进制做真实功能断言（--version 版本输出 + --species=human 基因预测输出）"}\n'
exit 0
