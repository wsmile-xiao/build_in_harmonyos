#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name orocos-kdl --version 1.5.1 --build-system cmake --cmake-toolchain conan --source-url https://github.com/orocos/orocos_kinematics_dynamics/archive/refs/tags/v1.5.1.tar.gz --sha256 5acb90acd82b10971717aca6c17874390762ecdaa3a8e4db04984ea1d4a2af9b --test-lang cpp --src-subdir orocos_kdl --requires eigen/3.4.0 --cmake-def 'EIGEN3_INCLUDE_DIR={eigen:includedir}' --libs orocos-kdl --pkgconfig-name orocos-kdl --out <输出根目录>
