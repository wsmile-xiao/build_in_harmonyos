#!/bin/bash
# Pre-build script for libiphb
# Generate configure script from configure.ac

cd "$BUILD_SRC_DIR"
autoreconf -fiv

echo "Generated configure script successfully"