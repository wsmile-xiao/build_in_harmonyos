#!/bin/sh
# kraken2 轻量消费者冒烟测试（不运行 build_db）：
# build_db 构建最小索引库会 mmap 大块哈希表，在 OHOS 沙箱中挂起
# （14400s 无输出被 CI 超时杀掉，build #61715），故改为直接驱动
# 已打包的二进制：classify 帮助输出（exit 0）+ k2mask 对小型 FASTA
# 真实屏蔽处理（-i/-o 读写文件）。
set -eu

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/kraken2-test.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

# 1) classify: 打印 usage 并退出 0（getopt 无 'v' 选项，--version 会按
#    未知选项落到 usage(0)；用 -h 语义明确），验证二进制可运行
classify -h >/dev/null 2>&1

# 2) k2mask: 对小型 FASTA 做低复杂度屏蔽（-i 输入文件 -o 输出文件），
#    验证真实 API 调用与文件读写
printf '>s1\nACGTACGTACGTACGTACGTACGTACGTACGT\n' > "$WORK_DIR/mini.fa"
k2mask -i "$WORK_DIR/mini.fa" -o "$WORK_DIR/mini.masked.fa"
test -s "$WORK_DIR/mini.masked.fa"

echo "kraken2 smoke OK (classify usage + k2mask masking)"
