#!/bin/sh
# test_simka.sh — simka 1.5.3 消费者测试（真跑被测二进制 + 与上游 truth 逐字节比对）
#
# 用法: sh test_simka.sh <simka 包目录>
# 期望值来源: 上游 tag v1.5.3 的 tests/truth/results_k21_t0 与 results_k31_t2
#             里的 mat_presenceAbsence_jaccard.csv（本脚本内嵌其原文）。
set -eu

PKG="${1:-}"
[ -n "$PKG" ] || { echo "usage: test_simka.sh <simka package folder>" >&2; exit 2; }

BIN="$PKG/bin"
# 私有临时目录：按进程号分址，绝不相对 cwd；退出即清理
TMPD="${TMPDIR:-$HOME/tmp}/simka-test-$$"
rm -rf "$TMPD"
mkdir -p "$TMPD/out-tmp" "$TMPD/exp"
trap 'rm -rf "$TMPD"' EXIT INT HUP TERM

fail() { echo "FAIL: $*" >&2; exit 1; }
ok()   { echo "OK:   $*"; }

# ---------------------------------------------------------------- 1. 产物齐备
# 上游 CMakeLists 定义了 5 个 add_executable，一个都不能少。
# L1e 破坏性反向验证（把 bin/ 移走后重跑）正是被这一段判失败的。
for t in simka simkaCount simkaCountProcess simkaMerge simkaMinCore; do
    [ -x "$BIN/$t" ] || fail "缺可执行文件或不可执行: bin/$t"
done
ok "5/5 上游可执行目标齐备（simka simkaCount simkaCountProcess simkaMerge simkaMinCore）"

INPUT="$PKG/example/simka_input.txt"
[ -f "$INPUT" ] || fail "缺上游示例数据集 example/simka_input.txt"
ok "示例数据集就位: example/simka_input.txt"

# ---------------------------------------------------------------- 2. 计数并比对
# --- 超时护栏 ---------------------------------------------------------------
# simka 的全部调用都只经由本函数这一个入口（下面 3 处 check_case / run_simka
# 直接调用），所以在这里统一套 timeout：任何一次真跑挂住都会在 SIMKA_TIMEOUT
# 秒内被判 **FAIL**（rc 124/137/143 = 超时），绝不"跳过即通过"，也不减少断言数。
# 依据：上游 gatb-core CommonFile::gets() 在末行无 \n 的文件上会纯用户态死转
# （见 patches/0001-*.patch 与 notes.md），没有这层护栏就会把 conan create
# 吊死到被 harness 强杀（上一轮 verify 就是这么变成 Signal 15、判决不成立的）。
SIMKA_TIMEOUT="${SIMKA_TIMEOUT:-180}"

run_simka() {  # run_simka <k> <abundance-min> <out-dir> [extra args...]
    k="$1"; t="$2"; out="$3"; shift 3
    rc=0
    timeout -s KILL "$SIMKA_TIMEOUT" "$BIN/simka" -in "$INPUT" -out "$out" \
        -out-tmp "$TMPD/out-tmp" \
        -simple-dist -complex-dist -kmer-size "$k" -abundance-min "$t" \
        -verbose 0 "$@" > "$out.log" 2>&1 || rc=$?
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ] || [ "$rc" -eq 143 ]; then
        echo "--- simka stdout/stderr (tail 40) ---"; tail -n 40 "$out.log" >&2
        fail "simka k=$k t=$t 超过 ${SIMKA_TIMEOUT}s 未结束，已被 timeout 终止 (rc=$rc)"
    fi
    [ "$rc" -eq 0 ] \
        || { echo "--- simka stdout/stderr ---"; cat "$out.log"; fail "simka k=$k t=$t 退出码非 0 (rc=$rc)"; }
}

