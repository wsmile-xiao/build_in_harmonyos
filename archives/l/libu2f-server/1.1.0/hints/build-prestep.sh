#!/bin/bash
# G0 干净构建验证前置步骤
# 问题：tarball 缺少 configure 脚本，需要先运行 autoreconf

cd "$BUILD_SRC_DIR"
autoreconf --install
