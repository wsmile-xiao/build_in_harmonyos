#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name ompl --version 1.6.0 --build-system cmake --cmake-toolchain conan --source-url https://github.com/ompl/ompl/archive/refs/tags/1.6.0.tar.gz --sha256 f03daa95d2bbf1c21e91a38786242c245f4740f16aa9e9adbf7c7e0236e3c625 --test-lang cpp --requires boost/1.90.0.3,eigen/3.4.0 --libs ompl,boost_serialization --pkgconfig-name ompl --cmake-def OMPL_BUILD_DEMOS=OFF --cmake-def OMPL_BUILD_TESTS=OFF --cmake-def OMPL_BUILD_PYBINDINGS=OFF --cmake-def OMPL_REGISTRATION=OFF --cmake-def 'EIGEN3_INCLUDE_DIR={eigen:includedir}' --cmake-def 'Boost_INCLUDE_DIR={boost:includedir}' --out <输出根目录>
