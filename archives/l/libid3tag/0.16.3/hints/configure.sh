#!/bin/sh
# Hints for libid3tag 0.16.3 - CMake project
# This wrapper replaces ./configure for CMake-based projects

# Create build directory
mkdir -p _build

# Run cmake configure
cmake -S . -B _build \
    -DCMAKE_INSTALL_PREFIX="${DEFAULT_PREFIX}" \
    -DBUILD_SHARED_LIBS=ON \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -DCMAKE_C_COMPILER=clang \
    -DCMAKE_CXX_COMPILER=clang++

# cmake configure succeeds (exit 0) if configuration was successful
exit 0
