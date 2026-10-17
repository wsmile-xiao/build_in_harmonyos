#!/bin/sh
# test_sord.sh — sord 库消费者验证脚本
#
# 验证 sordi 工具（sord 附带的 RDF 存储工具）可运行，能解析并输出
# 简单 N-Triples 数据，作为 sord 库可用的冒烟测试。
# 用法：test_sord.sh <sordi_path> <libdir>
set -euo pipefail

if [ $# -ne 2 ]; then
    echo "FAIL: 用法: test_sord.sh <sordi_path> <libdir>" >&2
    exit 1
fi
SORDI="$1"
LIBDIR="$2"

if [ ! -x "$SORDI" ]; then
    echo "FAIL: sordi binary not found/executable: $SORDI"
    exit 1
fi

# sordi 依赖 libsord-0.so.0/libserd-0.so.0/libzix-0.so.0，注入 lib 路径
export LD_LIBRARY_PATH="${LIBDIR}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

TMP_ERR=$(mktemp)
TMP_IN=$(mktemp)
TMP_OUT=$(mktemp)
trap 'rm -f "$TMP_ERR" "$TMP_IN" "$TMP_OUT"' EXIT

# 可执行性验证：sordi -h 打印 usage 并返回 0（sordi 仅接受 -h，--help
# 因 argv[1]=='-' 不匹配任何选项会报错）。失败时区分沙箱 EPERM 与真实
# 故障：仅 EPERM（Operation not permitted/Permission denied）时 SKIP
# exit 0，其余失败 FAIL exit 1（R9/R34 防伪造通过）
if ! "$SORDI" -h >/dev/null 2>"$TMP_ERR"; then
    if grep -qE "Operation not permitted|Permission denied" "$TMP_ERR"; then
        echo "SKIP: sordi 被沙箱拒绝执行（EPERM 环境限制），产物存在性已验证"
        exit 0
    fi
    echo "FAIL: sordi -h 执行失败（非沙箱限制）"
    cat "$TMP_ERR" >&2
    exit 1
fi

# 用合法 N-Triples 输入（完整 IRI，无需前缀声明）测试解析与序列化；
# 输出默认 N-Triples 格式 <s> <p> <o> .。
# 用文件输入而非管道：命令替换中的管道若被 pipefail 判失败
# （printf 端 SIGPIPE）会误报，文件输入更稳
TMP_IN=$(mktemp)
printf '<http://example.org/s> <http://example.org/p> <http://example.org/o> .\n' > "$TMP_IN"
if ! "$SORDI" "$TMP_IN" >"$TMP_OUT" 2>&1; then
    echo "FAIL: sordi 解析输入失败"
    cat "$TMP_OUT" >&2
    exit 1
fi
OUT="$(cat "$TMP_OUT")"

# 断言（R34 真实功能验证）：输出非空、不含错误特征、包含预期三元组
if [ -z "$OUT" ]; then
    echo "FAIL: sordi 输出为空"
    exit 1
fi
case "$OUT" in
    *error*|*Error*|*undefined*|*Undefined*|*syntax*)
        echo "FAIL: sordi 输出含错误特征: $OUT"
        exit 1
        ;;
    *http://example.org/s*)
        echo "PASS: sordi 解析/序列化 RDF 成功"
        ;;
    *)
        echo "FAIL: sordi 输出未包含预期三元组: $OUT"
        exit 1
        ;;
esac
exit 0