# simka 1.5.3 把每个距离矩阵写成 <name>.csv.gz。**上游自己的集成测试
# tests/simple_test.py 也是先解压再比对**（L16-24 decompress_simka_results()：
# 遍历 *.csv.gz -> 写出同名去 .gz -> 删除 .gz；L31 再 glob *.csv 与 truth 比），
# 所以这里做同一步解压是"照上游口径"，不是放宽判据。
decompress_results() {  # decompress_results <out-dir>
    d="$1"
    for f in "$d"/*.csv.gz; do
        [ -e "$f" ] || continue
        gunzip -c "$f" > "${f%.gz}" && rm -f "$f"
    done
}

# 上游 truth 原文（各 6 行：表头 + 5 个样本 A..E）
cat > "$TMPD/exp/k21_t0.csv" <<'EOF'
;A;B;C;D;E
A;0.000000;0.466667;0.551020;0.702899;0.466667
B;0.466667;0.000000;0.685714;0.398551;0.000000
C;0.551020;0.685714;0.000000;0.345588;0.685714
D;0.702899;0.398551;0.345588;0.000000;0.398551
E;0.466667;0.000000;0.685714;0.398551;0.000000
EOF

cat > "$TMPD/exp/k31_t2.csv" <<'EOF'
;A;B;C;D;E
A;0.000000;0.770833;0.937500;0.770833;0.466667
B;0.770833;0.000000;0.727273;0.000000;0.877778
C;0.937500;0.727273;0.000000;0.727273;0.966667
D;0.770833;0.000000;0.727273;0.000000;0.877778
E;0.466667;0.877778;0.966667;0.877778;0.000000
EOF

check_case() {  # check_case <k> <t> <期望文件名>
    k="$1"; t="$2"; exp="$TMPD/exp/$3.csv"
    out="$TMPD/res_k${k}_t${t}"
    run_simka "$k" "$t" "$out"
    decompress_results "$out"

    # 实测（本包一手读数，见 notes.md）：产物 21 个矩阵 = 上游 tests/truth/results_k*_t*/
    # 的 20 个 + 由 Bray-Curtis 派生、上游明示不进 truth 的 mat_abundance_jaccard。
    n=$(ls "$out"/*.csv 2>/dev/null | wc -l | tr -d ' ')
    [ "$n" -eq 21 ] || fail "k=$k t=$t 产出距离矩阵数=$n，实测应为 21（20 个有 truth + 1 个派生）"
    ok "k=$k t=$t 产出 21 个距离矩阵（20 个有上游 truth + 1 个派生）"

    got="$out/mat_presenceAbsence_jaccard.csv"
    [ -f "$got" ] || fail "k=$k t=$t 未产出 mat_presenceAbsence_jaccard.csv"
    cmp -s "$got" "$exp" \
        || { echo "--- got ---"; cat "$got"; echo "--- expect (上游 truth) ---"; cat "$exp"; \
             fail "k=$k t=$t 的 presenceAbsence_jaccard 矩阵与上游 truth 不一致"; }
    ok "k=$k t=$t 的 presenceAbsence_jaccard 矩阵与上游 truth 逐字节一致"

    # -simple-dist / -complex-dist 在 1.5.3 里就是两个矩阵族（不是额外的直方图文件）：
    #   simple  -> mat_presenceAbsence_*   (8)
    #   complex -> mat_abundance_*        (13)
    # 两个开关都打开才应有 8/13；少一个开关就少一整族，因此这条比原来的
    # "存在非 .csv 的非空文件" 判得更准（原来那条在 .csv.gz 命名下会假通过）。
    pa=$(ls "$out"/mat_presenceAbsence_*.csv 2>/dev/null | wc -l | tr -d ' ')
    ab=$(ls "$out"/mat_abundance_*.csv 2>/dev/null | wc -l | tr -d ' ')
    { [ "$pa" -eq 8 ] && [ "$ab" -eq 13 ]; } \
        || fail "k=$k t=$t 两个距离族计数不对：presenceAbsence=$pa(应 8) abundance=$ab(应 13)"
    ok "k=$k t=$t 的 simple/complex 两族矩阵齐备（presenceAbsence=$pa, abundance=$ab）"
}

check_case 21 0 k21_t0
check_case 31 2 k31_t2

# ------------------------------------------------- 3. 并行/内存切分的不变性
# 对应上游 simple_test.py 的 test_parallelization()：换核数与内存上限，结果必须一致。
par="$TMPD/res_parallel"
run_simka 21 0 "$par" -nb-cores 2 -max-memory 2000
decompress_results "$par"
cmp -s "$par/mat_presenceAbsence_jaccard.csv" "$TMPD/exp/k21_t0.csv" \
    || { echo "--- got(并行) ---"; cat "$par/mat_presenceAbsence_jaccard.csv"; \
         fail "-nb-cores 2 -max-memory 2000 下结果与默认不一致（分区/归并不变性被破坏）"; }
ok "并行与内存切分（-nb-cores 2 -max-memory 2000）下结果与默认一致"

echo "ALL SIMKA CONSUMER TESTS PASSED"
