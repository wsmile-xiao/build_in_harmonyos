#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name spdlog --version 1.17.0 --build-system cmake --cmake-toolchain conan --source-url https://github.com/gabime/spdlog/archive/refs/tags/v1.17.0.tar.gz --sha256 d8862955c6d74e5846b3f580b1605d2428b11d97a410d86e2fb13e857cd3a744 --test-lang cpp --requires fmt/12.2.0 --libs spdlog --pkgconfig-name spdlog --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --cmake-def SPDLOG_FMT_EXTERNAL=ON --cmake-def SPDLOG_BUILD_EXAMPLE=OFF --cmake-def SPDLOG_BUILD_TESTS=OFF --define SPDLOG_FMT_EXTERNAL --define SPDLOG_COMPILED_LIB --out <输出根目录>
