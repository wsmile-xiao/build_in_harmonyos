#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name layered-file-protocols --version 0.0.0.20260108 --build-system cmake --source-url https://github.com/equinor/layered-file-protocols/archive/da9234fb3ce28d50e701f29d23edcb62c32b106b.tar.gz --sha256 b40dc183f7ef1273669efa7a14949932675cb42516173083e0ae3e3a449274e9 --libs lfp --requires fmt/7.1.3 --cmake-def LFP_FMT_HEADER_ONLY=ON --cmake-def BUILD_TESTING=OFF --cmake-def CMAKE_POSITION_INDEPENDENT_CODE=ON --homepage https://github.com/equinor/layered-file-protocols --test-header lfp/lfp.h --test-lang c --out <输出根目录>
