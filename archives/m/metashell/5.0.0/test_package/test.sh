#!/bin/sh
# test.sh — metashell 5.0.0 消费者用例（R34）
# 真实执行已安装 bin/metashell 二进制，3 个显式用例，shell 变量计数，
# 结束打印 HMBS_TEST_PACKAGE_RESULT（discovered/passedCount 为真实用例数）。
# 注意：不用 set -e，保证任何失败都能走到标记打印；每个用例显式判分支。

PASSED=0
FAILED=0

pass_case() {
  echo "PASS: $1"
  PASSED=$((PASSED + 1))
}

fail_case() {
  echo "FAIL: $1"
  FAILED=$((FAILED + 1))
}

echo "--- metashell consumer test ---"

if ! command -v metashell >/dev/null 2>&1; then
  echo "metashell binary not in PATH: $(echo "$PATH")"
  fail_case "T1 metashell --help"
  fail_case "T2 metashell --engine wave --nosplash empty startup"
  fail_case "T3 metashell --engine wave smoke"
else
  # T1: --help 可运行且输出非空
  if metashell --help >help_out.txt 2>&1; then
    if [ -s help_out.txt ]; then
      echo "T1 help first line: $(head -n 1 help_out.txt)"
      pass_case "T1 metashell --help"
    else
      echo "T1 empty --help output"
      fail_case "T1 metashell --help"
    fi
  else
    echo "T1 --help exit=$? output:"
    head -n 5 help_out.txt 2>/dev/null
    fail_case "T1 metashell --help"
  fi

  # T2: wave 引擎空输入启动（OHOS 可用路径）。
  # 默认 auto/clang 引擎需在构建期写死的路径中发现宿主 clang++（templight_metashell、
  # /usr/bin/clang++ 等），OHOS 预检/CI 均无此路径（旧逻辑 exit=1，
  # “clang++ not found. Checked: ...”见 #62937），且即使找到也缺 Linux C++ sysroot；
  # 故消费者启动语义改测无需外部编译器的 wave 引擎，与 T3 互补（T2 空输入、T3 typedef 求值）。
  if printf "" | metashell --engine wave --nosplash >nosplash_out.txt 2>&1; then
    echo "T2 wave nosplash exit=0 size=$(wc -c <nosplash_out.txt)"
    pass_case "T2 metashell --engine wave --nosplash empty startup"
  else
    echo "T2 wave nosplash exit=$? output:"
    head -n 5 nosplash_out.txt 2>/dev/null
    fail_case "T2 metashell --engine wave --nosplash empty startup"
  fi

  # T3: wave 引擎冒烟（无需外部编译器）
  if printf "typedef int msh_consumer_check;\n" | metashell --engine wave --nosplash >wave_out.txt 2>&1; then
    echo "T3 wave exit=0 size=$(wc -c <wave_out.txt)"
    pass_case "T3 metashell --engine wave smoke"
  else
    echo "T3 wave exit=$? output:"
    head -n 5 wave_out.txt 2>/dev/null
    fail_case "T3 metashell --engine wave smoke"
  fi
fi

DISCOVERED=3
if [ "$FAILED" -eq 0 ] && [ "$PASSED" -eq "$DISCOVERED" ]; then
  OVERALL_PASSED=true
else
  OVERALL_PASSED=false
fi

# rule4: 3 用例均测 OHOS 可用路径（T1 --help、T2 wave 空启动、T3 wave 求值），
# 预期 100% 通过；失败即真实失败，不附 gaps 豁免。
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":${OVERALL_PASSED},\"command\":\"sh test.sh (metashell --help / --engine wave empty / --engine wave typedef)\",\"discovered\":${DISCOVERED},\"passedCount\":${PASSED}}"

if [ "$OVERALL_PASSED" = "true" ]; then
  echo "CONSUMER_ALL_PASS passed=$PASSED/$DISCOVERED"
  exit 0
else
  echo "CONSUMER_FAIL passed=$PASSED failed=$FAILED discovered=$DISCOVERED"
  exit 1
fi
