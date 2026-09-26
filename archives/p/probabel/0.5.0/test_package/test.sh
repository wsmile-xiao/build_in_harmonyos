#!/data/service/hnp/bin/bash
# test_package/test.sh — ProbABEL 0.5.0 消费者测试：以使用者身份运行**已安装**的交付物。
#
# 素材（原样拷入上游文件，未改写）：checks/inputfiles/{height.txt,test.mldose,test.mlinfo,
# test.dose.fvi,test.dose.fvd,test.map} 与 checks/verified_results/height_add.out.txt。
# 契约：A4 沿用上游 checks/test_qt.sh 的自洽比对（mldose vs dose.fvi 必须逐字节相同，
# 上游 run_diff.sh 即用朴素 diff）；A5 把上游 verified_results 当**数值锚点**（按列名对齐、
# 容差 1e-9、跳过 -c 的回报列）而非逐字节基准——该文件对当前 inputfiles 已过期
# （只有 5 行，而 test.map 有 6 个 SNP），上游自己的套件也不与它逐字节比。
# 负向断言需要拿到非零返回码（下方 probabel 缺 -d 必须失败、包装器返回码需先捕获再判定），
# 启用 -e 会在取到 rc 之前退出并跳过后继断言，故有意只开 -u -o pipefail；
# 全部断言以 || fail（fail() 内 exit 1）显式收口，不存在假通过。
set -u -o pipefail
cd "$(dirname "$0")"
here="$PWD"
work="work.$$.dir"
rm -rf "$work"; mkdir -p "$work"
cp input/height.txt input/test.mldose input/test.mlinfo input/test.map "$work/"
# palinear 读 .fvi 时会自行推导同名 .fvd 路径 ⇒ 两种形态必须一起提供
cp input/test.dose.fvi input/test.dose.fvd "$work/"
cd "$work" || exit 1

fail() { echo "CONSUMER FAIL: $*"; exit 1; }
pass() { echo "[$*] OK"; }

command -v palinear > /dev/null 2>&1 || fail "palinear 不在 PATH（交付未安装）"
command -v probabel > /dev/null 2>&1 || fail "probabel 包装器不在 PATH"

run_palinear() {  # $1=剂量文件 $2=输出前缀 [额外参数...]
    local dose="$1" out="$2"; shift 2
    palinear -p height.txt -d "$dose" -i test.mlinfo -m test.map -o "$out" "$@" > run.log 2>&1
}

# 1) perl 包装器（配方已修 shebang）必须可执行并给出用法
probabel > probabel.msg 2>&1; rc_pb=$?
[ -s probabel.msg ] || fail "probabel 包装器无任何输出 (rc=$rc_pb)"
grep -qiE "usage|probabel" probabel.msg || fail "probabel 输出无用法信息"
pass "1 probabel 包装器可执行 (rc=$rc_pb)"

# 2) 交付二进制在真实输入上跑通并产出结果
run_palinear test.mldose base || fail "palinear 退出码非 0：$(head -3 run.log)"
[ -s base_add.out.txt ] || fail "palinear 未产出 base_add.out.txt"
pass "2 palinear 运行成功并产出结果文件"

# 3) 结构：表头含关键列、分析 SNP 数与 map 一致、名称与顺序一致
head -1 base_add.out.txt | grep -qw chi2_SNP_add || fail "表头缺 chi2_SNP_add 列"
n_map=$(($(wc -l < test.map) - 1))
n_out=$(($(wc -l < base_add.out.txt) - 1))
[ "$n_map" = "$n_out" ] || fail "SNP 数不符：map=$n_map 输出=$n_out"
# 上游 test.map 内部分隔符不一致（前 5 行制表符、末行空格）⇒ 一律用空白分列取首字段，
# 不用 cut -f1（对空格分隔的那行会把整行当第一列）。
paste <(tail -n +2 test.map | awk '{print $1}') <(tail -n +2 base_add.out.txt | awk '{print $1}') \
    | awk -F'\t' '$1 != $2 {bad=1} END {exit bad}' || fail "SNP 名/顺序与 map 不一致"
pass "3 结构断言（$n_out 个 SNP，名称与顺序一致）"

# 4) 上游同契约：mldose 与 dose.fvi 两种输入的结果必须逐字节相同
run_palinear test.dose.fvi basefv || fail "palinear(dose.fvi) 退出码非 0"
diff base_add.out.txt basefv_add.out.txt > a4.diff 2>&1 \
    || fail "dose vs dose_fv 不一致：$(head -4 a4.diff)"
pass "4 dose 与 dose.fvi 结果逐字节一致（上游 test_qt.sh 契约）"

