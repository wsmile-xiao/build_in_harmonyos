#!/bin/sh
# 鸿蒙特有测试（test_package）— 用安装后的 esolver 求解自备 .map 标准格式样例。
#
# 断言口径：14 条产物断言（ok 1..14）。防「rc=0 却 0 字节输出」的假绿：
# 每次求解都同时断言 rc==0、.sol 文件非空（-s）、含 "status = OPTIMAL"、
# 含预期最优值 "Value = 14" 与解坐标。
#
# 样例为本任务自备（上游源码树零 .map/零夹具）：canonical 副本与 sha256 锚定
# 见任务私有 sources/fixtures/（不进提交面）；此处按锚定字节内联生成并在运行时
# 逐字节校验 sha256，保证测试输入与留档样例同源。
set -u

WORK="$PWD/ohos_solve_work"
rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$WORK" || exit 1
cd "$WORK" || exit 1

N=0
FAILED=0
ok()   { N=$((N + 1)); echo "ok $N - $1"; }
not_ok() { N=$((N + 1)); FAILED=$((FAILED + 1)); echo "not ok $N - $1"; }

# --- 1-2: 被测 CLI 可用性与版本标记 ---
if ESOLVER=$(command -v esolver 2>/dev/null) && [ -n "$ESOLVER" ]; then
    ok "esolver resolvable on PATH"
else
    not_ok "esolver resolvable on PATH"
fi

V=$(esolver -v 2>/dev/null || true)
case "$V" in
    *"QSopt_ex 2.5.10.3"*) ok "esolver -v prints QSopt_ex 2.5.10.3 marker" ;;
    *) not_ok "esolver -v prints QSopt_ex 2.5.10.3 marker (got: $V)" ;;
esac

# --- 3-8: LP 标准格式样例（CPLEX LP 文本，-L 显式按 LP 解析） ---
cat > sample_lp.map <<'__FIX_LP__'
\ comment: qsopt-ex self-made sample fixture - standard CPLEX LP format
\ maximize 2x + 3y  s.t.  x + y <= 5,  x <= 2,  y <= 4,  x,y >= 0 (LP default lower bound 0)
\ unique optimum: x=1, y=4, objective = 14
Maximize
 obj: 2 x + 3 y
Subject To
 c1: x + y <= 5
 c2: x <= 2
 c3: y <= 4
End
__FIX_LP__
H=$(sha256sum sample_lp.map); H=${H%% *}
if [ "$H" = "9bdf1d2b8faaf65839167466f3e537566577a9741363b1aba67c5a32b696d433" ]; then ok "sample_lp.map sha256 matches anchored fixture"; else not_ok "sample_lp.map sha256 matches anchored fixture (got $H)"; fi

if esolver -L -O out_lp.sol sample_lp.map >/dev/null 2>&1; then
    ok "esolver LP solve rc==0"
else
    not_ok "esolver LP solve rc==0"
fi
if [ -s out_lp.sol ]; then ok "out_lp.sol non-empty"; else not_ok "out_lp.sol non-empty"; fi
if grep -q "status = OPTIMAL" out_lp.sol; then ok "out_lp.sol contains status = OPTIMAL"; else not_ok "out_lp.sol contains status = OPTIMAL"; fi
if grep -q "Value = 14" out_lp.sol; then ok "out_lp.sol contains expected objective Value = 14"; else not_ok "out_lp.sol contains expected objective Value = 14"; fi
if grep -q "x = 1" out_lp.sol; then ok "out_lp.sol contains solution x = 1"; else not_ok "out_lp.sol contains solution x = 1"; fi

# --- 9-14: MPS 标准格式样例（固定列格式 + CPLEX OBJSENSE MAX 扩展） ---
cat > sample_mps.map <<'__FIX_MPS__'
* qsopt-ex self-made sample fixture - standard fixed-column MPS format
* same LP as sample_lp.map: unique optimum x=1, y=4, objective = 14
NAME          QSMP
OBJSENSE
  MAX
ROWS
    N  OBJ     
    L  C1      
    L  C2      
    L  C3      
COLUMNS
    X         OBJ                  2   C1                   1
    X         C2                   1
    Y         OBJ                  3   C1                   1
    Y         C3                   1
RHS
    RHS     C1                 5       C2                 2
    RHS     C3                 4
ENDATA
__FIX_MPS__
H=$(sha256sum sample_mps.map); H=${H%% *}
if [ "$H" = "2171121fd2659947935f9fe1b5179b43215a373e5cd094040f2e211d86d54c42" ]; then ok "sample_mps.map sha256 matches anchored fixture"; else not_ok "sample_mps.map sha256 matches anchored fixture (got $H)"; fi

if esolver -O out_mps.sol sample_mps.map >/dev/null 2>&1; then
    ok "esolver MPS solve rc==0"
else
    not_ok "esolver MPS solve rc==0"
fi
if [ -s out_mps.sol ]; then ok "out_mps.sol non-empty"; else not_ok "out_mps.sol non-empty"; fi
if grep -q "status = OPTIMAL" out_mps.sol; then ok "out_mps.sol contains status = OPTIMAL"; else not_ok "out_mps.sol contains status = OPTIMAL"; fi
if grep -q "Value = 14" out_mps.sol; then ok "out_mps.sol contains expected objective Value = 14"; else not_ok "out_mps.sol contains expected objective Value = 14"; fi
if grep -q "X = 1" out_mps.sol; then ok "out_mps.sol contains solution X = 1"; else not_ok "out_mps.sol contains solution X = 1"; fi

echo "# qsopt-ex ohos solve test: total=$N pass=$((N - FAILED)) fail=$FAILED"
[ "$FAILED" -eq 0 ] || exit 1
exit 0
