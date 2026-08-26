#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name dlisio --version 1.0.4 --build-system cmake --source-url https://github.com/equinor/dlisio/archive/refs/tags/v1.0.4.tar.gz --sha256 78d5c0e23f4bf55e6cba36e6ab5038156d81cb9f6cb9d03b147b5be12aa7f0d0 --libs dlisio --requires fmt/7.1.3,layered-file-protocols/0.0.0.20260108,mpark-variant/1.4.0 --cmake-def BUILD_PYTHON=OFF --cmake-def BUILD_TESTING=OFF --cmake-def CMAKE_POSITION_INDEPENDENT_CODE=ON --homepage https://github.com/equinor/dlisio --test-header dlisio/dlis/types.h --test-lang cpp --out <输出根目录>
