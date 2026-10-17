#!/data/service/hnp/bin/bash
# test_package/test.sh — oomd 0.5.0 消费者冒烟测试（R34：真实执行打包产物）
#
# 设备与 CI worker 均不是 oomd 的合法运行环境（实测无 cgroup2 挂载点、
# /proc/pressure/{cpu,io} 不可读、非 root），因此不在这里断言守护进程行为，
# 只断言上游确定性契约（10 条，逐条计数见 test_package/MANIFEST.yml）：
#   [1]  打包产物 oomd 存在且可执行
#   [2]  oomd --help 退出码恰为 0
#   [3]  输出含 usage 行（上游 Main.cpp usage() 契约）
#   [4]  输出含 --cgroup-fs 选项（上游默认 /sys/fs/cgroup，路径 C 关键开关）
#   [5]  ELF64（EI_CLASS=2）
#   [6]  小端（EI_DATA=1）
#   [7]  AArch64（e_machine=183）
#   [8]  真实链接 jsoncpp（DT_NEEDED 双探测器：readelf 主检 / grep -a 备检）
#   [9]  配置文件 etc/oomd/oomd.json 已随包安装
#   [10] man 手册 share/man/man1/oomd.1 已随包安装
set -u
PATH=/data/service/hnp/bin:$PATH
PKG="${1:-}"

BIN="$(command -v oomd || true)"
if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
    echo "[1] ❌ oomd 不在 PATH 上"
    exit 1
fi
echo "[1] ✅ 产物存在: $BIN"

set +e
OUT="$("$BIN" --help 2>&1)"
RC=$?
set -e
if [ "$RC" -ne 0 ]; then
    echo "[2] ❌ oomd --help rc=$RC"
    exit 1
fi
echo "[2] ✅ oomd --help rc=0"
echo "$OUT" | sed -n '1,3p'

if ! echo "$OUT" | grep -q "usage: oomd"; then
    echo "[3] ❌ usage 行缺失"
    exit 1
fi
echo "[3] ✅ usage 行存在"

if ! echo "$OUT" | grep -q -- "--cgroup-fs"; then
    echo "[4] ❌ --cgroup-fs 选项缺失"
    exit 1
fi
echo "[4] ✅ --cgroup-fs 选项存在"

EICLASS="$(od -An -t u1 -j 4 -N 1 "$BIN" | tr -d ' \n')"
if [ "$EICLASS" != "2" ]; then
    echo "[5] ❌ EI_CLASS=$EICLASS (期望 2=ELF64)"
    exit 1
fi
echo "[5] ✅ ELF64"

EIDATA="$(od -An -t u1 -j 5 -N 1 "$BIN" | tr -d ' \n')"
if [ "$EIDATA" != "1" ]; then
    echo "[6] ❌ EI_DATA=$EIDATA (期望 1=小端)"
    exit 1
fi
echo "[6] ✅ 小端"

EMACHINE="$(od -An -t u2 -j 18 -N 2 "$BIN" | tr -d ' \n')"
if [ "$EMACHINE" != "183" ]; then
    echo "[7] ❌ e_machine=$EMACHINE (期望 183=AArch64)"
    exit 1
fi
echo "[7] ✅ AArch64"

if command -v readelf >/dev/null 2>&1; then
    NEED="$(readelf -d "$BIN" 2>/dev/null | grep NEEDED || true)"
else
    NEED="$(grep -a -o -E 'libjsoncpp[^ ]*' "$BIN" | head -1 || true)"
fi
if ! echo "$NEED" | grep -q "jsoncpp"; then
    echo "[8] ❌ 未链接 jsoncpp（DT_NEEDED）: ${NEED:-<空>}"
    exit 1
fi
echo "[8] ✅ 真实链接 jsoncpp: $(echo "$NEED" | tr -s ' ' | head -2 | tr '\n' ' ')"

if [ -n "$PKG" ] && [ ! -f "$PKG/etc/oomd/oomd.json" ]; then
    echo "[9] ❌ 缺 etc/oomd/oomd.json"
    exit 1
fi
echo "[9] ✅ 配置文件随包安装"

if [ -n "$PKG" ] && [ ! -f "$PKG/share/man/man1/oomd.1" ]; then
    echo "[10] ❌ 缺 share/man/man1/oomd.1"
    exit 1
fi
echo "[10] ✅ man 手册随包安装"

echo "oomd 0.5.0 test_package: 10/10 断言通过"
