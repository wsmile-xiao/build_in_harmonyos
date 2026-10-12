#!/bin/sh
# xsct 2.3 —— 消费者端到端用例（HarmonyOS PC）
#
# 用法: consumer_test.sh <bindir>
#
# 设计约束（CI 实证，PR #15143 build #80198）：加载验证不依赖 conan 宿主
# python3。HNP 安装的 python3（如 CI worker 的 /data/service/hnp/bin/python3）
# 运行在受限 linker namespace 中，对其 dlopen 缓存目录下的共享库会得到
# EACCES(Permission denied)；而 exec 时按 DT_NEEDED 加载不受此限。因此
# 「闭包真实加载」的证明全部由原生执行（B 节）承担，测试结果不随
# 「哪个 python3 运行 conan」而变化。
#
# 覆盖两部分（每一步都校验退出码，非 Python assert）：
#
#  A. HarmonyOS 专有非断言检查 —— 原生 ELF 与动态依赖闭包（静态）
#     A1 xsct 必须是 OHOS aarch64 原生 ELF 可执行文件
#     A2 xsct 的 DT_NEEDED 动态依赖闭包必须含 libX11.so.6 / libXrandr.so.2
#
#  B. 端到端消费者用例（原生进程真实执行 + 上游语义校验）
#     B1 无 DISPLAY 原生执行 xsct：动态加载器必须先完整解析并加载整个
#        DT_NEEDED 闭包（含传递依赖与重定位）才能进入 main()，随后运行到
#        X11 运行时路径并按上游源码语义优雅返回 EXIT_FAILURE(1)——这是
#        闭包在本机真实加载的直接证据（等价于逐库 dlopen 且覆盖面更强）
#     B2 伪造不可达 DISPLAY 执行 xsct：仍优雅失败（非信号终止 / 非加载失败）
#
# 参数: $1 = 被测包 bin 目录（含 xsct）
set -u

BINDIR="$1"
XSCT="$BINDIR/xsct"

[ -x "$XSCT" ] || { echo "FAIL: 缺少可执行文件 $XSCT" >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/xsct-consumer.XXXXXX" 2>/dev/null || mktemp -d 2>/dev/null) \
  || { echo "FAIL: mktemp" >&2; exit 1; }
trap 'rm -rf "$TMP" >/dev/null 2>&1 || true' EXIT INT TERM

fail() { echo "FAIL: $*" >&2; exit 1; }

# ─────────────────────────── A. HarmonyOS 专有检查 ───────────────────────────
echo "== A. HarmonyOS 专有非断言检查：原生 ELF 与动态闭包 =="

echo "+ readelf -h $XSCT"
readelf -h "$XSCT"
readelf -h "$XSCT" | grep -q 'ELF' || fail "A1: xsct 不是 ELF 可执行文件"
readelf -h "$XSCT" | grep -q 'AArch64' || fail "A1: xsct 不是 aarch64 原生 ELF"
echo "+ file $XSCT"
file "$XSCT" || true   # 仅作参考输出，不参与判定

echo "+ readelf -d $XSCT"
readelf -d "$XSCT"
readelf -d "$XSCT" | grep -q 'NEEDED' || fail "A2: xsct 无 DT_NEEDED 动态依赖闭包"
readelf -d "$XSCT" | grep -q 'libX11.so.6' || fail "A2: xsct 闭包缺 libX11.so.6"
readelf -d "$XSCT" | grep -q 'libXrandr.so.2' || fail "A2: xsct 闭包缺 libXrandr.so.2"

echo "+ DT_NEEDED 闭包清单"
readelf -d "$XSCT" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p' | sed 's/^/  /'

echo "OK A: xsct 为 aarch64 原生 ELF，DT_NEEDED 闭包声明完整（真实加载由 B 节原生执行强制校验）"

# ──────────────────────── B. 端到端消费者用例 ────────────────────────
echo "== B. 消费者端到端用例：真实执行 xsct（原生进程 + X11 运行时路径） =="

# B1: 无 DISPLAY 原生执行。上游 sct 2.3 main() 首行即 XOpenDisplay(NULL)，
#     加载器必须先完整解析并加载整个 DT_NEEDED 闭包（含传递依赖与重定位）
#     才能进入 main；无 DISPLAY 时上游按源码语义 perror("XOpenDisplay(NULL)
#     failed") + EXIT_FAILURE(1)。若动态闭包缺失/不可加载，加载器会以 127
#     退出并输出 shared library 错误。以退出码 + 错误流证据判定
#     「二进制真实运行且闭包完整可加载」。
( unset DISPLAY; "$XSCT" 6500 </dev/null >"$TMP/b1.out" 2>"$TMP/b1.err" )
rc=$?
echo "+ $XSCT 6500 (no DISPLAY) -> exit=$rc"
sed 's/^/    /' "$TMP/b1.err" 2>/dev/null || true
[ "$rc" -ne 127 ] || fail "B1: 动态加载器报告共享库缺失（exit=127）"
[ "$rc" -ne 126 ] || fail "B1: xsct 不可执行（exit=126）"
grep -q 'XOpenDisplay' "$TMP/b1.err" || fail "B1: 未见 X11 运行时路径证据（stderr 无 XOpenDisplay）"
grep -qi 'shared library' "$TMP/b1.err" && fail "B1: 存在共享库加载错误"
[ "$rc" -eq 1 ] || fail "B1: 期望上游 EXIT_FAILURE(1)，实际 exit=$rc"

# B2: 伪造不可达 DISPLAY，验证 xsct 仍优雅失败（非崩溃 / 非信号终止）
( DISPLAY=:9999; export DISPLAY; "$XSCT" 6500 </dev/null >"$TMP/b2.out" 2>"$TMP/b2.err" )
rc2=$?
echo "+ $XSCT 6500 (DISPLAY=:9999) -> exit=$rc2"
[ "$rc2" -lt 128 ] || fail "B2: xsct 因信号终止（exit=$rc2），未优雅失败"
grep -qi 'shared library' "$TMP/b2.err" && fail "B2: 存在共享库加载错误"

echo "OK B: xsct 真实执行，动态闭包经本机加载器完整解析加载，X11 运行时路径符合上游语义"
echo "ALL CONSUMER TESTS PASSED"
