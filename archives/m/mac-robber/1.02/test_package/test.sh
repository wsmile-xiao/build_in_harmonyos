#!/usr/bin/env sh
# test_package/test.sh — 真实调用 mac-robber 二进制的消费者测试
# 由 test_package/conanfile.py 调用：sh test.sh <path-to-mac-robber>
#
# 构造可审计文件树（普通文件/空文件/子目录/符号链接），真实执行 mac-robber
# 扫描该目录，验证输出 body-file 格式与核心功能：
#   1. CLI 能真实启动（扫描成功返回 0）
#   2. 输出包含创建的文件名
#   3. 识别目录（ls 串首字符为 'd'）
#   4. 符号链接：ls 串首字符为 'l' 且输出含 " -> " 与目标路径
#   5. -V 版本输出含 1.02
#   6. 不存在的目录返回非零
#   7. 输出结构：字段以 | 分隔，每行首字段为 0，第三字段为 0
#   8. 输出行数 = 文件数（不含 . 和 ..）
#
# 不验证动态数据（inode/时间戳/uid/gid），只验证结构与确定性内容。
# 所有操作仅在 test_package 自己创建的临时目录内，不扫描宿主机敏感目录。
#
# 每个用例独立计数，结束后输出 HMBS_TEST_PACKAGE_RESULT 机器证据标记。
# 任一失败则退出码 1，避免静默通过。
set -u

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-mac-robber>" >&2
    exit 2
fi

mrb_bin="$1"
PASS=0
FAIL=0

# 找一个可写临时目录构建审计文件树
TMPROOT="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
WORKDIR=""
for cand in "$TMPROOT" "$HOME" "$PWD" "$(dirname "$0")"; do
    [ -n "$cand" ] || continue
    try="$cand/mrbtest-$$"
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

# ── 构建可审计文件树 ──
# mac-robber 要求目录参数以 / 结尾，且递归扫描。
SCAN="$WORKDIR/scandir/"
mkdir -p "$SCAN" "$SCAN/subdir"
printf 'hello world\n' > "$SCAN/regular.txt"
: > "$SCAN/empty.txt"            # zero-byte file
ln -s regular.txt "$SCAN/link_to_regular" 2>/dev/null || true

# ── 用例 1: CLI 启动 + 扫描成功返回 0 ──
echo "[case 1/8] scan audit tree (return 0)"
output="$("$mrb_bin" "$SCAN" 2>&1)"
rc=$?
echo "  rc=$rc"
if [ "$rc" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] scan exited 0"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] scan exited $rc (expected 0)"
    echo "  output: $(printf '%s' "$output" | head -3 | tr '\n' ' ')"
fi

# ── 用例 2: 输出包含创建的文件名 ──
echo "[case 2/8] output contains created filenames"
if printf '%s\n' "$output" | grep -F "regular.txt" >/dev/null \
   && printf '%s\n' "$output" | grep -F "empty.txt" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] regular.txt and empty.txt present in output"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] expected filenames missing from output"
fi

# ── 用例 3: 识别目录（ls 串首字符 'd'）──
echo "[case 3/8] directory identified (mode 'd...')"
# subdir 行：0|<path>/subdir|0|d...
if printf '%s\n' "$output" | grep -E '0\|[^|]*subdir[^|]*\|0\|d' >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] subdir row has directory mode 'd'"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] subdir not identified as directory"
fi

# ── 用例 4: 符号链接（mode 'l' + ' -> ' + 目标）──
echo "[case 4/8] symlink identified (mode 'l' + ' -> target')"
if printf '%s\n' "$output" | grep -E '0\|[^|]*link_to_regular[^|]*\|0\|l' >/dev/null \
   && printf '%s\n' "$output" | grep -F "link_to_regular" \
      | grep -F " -> " >/dev/null \
   && printf '%s\n' "$output" | grep -F "link_to_regular" \
      | grep -F "regular.txt" >/dev/null; then
    PASS=$((PASS + 1))
    echo "  [ok] symlink row has 'l' mode, ' -> ' and target path"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] symlink not correctly identified"
    printf '%s\n' "$output" | grep -F "link_to_regular" | head -1 | sed 's/^/    /'
fi

# ── 用例 5: -V 版本输出含 1.02 ──
echo "[case 5/8] -V version contains 1.02"
ver_output="$("$mrb_bin" -V 2>&1)"
rc_v=$?
echo "  output: $(printf '%s' "$ver_output" | tr '\n' ' ')"
if printf '%s\n' "$ver_output" | grep -F "1.02" >/dev/null && [ "$rc_v" -eq 0 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] version contains 1.02"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] version output missing 1.02 (rc=$rc_v)"
fi

# ── 用例 6: 不存在的目录返回非零 ──
echo "[case 6/8] nonexistent directory returns non-zero"
"$mrb_bin" "$WORKDIR/does_not_exist_xyz/" >/dev/null 2>&1
rc_bad=$?
if [ "$rc_bad" -ne 0 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] nonexistent dir exited $rc_bad (non-zero)"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] nonexistent dir exited 0 (expected non-zero)"
fi

# ── 用例 7: 输出结构（字段以 | 分隔，每数据行首字段 0 第三字段 0）──
echo "[case 7/8] output body-file structure"
# Skip header lines (class|host|start_time, body|..., MD5|name|...).
# Data rows match: ^0|...|0|...  (first and third fields are 0)
data_rows=$(printf '%s\n' "$output" | grep -cE '^0\|[^|]*\|0\|')
if [ "$data_rows" -ge 4 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] $data_rows data rows with 0|<path>|0| structure"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] expected >=4 structured data rows, got $data_rows"
fi

# ── 用例 8: 输出数据行数 = 文件数（不含 . 和 ..）──
echo "[case 8/8] data row count matches file count"
# Created: regular.txt, empty.txt, link_to_regular, subdir (4 entries, no . or ..)
if [ "$data_rows" -eq 4 ]; then
    PASS=$((PASS + 1))
    echo "  [ok] exactly 4 data rows for 4 created entries"
else
    FAIL=$((FAIL + 1))
    echo "  [fail] expected 4 data rows, got $data_rows"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test.sh <mac-robber-bin>\",\"discovered\":8,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
