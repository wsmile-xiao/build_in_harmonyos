#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name fcl --version 0.7.0 --build-system cmake --cmake-toolchain conan --source-url https://github.com/flexible-collision-library/fcl/archive/refs/tags/0.7.0.tar.gz --sha256 90409e940b24045987506a6b239424a4222e2daf648c86dd146cbcb692ebdcbc --test-lang cpp --requires libccd/2.1,eigen/3.4.0,octomap/1.10.0 --cmake-def 'EIGEN3_INCLUDE_DIR={eigen:includedir}' --libs fcl --pkgconfig-name fcl --cmake-def BUILD_TESTING=OFF --cmake-def FCL_USE_X64_SSE=OFF --cmake-def FCL_USE_HOST_NATIVE_ARCH=OFF --out <输出根目录>
