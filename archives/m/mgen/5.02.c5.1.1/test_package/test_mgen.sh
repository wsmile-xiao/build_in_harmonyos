#!/usr/bin/env sh
# test_package/test_mgen.sh — 真实调用 mgen 二进制的消费者测试
# 由 test_package/conanfile.py 调用：sh test_mgen.sh <path-to-mgen> <path-to-mpmgr>
#
# mgen 是 NRL 网络流量发生器（CLI 工具，无库 API）。以下用例全部真实执行
# 打包产物，不发送任何网络流量、不依赖外部服务：
#   1. `mgen help` 能真实启动并产生输出（非空）
#   2. help 输出含版本横幅 "mgen: version 5.1.1"（fprintf 硬编码，确定性）
#   3. help 输出含用法 "input <scriptFile>"
#   4. help 输出含用法 "output <logFile>"
#   5. help 输出含用法 "convert <binaryLog>"
#   6. help 输出含用法 "interface <interfaceName>"
#   7. 同包的 mpmgr 二进制存在且可执行（ELF 检查在 conanfile.py 做）
#   8. 未知命令不会挂起：限时 15 秒内必须退出（防 dispatch 循环挂起）
#
# 不验证动态数据（时间戳/随机种子），只验证确定性文本与进程行为。
# 所有操作仅读写 test 自建临时目录，不触碰宿主机敏感路径。
#
# 每个用例独立计数，结束后输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记。
# 任一失败则退出码 1，避免静默通过。
set -u

if [ "$#" -ne 2 ]; then
    echo "usage: $0 <path-to-mgen> <path-to-mpmgr>" >&2
    exit 2
fi

mgen_bin="$1"
mpmgr_bin="$2"
PASS=0
FAIL=0

# 找一个可写临时目录
TMPROOT="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
WORKDIR=""
for cand in "$TMPROOT" "$HOME" "$PWD"; do
    [ -n "$cand" ] || continue
    try="$cand/mgentest-$$"
    if mkdir -p "$try" 2>/dev/null; then
        WORKDIR="$try"
        break
    fi
done
if [ -z "$WORKDIR" ]; then
    echo "[fail] cannot create writable work dir" >&2
    exit 1
fi
trap 'rm -rf "$WORKDIR"' EXIT

# ── 用例 1: `mgen help` 真实启动并产生输出 ──
echo "[case 1/8] mgen help produces output"
help_output="$("$mgen_bin" help 2>&1)"
if [ -n "$help_output" ]; then
    PASS=$((PASS + 1))
    echo "  [ok] help output non-empty"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] help output empty"
fi

# ── 用例 2: 版本横幅 ──
echo "[case 2/8] help contains version banner"
if printf '%s\n' "$help_output" | grep -F "mgen: version 5.1.1" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] found 'mgen: version 5.1.1'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] version banner missing"
fi

# ── 用例 3: input 用法 ──
echo "[case 3/8] help contains input usage"
if printf '%s\n' "$help_output" | grep -F "input <scriptFile>" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] found 'input <scriptFile>'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] input usage missing"
fi

# ── 用例 4: output 用法 ──
echo "[case 4/8] help contains output usage"
if printf '%s\n' "$help_output" | grep -F "output <logFile>" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] found 'output <logFile>'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] output usage missing"
fi

# ── 用例 5: convert 用法 ──
echo "[case 5/8] help contains convert usage"
if printf '%s\n' "$help_output" | grep -F "convert <binaryLog>" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] found 'convert <binaryLog>'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] convert usage missing"
fi

# ── 用例 6: interface 用法 ──
echo "[case 6/8] help contains interface usage"
if printf '%s\n' "$help_output" | grep -F "interface <interfaceName>" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] found 'interface <interfaceName>'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] interface usage missing"
fi

# ── 用例 7: mpmgr 二进制存在且可执行 ──
echo "[case 7/8] mpmgr binary exists and is executable"
if [ -x "$mpmgr_bin" ]; then
    PASS=$((PASS + 1))
    echo "  [ok] mpmgr executable: $mpmgr_bin"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] mpmgr not executable: $mpmgr_bin"
fi

# ── 用例 8: 未知命令限时退出（不挂起）──
echo "[case 8/8] unknown command terminates within 15s"
"$mgen_bin" nosuchcommand_xyz > "$WORKDIR/neg.log" 2>&1 &
neg_pid=$!
i=0
while kill -0 "$neg_pid" 2>/dev/null; do
    sleep 1
    i=$((i + 1))
    if [ "$i" -ge 15 ]; then
        break
    fi
done
if kill -0 "$neg_pid" 2>/dev/null; then
    kill "$neg_pid" 2>/dev/null
    wait "$neg_pid" 2>/dev/null
    FAIL=$((FAIL + 1))
    echo "  [fail] unknown command did not terminate within 15s (killed)"
else
    wait "$neg_pid" 2>/dev/null
    neg_rc=$?
    PASS=$((PASS + 1))
    echo "  [ok] unknown command terminated (rc=$neg_rc)"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test_mgen.sh <mgen-bin> <mpmgr-bin>\",\"discovered\":8,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
