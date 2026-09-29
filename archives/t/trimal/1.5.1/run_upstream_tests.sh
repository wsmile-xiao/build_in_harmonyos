#!/usr/bin/env bash
# 在鸿蒙 PC (aarch64) 上重现 trimAl 1.5.1 上游 dataset 回归套件（504 用例）。
# 自包含：下载官方 tar 包 -> 用 OHOS clang 构建三个二进制 -> 运行上游
# generate/compare 两个脚本，逐一比对 dataset/trimmed_msas/ 下的参考输出。
#
# 用法: bash run_upstream_tests.sh [工作目录]
#   环境变量: CXX（默认 clang++）、CONFIG_SHELL（默认 bash）
set -euo pipefail

URL="https://github.com/inab/trimal/archive/refs/tags/v1.5.1.tar.gz"
WORK="${1:-${TMPDIR:-$HOME/tmp}/trimal-upstream-suite}"
CXX_BIN="${CXX:-clang++}"
BASH_BIN="${CONFIG_SHELL:-bash}"

rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

echo "[1/4] download $URL"
curl -fsSL "$URL" -o trimal-1.5.1.tar.gz
sha256sum trimal-1.5.1.tar.gz

echo "[2/4] extract"
tar xzf trimal-1.5.1.tar.gz
cd trimal-1.5.1

echo "[3/4] build: make -C source CC=$CXX_BIN -j1"
make -C source CC="$CXX_BIN" -j1

echo "[4/4] upstream dataset regression (504 cases): generate + compare"
"$BASH_BIN" scripts/generate_trimmed_msas.sh
"$BASH_BIN" scripts/compare_trimmed_msas.sh
echo "PASS: upstream dataset regression 504/504"
