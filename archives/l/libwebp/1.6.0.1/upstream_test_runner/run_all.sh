#!/bin/sh
# 逐目标执行 12 个上游 fuzz 目标驱动:语料 = 全部种子文件。
# 任一目标崩溃/abort(非零退出)或无 PASS 行 = FAIL;汇总后按 fail 计数传播非零退出码,
# 供 build_run.sh / CI 门禁判红(契约:全绿才 exit 0)。
set -eu
cd "$(dirname "$0")"

SEEDS="seeds_bin/s_lossy_q75.webp seeds_bin/s_lossy_q100.webp seeds_bin/s_vp8l_lossless.webp seeds_bin/s_anim_3f.webp seeds_bin/s_tiny.webp seeds_bin/s_corrupt.bin seeds_bin/s_random.bin seeds_bin/s_trunc.webp seeds_bin/s_8x8.ppm"

pass=0
fail=0
for t in simple_api dec webp_info huffman imageio enc enc_dec \
         advanced_api animation_api animdecoder animencoder mux_demux; do
  bin="build/fuzz_$t"
  if [ ! -x "$bin" ]; then
    echo "BIN-MISSING $t"
    fail=$((fail + 1))
    continue
  fi
  if "$bin" $SEEDS > "log_$t.txt" 2>&1; then
    line=$(grep -h "PASS $t" "log_$t.txt" | tail -1)
    if [ -n "$line" ]; then
      echo "$line"
      pass=$((pass + 1))
    else
      echo "FAIL $t (exit 0 但无 PASS 行): $(tail -3 "log_$t.txt" | tr '\n' ' ')"
      fail=$((fail + 1))
    fi
  else
    code=$?
    echo "FAIL $t (exit $code): $(tail -3 "log_$t.txt" | tr '\n' ' ')"
    fail=$((fail + 1))
  fi
done

echo "=== SUMMARY pass=$pass fail=$fail ==="
if [ "$fail" -gt 0 ]; then
  exit 1
fi
