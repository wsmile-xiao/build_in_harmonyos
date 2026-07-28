#!/data/service/hnp/bin/bash
# test_package/test.sh — iproute2 核心工具功能验证
#
# 覆盖两层：
#   1. 版本自检 (-V)：ip/tc/bridge/ss 可执行
#   2. netlink 实际通信：只读查询命令，验证工具能与 OHOS 内核网络栈交互
#      （RTM_GETLINK/GETADDR/GETROUTE/GETNEIGH、sock_diag 等），
#      这是 R40「系统底层：netlink」适配完整性的关键运行期证据。
#
# 说明：此处仅做只读查询，不做 add/set/del 等写操作（写操作需 root/CAP_NET_ADMIN，
# 会改动设备网络状态，应由人工在受控 aarch64 环境单独验证）。
# 在 conanrun env 下运行（PATH 含安装后的 bin/）。
set -u

pass=0
fail=0
out=/tmp/iproute2_test.out

run() {
    local desc="$1"; shift
    echo "[test] $desc :: $*"
    if "$@" >"$out" 2>&1; then
        echo "  OK"
        pass=$((pass + 1))
    else
        rc=$?
        echo "  FAILED (rc=$rc)"
        sed 's/^/     | /' "$out"
        fail=$((fail + 1))
    fi
}

echo "=== 1. 版本自检 (-V) ==="
run "ip 版本"     ip -V
run "tc 版本"     tc -V
run "bridge 版本" bridge -V
run "ss 版本"     ss -V

echo "=== 2. netlink 实际通信（只读查询，验证与内核网络栈交互） ==="
run "ip link show   (RTM_GETLINK)"  ip link show
run "ip addr show   (RTM_GETADDR)"  ip addr show
run "ip route show  (RTM_GETROUTE)" ip route show
run "ip -s link     (接口统计)"      ip -s link show
run "ip neigh show  (RTM_GETNEIGH)" ip neigh show
run "ip rule show"                  ip rule show
run "bridge link show"              bridge link show
run "tc qdisc show"                 tc qdisc show
run "ss -s          (sock_diag 汇总)" ss -s
run "ss -tan        (TCP 套接字枚举)" ss -tan

echo
echo "==== 结果: 通过 $pass, 失败 $fail ===="
if [ "$fail" -eq 0 ]; then
    echo "iproute2 版本 + netlink 功能验证全部通过"
    exit 0
else
    echo "存在失败项，需人工确认：netlink 只读查询失败通常意味着"
    echo "OHOS 内核 netlink 接口不可用，或适配存在缺陷。"
    exit 1
fi
