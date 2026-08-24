#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name fmt --version 7.1.3 --build-system cmake --source-url https://github.com/fmtlib/fmt/archive/refs/tags/7.1.3.tar.gz --sha256 5cae7072042b3043e12d53d50ef404bbb76949dad1de368d7f993a15c8c05ecc --libs fmt --pkgconfig-name fmt --cmake-def FMT_TEST=OFF --cmake-def FMT_DOC=OFF --homepage https://github.com/fmtlib/fmt --test-header fmt/core.h --test-lang cpp --out <输出根目录>
