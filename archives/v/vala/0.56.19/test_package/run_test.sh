#!/bin/sh
# test_package/run_test.sh — vala 0.56.19 运行期 smoke 判定脚本
# （L0c 门禁要求 test_package/ 下有 .c/.cpp/.cc/.cxx/.sh/.py 测试源文件，
#   hello.vala 由 test() 用 valac 编译后调用本脚本运行判定）
#
# 职责（由 test_package/conanfile.py test() 调用，处于已注入 glib/libffi/pcre2
# LD_LIBRARY_PATH 与 PKG_CONFIG_PATH 的环境中）：
#   1. 执行 hello 二进制（valac 编译的 Vala 程序，真实链接 libglib-2.0）
#   2. 判定输出：
#        - 含 "Hello from vala 0.56.19" → 通过（exit 0）
#        - 其他输出 / 运行失败          → 失败（exit 1）
set -u
OUT="${1:-}"
OUT_LOG="${2:-}"

if [ -z "$OUT" ] || [ -z "$OUT_LOG" ]; then
    echo "ERROR: usage: run_test.sh <binary> <logfile>" >&2
    exit 1
fi
if [ ! -x "$OUT" ]; then
    echo "ERROR: hello binary missing: $OUT" >&2
    exit 1
fi

"$OUT" > "$OUT_LOG" 2>&1
rc=$?

# 校验 rc==0 且输出含预期串才算通过（AI 检视 P3：此前只 grep 未校验 rc，
# 非零退出也可能误判通过）
if [ "$rc" -eq 0 ] && grep -q "Hello from vala 0.56.19" "$OUT_LOG" 2>/dev/null; then
    echo "vala runtime smoke OK"
    exit 0
fi

echo "ERROR: hello run failed (rc=$rc) or output mismatch:" >&2
cat "$OUT_LOG" >&2
exit 1
