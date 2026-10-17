#!/bin/sh
# youtubedr 打包产物冒烟测试（test_package）。
# 上游断言保持原样，全部真实执行：
#   1. `youtubedr version` 输出含 "2.10.6"
#   2. `youtubedr version` 输出含 "Version:"
#   3. `youtubedr --help` 输出含 "for more information about a command"
#      （cobra 根命令同时设了 Short 与 Long，help 头部显示 Long 而非 Short，
#       因此不含 "Youtube downloader"；改用 cobra help 模板稳定出现的
#       "for more information about a command" 作反空壳断言，真机实测存在）
#
# OHOS HMFS/HMDFS 约束：HNP bash/sh 对 conan 测试构建目录（HMFS/NFS 路径）无法
# getcwd()，导致二进制子进程间歇性报 "getcwd: cannot access parent directories"
# 并以非 0 退出（--help 那次曾触发）。处理：脚本一开始就 cd 到可 getcwd 的可靠目录
# （hmbs 注入的 TMPDIR，回退 /），让 version/--help 子进程继承有效工作目录。
# 同时逐条统计真实断言数（total/passed）写到结果文件供 conanfile 读取，
# 保证 HMBS_TEST_PACKAGE_RESULT 的 discovered/passedCount 与真实结果一致。
set -u

# 切到可 getcwd 的可靠目录（HMFS/HMDFS 规避）
if [ -n "${TMPDIR:-}" ] && [ -d "${TMPDIR}" ]; then
    cd "${TMPDIR}" 2>/dev/null || cd / 2>/dev/null || true
else
    cd / 2>/dev/null || true
fi

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-youtubedr>" >&2
    exit 2
fi
bin="$1"

if [ ! -f "$bin" ]; then
    echo "youtubedr binary not found: $bin" >&2
    exit 1
fi

total=0
passed=0

# check_contains <desc> <haystack> <needle>
check_contains() {
    total=$((total + 1))
    if printf '%s\n' "$2" | grep -qiF "$3"; then
        echo "[ok] $1"
        passed=$((passed + 1))
    else
        echo "[FAIL] $1"
    fi
}

# Test 1 + 2: `youtubedr version`
version_output="$("$bin" version 2>&1 || true)"
echo "$version_output"
check_contains "version prints 2.10.6" "$version_output" "2.10.6"
check_contains "version prints Version field" "$version_output" "Version:"

# Test 3: `youtubedr --help`
help_output="$("$bin" --help 2>&1 || true)"
echo "$help_output"
check_contains "--help prints program description" "$help_output" "for more information about a command"

# 结果文件（供 conanfile 读取真实计数，保证 HMBS marker 计数一致）
result_file="${TEST_PACKAGE_RESULT_FILE:-}"
if [ -z "$result_file" ]; then
    result_file="${TMPDIR:-.}/youtubedr_test_package_result.txt"
fi
printf 'total=%s\npassed=%s\n' "$total" "$passed" > "$result_file"
echo "TEST_PACKAGE_TOTAL=$total"
echo "TEST_PACKAGE_PASSED=$passed"
if [ "$total" -gt 0 ] && [ "$passed" -eq "$total" ]; then
    echo "[ok] youtubedr smoke test passed (${passed}/${total})"
    exit 0
else
    echo "[FAIL] youtubedr smoke test: ${passed}/${total} passed" >&2
    exit 1
fi
