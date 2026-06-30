#!/bin/sh
# massdns cmake configure helper for G0 clean-verify
# This script wraps cmake configuration for the clean-verify process
set -e
mkdir -p build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$DEFAULT_PREFIX" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=bfd" \
  -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd"
