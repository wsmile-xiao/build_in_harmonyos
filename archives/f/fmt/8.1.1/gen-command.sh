#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name fmt --version 8.1.1 --build-system cmake --cmake-toolchain conan --source-url https://github.com/fmtlib/fmt/archive/refs/tags/8.1.1.tar.gz --sha256 3d794d3cf67633b34b2771eb9f073bde87e846e0d395d254df7b211ef1ec7346 --test-lang cpp --libs fmt --pkgconfig-name fmt --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --cmake-def FMT_TEST=OFF --cmake-def FMT_DOC=OFF --out <输出根目录>
