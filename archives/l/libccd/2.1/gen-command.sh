#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name libccd --version 2.1 --build-system cmake --cmake-toolchain conan --source-url https://github.com/danfis/libccd/archive/refs/tags/v2.1.tar.gz --sha256 542b6c47f522d581fbf39e51df32c7d1256ac0c626e7c2b41f1040d4b9d50d1e --libs ccd --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --cmake-def ENABLE_DOUBLE_PRECISION=ON --cmake-def BUILD_DOCUMENTATION=OFF --cmake-def BUILD_TESTING=OFF --pkgconfig-name ccd --test-lang c --homepage https://github.com/danfis/libccd --out <输出根目录>
