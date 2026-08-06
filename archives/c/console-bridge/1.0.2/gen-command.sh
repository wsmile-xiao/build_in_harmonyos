#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name console-bridge --version 1.0.2 --build-system cmake --cmake-toolchain conan --source-url https://github.com/ros/console_bridge/archive/refs/tags/1.0.2.tar.gz --sha256 303a619c01a9e14a3c82eb9762b8a428ef5311a6d46353872ab9a904358be4a4 --test-lang cpp --libs console_bridge --pkgconfig-name console_bridge --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --out <输出根目录>
