#!/bin/bash
# flatcc cmake clean-verify hint
# This project uses cmake, not autotools

mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DFLATCC_ALLOW_WERROR=OFF \
  -DFLATCC_INSTALL=ON
make -j2
make install DESTDIR=$TEST_PREFIX
