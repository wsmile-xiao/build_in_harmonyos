#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/kimwalisch/primecount/archive/refs/tags/v7.19.tar.gz --sha256 0ecb63282c02e3056707671b3d6c5bdb783b64a33c911f0fd4abe6e79e9f8a34 --name primecount --version 7.19 --build-system cmake --libs primecount --requires primesieve/12.13 --cmake-def 'BUILD_STATIC_LIBS={shared:OFF|ON}' --cmake-def 'BUILD_SHARED_LIBS={shared:ON|OFF}' --cmake-def BUILD_TESTS=OFF --cmake-def BUILD_LIBPRIMESIEVE=OFF --cmake-def BUILD_PRIMECOUNT=OFF --cmake-def WITH_POPCNT=OFF --cmake-def WITH_OPENMP=OFF --cmake-def CMAKE_NO_SYSTEM_FROM_IMPORTED=ON --test-header primecount.hpp --test-symbol primecount::pi --test-lang cpp --homepage https://github.com/kimwalisch/primecount --sign-so --out <输出根目录>
