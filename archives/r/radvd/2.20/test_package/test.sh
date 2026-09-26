#!/data/service/hnp/bin/bash
# test_package/test.sh — radvd 2.20 消费者测试（在 conanrun 环境里执行，
# PATH 已含包内 bin/）。每条断言都调用被测包自己的二进制。
set -uo pipefail

# HMDFS：bash 信任逻辑 PWD 而非失败的 getcwd() 系统调用，先把它播种好。
PWD="$(pwd)"
export PWD

scratch="$(mktemp -d 2>/dev/null || echo ./tp-scratch)"
mkdir -p "$scratch"
trap 'rm -rf "$scratch"' EXIT

fail() { echo "FAIL: $*"; exit 1; }
pass() { echo "PASS: $*"; }

# ---- 断言 1：两个 sbin 可执行文件都在 PATH 里（G4/L0k 产物完整性）----
for prog in radvd radvdump; do
    command -v "$prog" >/dev/null 2>&1 || fail "$prog 未安装到 PATH"
done
pass "radvd 与 radvdump 均可定位"

# ---- 断言 2：radvd -v 报出被适配的版本号（证明构建绑定了 VERSION）----
ver_out="$(radvd -v 2>&1)" || true
case "$ver_out" in
    *2.20*) pass "radvd -v 报告版本 2.20：$(printf '%s' "$ver_out" | head -1)" ;;
    *)      fail "radvd -v 未包含 2.20，实际输出：$ver_out" ;;
esac

# ---- 断言 3：radvd -h 打印 usage（getopt_long 分支被编进去了）----
help_out="$(radvd -h 2>&1)" || true
printf '%s' "$help_out" | grep -q -- '--configtest' \
    || fail "radvd -h 缺少 --configtest，usage_str 未生效：$help_out"
printf '%s' "$help_out" | grep -q -- '--nodaemon' \
    || fail "radvd -h 缺少 --nodaemon"
pass "radvd -h usage 含 --configtest/--nodaemon（getopt_long 已编译）"

# ---- 断言 4：合法配置通过解析（-c 是 configtest；-t 是 chrootdir，别混）----
cat > "$scratch/good.conf" <<'CONF'
interface lo
{
    AdvSendAdvert on;
    MinRtrAdvInterval 30;
    MaxRtrAdvInterval 100;
    prefix 2001:db8:1234::/64
    {
        AdvOnLink on;
        AdvAutonomous on;
        AdvRouterAddr off;
    };
    RDNSS 2001:db8:1234::1
    {
    };
};
CONF
good_out="$(radvd -c -C "$scratch/good.conf" -l "$scratch/good.log" -m stderr 2>&1)"
good_rc=$?
if [ "$good_rc" -ne 0 ]; then
    echo "---- configtest(good) rc=$good_rc ----"
    printf '%s\n' "$good_out"
    fail "合法配置解析未通过（rc=$good_rc）；这是接口缺失还是解析器缺陷，见上方第一条错误"
fi
pass "合法配置通过解析（radvd -c 返回 0）"

# ---- 断言 5：非法配置必须被拒（反向断言，证明解析器真的在校验）----
cat > "$scratch/bad.conf" <<'CONF'
interface lo
{
    AdvSendAdvert maybe;
};
CONF
bad_out="$(radvd -c -C "$scratch/bad.conf" -l "$scratch/bad.log" -m stderr 2>&1)"
bad_rc=$?
if [ "$bad_rc" -eq 0 ]; then
    printf '%s\n' "$bad_out"
    fail "非法配置（AdvSendAdvert maybe）竟被接受，解析器校验未生效"
fi
pass "非法配置被拒（rc=$bad_rc，第一条错误见下）"
printf '%s\n' "$bad_out" | head -3

# ---- 断言 6：语法级错误（缺分号/未知指令）也要被拒 ----
cat > "$scratch/bad2.conf" <<'CONF'
interface lo
{
    NotARealDirective on;
};
CONF
bad2_out="$(radvd -c -C "$scratch/bad2.conf" -l "$scratch/bad2.log" -m stderr 2>&1)"
bad2_rc=$?
[ "$bad2_rc" -ne 0 ] || { printf '%s\n' "$bad2_out"; fail "未知指令被接受"; }
pass "未知指令被拒（rc=$bad2_rc）"

# ---- 断言 7：radvdump 的用法出口（第二个二进制可执行且带参数校验）----
dump_out="$(radvdump --nonsense-option-xyz 2>&1)"
dump_rc=$?
if [ "$dump_rc" -eq 0 ]; then
    printf '%s\n' "$dump_out"
    fail "radvdump 对未知长选项竟然返回 0"
fi
pass "radvdump 可执行且拒绝未知选项（rc=$dump_rc）"

echo "radvd 2.20 consumer test: all assertions passed"