# 5) 数值锚点：与上游 verified_results 按列名对齐比较（容差 1e-9；跳过 -c 的回报列 chrom）
# PY: CI worker 的 python3 在 /data/app/bin（判决日志 _=/data/app/bin/python3），
# 设备侧在 ~/.harmonybrew/bin；两处都不存在时显式失败，不让数值锚点静默跳过。
PY=$(command -v python3 2>/dev/null || command -v /data/app/bin/python3 2>/dev/null || command -v /data/service/hnp/bin/python3 2>/dev/null || true)
[ -z "$PY" ] && { echo "CONSUMER FAIL: no python3 resolvable for numeric anchor"; exit 1; }
"$PY" - "$here/expected/height_add.out.txt" base_add.out.txt <<'PY' || fail "数值锚点未通过"
import math, sys
TOL, SKIP = 1e-9, {"chrom"}

def read(path):
    rows = [ln.split() for ln in open(path) if ln.strip()]
    header, table = rows[0], rows[1:]
    return header, {r[0]: dict(zip(header, r)) for r in table}

rh, ref = read(sys.argv[1])
gh, got = read(sys.argv[2])
cols = [c for c in rh if c in gh and c not in SKIP and c != "name"]
assert cols, "无可比列"
n_snp = cells = 0
for snp, rrow in ref.items():
    grow = got.get(snp)
    if grow is None:
        continue                       # 基准未覆盖的 SNP 由 3/4 号断言约束
    n_snp += 1
    for c in cols:
        r, g = rrow[c], grow[c]
        try:
            rf, gf = float(r), float(g)
        except ValueError:
            assert r == g, f"{snp}/{c}: 非数值列不等 {r!r} vs {g!r}"
        else:
            if math.isnan(rf) or math.isnan(gf):
                assert math.isnan(rf) and math.isnan(gf), f"{snp}/{c}: nan 语义不一致 {r} vs {g}"
            else:
                assert abs(rf - gf) <= TOL * max(1.0, abs(rf)), f"{snp}/{c}: {r} vs {g}"
        cells += 1
assert n_snp >= 5 and cells >= 5 * len(cols), f"锚点覆盖过少：SNP={n_snp} 单元格={cells}"
print(f"    锚点：{n_snp} 个同名 SNP × {len(cols)} 列 = {cells} 个单元格，容差 {TOL:g}")
PY
pass "5 与上游 verified_results 数值一致"

# 6) 参数语义：-c 19 时多出 chrom 列、值全为 19，且去掉该列后与不带 -c 的输出逐字节一致
#    （chrom 的列号按表头名定位，不硬编码下标）
run_palinear test.mldose chromopts -c 19 || fail "palinear -c 19 退出码非 0"
head -1 chromopts_add.out.txt | grep -qw chrom || fail "-c 19 未产生 chrom 列"
awk 'NR==1 { for (i=1;i<=NF;i++) if ($i=="chrom") c=i; if (!c) exit 1; next }
     $c != "19" { bad=1 } END { exit bad }' chromopts_add.out.txt \
    || fail "-c 19 的 chrom 列取值非 19"
awk 'NR==1 { for (i=1;i<=NF;i++) if ($i=="chrom") c=i }
     { out=""; for (i=1;i<=NF;i++) if (i!=c) out = out (out==""?"":" ") $i; print out }' chromopts_add.out.txt > a6.stripped
diff base_add.out.txt a6.stripped > a6.diff || fail "-c 19 改变了计算结果：$(head -4 a6.diff)"
pass "6 -c 19 语义正确（chrom 列=19，去掉该列后与不带 -c 的输出逐字节一致）"

# 7) 错误路径：缺必需参数 -d 时必须非零退出
palinear -p height.txt -i test.mlinfo -m test.map -o err > /dev/null 2>&1
[ $? -ne 0 ] || fail "缺 -d 时 palinear 仍以 0 退出"
pass "7 缺必需参数时非零退出"

# 8) 其余打包工具均已安装且响应调用
#    （extract-snp 上游 configure.ac:202-206 明确 --enable-extract-snp 默认关闭、
#     自述 "this program is not finished yet" ⇒ 不属交付面，不断言其存在）
for tool in palogist pacoxph; do
    command -v "$tool" > /dev/null 2>&1 || fail "$tool 未安装"
    "$tool" > "$tool.msg" 2>&1
    [ -s "$tool.msg" ] || fail "$tool 无任何输出"
done
pass "8 palogist/pacoxph 均已安装且响应调用"

# 9) 交付别名 probabel.pl 必须可用（上游用 ln -s $(DESTDIR)$(bindir)/probabel 安装，
#    链接目标含 DESTDIR ⇒ 打包后会悬空；配方 package() 已改写为相对链接）
alias_path="$(command -v probabel.pl || true)"
[ -n "$alias_path" ] || fail "probabel.pl 别名未交付"
[ -e "$alias_path" ] || fail "probabel.pl 是悬空链接：$(readlink "$alias_path")"
"$alias_path" > alias.msg 2>&1
[ -s alias.msg ] || fail "probabel.pl 可执行但无输出"
pass "9 probabel.pl 别名可用（$(basename "$(readlink "$alias_path" || echo 副本)")）"

cd "$here" && rm -rf "$work"
echo "test_package: PASS（9 组消费者断言）"
