#!/bin/sh
PREFIX="${PREFIX:-$HOME/usr/local}"
cd "$(dirname "$0")"
tar -xzf ngtcp2-1.22.1-ohos-aarch64.tar.gz -C "$PREFIX"
echo "ngtcp2 1.22.1 installed to $PREFIX"
