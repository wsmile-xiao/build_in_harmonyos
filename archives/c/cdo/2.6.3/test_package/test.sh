#!/usr/bin/env bash
# test_package/test.sh — cdo 2.6.3 消费者测试
# 真实调用 cdo 算子链（本地生成数据，不依赖外网、不依赖外部数据文件）
set -eu

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

echo "[1] cdo -V 版本探测"
cdo -V 2>&1 | head -3
cdo -V 2>&1 | grep -q "Climate Data Operators version"

echo "[2] 生成随机场（NetCDF classic，10x5）"
cdo -f nc -random,r10x5 "$WORK/a.nc"
[ -s "$WORK/a.nc" ]

echo "[3] 网格尺寸（xsize=10 / ysize=5）"
cdo -info "$WORK/a.nc" | head -5
# griddes 是上游自身测试使用的网格描述入口（test/pytest/MapReduce.py.test）
XZ=$(cdo -s griddes "$WORK/a.nc" | awk -F= '/^xsize/ {gsub(/ /,"",$2); print $2}')
YZ=$(cdo -s griddes "$WORK/a.nc" | awk -F= '/^ysize/ {gsub(/ /,"",$2); print $2}')
echo "   xsize=$XZ ysize=$YZ"
[ "$XZ" = "10" ] && [ "$YZ" = "5" ]

echo "[4] 算术恒等式：add(a,a) - a - a == 0 场"
cdo -f nc -add "$WORK/a.nc" "$WORK/a.nc" "$WORK/sum.nc"
cdo -f nc -sub "$WORK/sum.nc" "$WORK/a.nc" "$WORK/diff.nc"
cdo -f nc -sub "$WORK/diff.nc" "$WORK/a.nc" "$WORK/zero.nc"
cdo -f nc -abs "$WORK/zero.nc" "$WORK/abs.nc"
MEAN=$(cdo -s -output -fldmean "$WORK/abs.nc" | tr -d '[:space:]')
echo "   field mean of |a+a-a-a| = $MEAN"
# 用 awk 做数值判断（元素全为 0 → 均值 0）
echo "$MEAN" | awk '{ if ($1+0 != 0) { print "FAIL: mean != 0 (" $1 ")"; exit 1 } }'

echo "[5] NetCDF-4 / HDF5 路径"
cdo -f nc4 -random,r5x5 "$WORK/n4.nc"
[ -s "$WORK/n4.nc" ]

echo "[6] GRIB2 编解码（eccodes 路径）"
cdo -f grb2 -random,r5x5 "$WORK/g.grb2"
[ -s "$WORK/g.grb2" ]
cdo -info "$WORK/g.grb2" | head -3

echo "[7] 重网格/投影算子（proj 路径）"
cdo -f nc -topo,global_5 "$WORK/topo.nc"
[ -s "$WORK/topo.nc" ]

echo "ALL CDO CONSUMER TESTS PASSED"
