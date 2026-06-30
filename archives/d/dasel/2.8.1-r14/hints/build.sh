#!/bin/sh
# dasel build.sh — Go 项目构建脚本
# 用于 G0 干净构建验证

set -e

PREFIX="${1:-$HOME/usr/local}"

export CGO_ENABLED=1
export GOPROXY=https://goproxy.cn,direct
export TMPDIR=/data/storage/el2/base/cache
export PATH=$HOME/usr/local/go1263/bin:$PATH

# Build
go build -ldflags="-s -w -X github.com/tomwright/dasel/v2/internal.Version=2.8.1" -o dasel ./cmd/dasel/

# Install
mkdir -p "$PREFIX/bin"
cp dasel "$PREFIX/bin/dasel"

echo "Build complete: dasel installed to $PREFIX/bin/dasel"