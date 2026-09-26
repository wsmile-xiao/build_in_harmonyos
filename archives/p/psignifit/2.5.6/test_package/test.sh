#!/data/service/hnp/bin/bash
# test_package/test.sh — psignifit 2.5.6 消费者测试（Conan L1）
#
# 覆盖面（14 断言，与 MANIFEST.yml assertion_count=14 对应）：
#   [1-2]   CLI 冒烟：--version / --help（补丁 0002，与 Conan L2 同口径）
#   [3-8]   上游唯一测试入口 `psignifit -t`：内嵌 8×3 数据 + 4 金值
#           （容差 = 每参数相对误差 ≤0.1%，psig-src/psignifit.c::SelfTest）
#   [9-13]  文件/stdin 输入面（补丁 0001，Debian #975467 同款 aarch64 unsigned char 修复），
#           含 Debian run-unit-test 同形管道输入
#   [14]    显式 `< /dev/null` 非 tty 形态复跑 `-t`（isatty 短路分支）
# 形态说明：沙箱/CI 中 stdin 通常非 tty；上游 `-t` 使 doSelfTest=TRUE，在
# `isatty(0)` stdin 装载判定**之前**短路——这是判据设计点，不绕过。
#
# stdin 确定性（2026-09-25 CI 挂死返修）：上游 `psig-src/main.c` 有
#   if(!doSelfTest && (input == NULL || !isatty(0))) input = … LoadPrefs("stdin", …);
# 而 `LoadBatchFromFile()` 对 `stdin`/`-` 走 `while((c=fgetc(stream))!=EOF)` **读到 EOF 为止**。
# 于是只要调用方 stdin 是「非 tty 且永不到 EOF 的流」（CI worker 上 `bash test.sh`
# 的 stdin 是未关闭的管道/构建机 stdin），**文件输入面那一次调用就会永久阻塞**，
# 表现为 `== 文件/stdin 输入面 … ==` 标题后再无输出、4h 无输出超时被 kill。
# 处置：给**读 stdin 的文件输入调用**显式 `< /dev/null`（= tty / 设备侧原本的实际形态，
# 语义等价、结果不变，仅把 stdin 从「继承」改为「确定」）。stdin 输入面本身仍由下方
# 管道用例（自带 EOF 的管道）覆盖，不受影响。
set -u
n=0
ok()   { n=$((n+1)); echo "  [PASS $n] $*"; }
fail() { echo "  [FAIL] $*（已通过断言数=$n）"; exit 1; }

echo "== CLI 冒烟（补丁 0002） =="
out=$(psignifit --version 2>&1) || fail "psignifit --version rc!=0"
case "$out" in
  *"psignifit 2.5.6"*) ok "--version 输出 psignifit 2.5.6" ;;
  *) fail "--version 输出异常: $out" ;;
esac

out=$(psignifit --help 2>&1) || fail "psignifit --help rc!=0"
case "$out" in
  *"usage: "*) ok "--help rc=0 且打印 usage" ;;
  *) fail "--help 未打印 usage: $out" ;;
esac

echo "== 上游自检 psignifit -t（内嵌数据 + 4 金值） =="
st=$(psignifit -t 2>&1); rc=$?
[ "$rc" -eq 0 ] || fail "psignifit -t rc=$rc（应为 0）"
ok "psignifit -t rc=0（继承 stdin＝非 tty 形态，doSelfTest 在 isatty 判定前短路）"

case "$st" in
  *"engine version = 2.5.6"*) ok "自检报告 engine version = 2.5.6" ;;
  *) fail "版本行缺失" ;;
esac

case "$st" in
  *"fitted parameters : {a = 3.06836, b = 4.00961, g = 0.5, l = 3.09818e-07}"*)
      ok "拟合值逐字等于 4 金值 {3.06836, 4.00961, 0.5, 3.09818e-07}" ;;
  *) fail "拟合值不等于 4 金值" ;;
esac

case "$st" in
  *"should be : {a = 3.06836, b = 4.00961, g = 0.5, l = 3.09818e-07}"*)
      ok "上游基准（should be）行与 4 金值一致" ;;
  *) fail "should be 行缺失或不一致" ;;
esac

case "$st" in
  *"*** success! ***"*) ok "自检成功标记 *** success! ***" ;;
  *) fail "缺少成功标记" ;;
esac

if echo "$st" | grep -qE 'Warning: .* out'; then
  fail "存在超出 0.1% 容差的参数告警"
else
  ok "无超容差（0.1%）Warning（4 参数全部在容差内）"
fi

echo "== 文件/stdin 输入面（补丁 0001，aarch64 signed char） =="
d="${PWD}/psig-data.$$"
mkdir -p "$d" || fail "无法创建临时数据目录 $d"
trap 'rm -rf "$d"' EXIT
cat > "$d/dat" <<'DATA'
1.00000000	0.50000000	40
4.00000000	1.00000000	40
6.00000000	1.00000000	40
1.60000000	0.57500000	40
3.50000000	0.86700000	60
1.80000000	0.58600000	60
3.00000000	0.81700000	60
2.50000000	0.66700000	60
DATA
cat > "$d/prefs" <<'PREFS'
#shape			logistic
#n_intervals	2
#runs			999
PREFS
[ -s "$d/dat" ] && [ -s "$d/prefs" ] || fail "内联示例数据写入失败"

out=$(cd "$d" && psignifit dat prefs < /dev/null 2>&1); rc=$?
[ "$rc" -eq 0 ] || fail "文件输入面 rc=$rc（未打 0001 补丁时报 input stream is too big）"
ok "文件输入面 rc=0（aarch64 unsigned char 修复生效；stdin 已钉为 /dev/null，不继承调用方）"

case "$out" in
  *"fitting to original data"*) ok "输出含 fitting to original data" ;;
  *) fail "缺少 fitting 行" ;;
esac

case "$out" in
  *"#TH_EST"*) ok "输出含 #TH_EST 阈值矩阵" ;;
  *) fail "缺少 #TH_EST 输出" ;;
esac

lines=$(printf '%s\n' "$out" | wc -l)
[ "$lines" -ge 10 ] || fail "输出行数 $lines < 10，疑似空产出假绿"
ok "输出 $lines 行（≥10，非空产出）"

out=$(cd "$d" && printf '#random_seed 12345\n' | cat prefs - | psignifit dat - 2>&1); rc=$?
[ "$rc" -eq 0 ] || fail "管道输入面 rc=$rc"
case "$out" in
  *"#PA_EST"*) ok "管道输入面（Debian run-unit-test 同形）rc=0 且含 #PA_EST" ;;
  *) fail "管道输入面缺 #PA_EST" ;;
esac

echo "== isatty 短路形态（显式非 tty stdin） =="
if psignifit -t < /dev/null > /dev/null 2>&1; then
  ok "psignifit -t < /dev/null rc=0（isatty 短路分支同样通过）"
else
  fail "psignifit -t < /dev/null 非 0"
fi

echo "assertions=$n"
if [ "$n" -ne 14 ]; then
  echo "断言数 $n != 14（与 MANIFEST.yml assertion_count 不符）"
  exit 1
fi
echo "ALL PASS (14/14)"
