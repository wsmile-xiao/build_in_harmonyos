#!/usr/bin/env bash
# test_package/test_puzzles.sh — puzzles 20260720.3c36322 (Simon Tatham's
# Portable Puzzle Collection) HarmonyOS 测试套件。
#
# 在 conanrun 环境中运行（PATH 含已安装的 bin/）。逐场景执行并统计：
#   单元测试 10 项（上游 auxiliary 自检程序）
#   集成测试 40 项（游戏内建 --test-solve：can_solve=true 34 个真实解 + can_solve=false 6 个按上游语义输出 "Solution not known" 且 exit 0 冒烟）
#   其他测试  1 项（fuzzpuzz 消费有效存档）
#   鸿蒙特有  5 项（OHOS 前端 CLI 全链路：预设枚举/生成/计时/序列化/随机源）
# 口径：独立命令行场景数，每个场景 = 一条可判定成败的命令行执行。
set -u
SAVEDIR="${TMPDIR:-$PWD}/puzzles-save-$$"
mkdir -p "$SAVEDIR"

PASS=0
FAIL=0
FAILED_TESTS=""

run_test() {
    local name="$1"
    shift
    local out
    out=$(mktemp)
    if "$@" >"$out" 2>&1; then
        PASS=$((PASS + 1))
        echo "PASS  ${name}"
    else
        FAIL=$((FAIL + 1))
        FAILED_TESTS="${FAILED_TESTS} ${name}"
        echo "FAIL  ${name} :: $*"
        tail -5 "$out" | sed 's/^/      | /'
    fi
    rm -f "$out"
}

GAMES_SOLVABLE="blackbox bridges dominosa fifteen filling flip flood guess \
inertia keen lightup loopy magnets map mines mosaic net netslide palisade \
pattern pearl rect signpost singles sixteen slant solo tents towers tracks \
twiddle undead unequal unruly"
# can_solve=false 的 6 个游戏：--test-solve 按上游语义输出 "Solution not known" 且 exit 0（冒烟）
GAMES_SMOKE="cube galaxies pegs range samegame untangle"

echo "===== 单元测试（上游 auxiliary 自检程序） ====="
run_test "combi-test"          combi-test 3 5
run_test "divvy-test"          divvy-test
run_test "findloop-test"       findloop-test --iterations 100
run_test "hat-test"            hat-test
run_test "latin-test"          latin-test 3
run_test "penrose-legacy-test" penrose-legacy-test P3 5 3
run_test "penrose-test"        penrose-test
run_test "sort-test"           sort-test
run_test "spectre-test"        spectre-test
run_test "tree234-test"        tree234-test

echo "===== 集成测试（游戏内建 --test-solve） ====="
for g in $GAMES_SOLVABLE; do
    run_test "test-solve/$g" "$g" --test-solve --generate 2
done
for g in $GAMES_SMOKE; do
    run_test "test-solve-smoke/$g" "$g" --test-solve --generate 2
done

echo "===== 其他测试（fuzzpuzz） ====="
if solo --save $SAVEDIR/fuzzsave --generate 1 3x3 >/dev/null 2>&1 \
   && [ -s $SAVEDIR/fuzzsave0 ]; then
    run_test "fuzzpuzz" fuzzpuzz < $SAVEDIR/fuzzsave0
else
    FAIL=$((FAIL + 1)); FAILED_TESTS="${FAILED_TESTS} fuzzpuzz-setup"
    echo "FAIL  fuzzpuzz-setup :: 无法生成 fuzz 输入存档"
fi

echo "===== 鸿蒙特有测试（OHOS 前端 CLI 全链路） ====="
# 1) 预设枚举：--list-presets 输出非空且格式为「参数 标题」
out=$(mktemp)
if solo --list-presets >"$out" 2>&1 && [ -s "$out" ] \
   && grep -qE '^[^ ]+ .+$' "$out"; then
    PASS=$((PASS + 1)); echo "PASS  ohos-frontend/list-presets"
else
    FAIL=$((FAIL + 1)); FAILED_TESTS="${FAILED_TESTS} ohos-list-presets"
    echo "FAIL  ohos-frontend/list-presets"
fi
rm -f "$out"

# 2) 生成：--generate 输出可解析的 参数#种子 描述
out=$(mktemp)
if solo --generate 1 3x3 >"$out" 2>&1 && grep -qE '^3x3:[A-Za-z0-9_]+$' "$out"; then
    PASS=$((PASS + 1)); echo "PASS  ohos-frontend/generate"
else
    FAIL=$((FAIL + 1)); FAILED_TESTS="${FAILED_TESTS} ohos-generate"
    echo "FAIL  ohos-frontend/generate"; tail -3 "$out" | sed 's/^/      | /'
fi
rm -f "$out"

# 3) 计时：--time-generation 输出生成耗时（getrusage 在 bionic 上可用）
out=$(mktemp)
if solo --time-generation --generate 1 3x3 >"$out" 2>&1 \
   && grep -qE '^Solo .*: [0-9.]+$' "$out"; then
    PASS=$((PASS + 1)); echo "PASS  ohos-frontend/time-generation"
else
    FAIL=$((FAIL + 1)); FAILED_TESTS="${FAILED_TESTS} ohos-time-generation"
    echo "FAIL  ohos-frontend/time-generation"; tail -3 "$out" | sed 's/^/      | /'
fi
rm -f "$out"

# 4) 序列化：--save 产出非空存档文件（midend_serialise 落盘）
rm -f $SAVEDIR/ohos_save0
if solo --save $SAVEDIR/ohos_save --generate 1 3x3 >/dev/null 2>&1 \
   && [ -s $SAVEDIR/ohos_save0 ] \
   && head -c 9 $SAVEDIR/ohos_save0 | grep -q '^SAVEFILE:'; then
    PASS=$((PASS + 1)); echo "PASS  ohos-frontend/save-serialise"
else
    FAIL=$((FAIL + 1)); FAILED_TESTS="${FAILED_TESTS} ohos-save"
    echo "FAIL  ohos-frontend/save-serialise"
fi

# 5) 随机源：两次 --generate 相同参数必须产出不同随机种子
#    （验证 OHOS 前端 get_random_seed 的 /dev/urandom 熵源真实工作）
out1=$(mktemp); out2=$(mktemp)
solo --generate 1 3x3 >"$out1" 2>&1
solo --generate 1 3x3 >"$out2" 2>&1
if [ -s "$out1" ] && [ -s "$out2" ] && ! cmp -s "$out1" "$out2"; then
    PASS=$((PASS + 1)); echo "PASS  ohos-frontend/random-source"
else
    FAIL=$((FAIL + 1)); FAILED_TESTS="${FAILED_TESTS} ohos-random-source"
    echo "FAIL  ohos-frontend/random-source（两次生成输出相同）"
fi
rm -f "$out1" "$out2" "$SAVEDIR"/fuzzsave0 "$SAVEDIR"/ohos_save0; rmdir "$SAVEDIR" 2>/dev/null || true

echo ""
echo "===== 结果: PASS=${PASS} FAIL=${FAIL} ====="
if [ "$FAIL" -gt 0 ]; then
    echo "失败场景:${FAILED_TESTS}"
    exit 1
fi
exit 0
