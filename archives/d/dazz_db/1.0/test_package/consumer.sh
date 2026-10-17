#!/bin/sh
# 消费者用例：dazz_db 1.0（consumer verification）
#
# 模拟业务上层组件/下游使用者：仅通过已安装包导出的公开 CLI 工具
# （<package_folder>/bin/ 下的可执行文件）完成一个完整的业务工作流——
# 合成读段 → 建库 → 查询统计 → 还原导出，并核对每个环节的可观察结果。
# 与上游测试（0 用例）、鸿蒙专项适配测试（test_package/test.sh）分别计数。
#
# usage: consumer.sh <bin-dir> <work-dir>

set -u

BIN=${1:-}
WORK=${2:-}

PASS=0
FAIL=0
chk() { if [ "$1" -eq 0 ]; then PASS=$((PASS + 1)); printf 'PASS  %s\n' "$2"; else FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$2"; fi; }
say() { printf '\n== %s\n' "$1"; }

if [ -z "$BIN" ] || [ -z "$WORK" ]; then
  echo "usage: consumer.sh <bin-dir> <work-dir>" >&2
  exit 2
fi
PATH="${BIN}:${PATH}"
export PATH
mkdir -p "$WORK" || exit 2
cd "$WORK" || exit 2
rm -rf ./* 2>/dev/null

########################################################################
say "1. 业务工作流：合成读段"
# 下游第一步：生成 0.005 Mbp 基因组 20x 覆盖的合成读段（公开 CLI simulator）
simulator 0.005 -c20. -r42 -Mmap.txt > G.fasta 2>sim.err
chk $? "simulator 生成合成读段 (公开 CLI)"
chk "$([ -s G.fasta ] && echo 0 || echo 1)" "读段 fasta 非空"

########################################################################
say "2. 业务工作流：建库"
fasta2DB -v G G.fasta > f2db.log 2>&1
chk $? "fasta2DB 建压缩库 (公开 CLI)"
chk "$([ -s G.db ] && [ -s .G.idx ] && [ -s .G.bps ] && echo 0 || echo 1)" \
    "G.db/.G.idx/.G.bps 三件套存在"

########################################################################
say "3. 业务工作流：查询统计"
DBstats -n G > stats.txt 2>&1
chk $? "DBstats 输出统计 (公开 CLI)"
DBshow G > show.txt 2>&1
chk $? "DBshow 导出读段 (公开 CLI)"

########################################################################
say "4. 业务工作流：还原导出"
cp G.fasta G.expected
printf 'stale\n' > G.fasta
DB2fasta G > db2f.log 2>&1
chk $? "DB2fasta 还原 fasta (公开 CLI)"
cmp -s G.expected G.fasta
chk $? "还原结果与源读段逐字节一致"

########################################################################
say "summary"
printf 'consumer case: PASS=%d FAIL=%d TOTAL=%d\n' "$PASS" "$FAIL" "$((PASS + FAIL))"
if [ "$FAIL" -ne 0 ]; then
  echo "RESULT: FAILED"
  exit 1
fi
echo "RESULT: OK"
exit 0