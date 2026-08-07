#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name libnghttp2 --version 1.70.0 --build-system cmake --cmake-toolchain conan --source-url https://github.com/nghttp2/nghttp2/releases/download/v1.70.0/nghttp2-1.70.0.tar.xz --sha256 e05cb1388eaca3830aded4ccf20044b6e1ac1a61411dcca11b0437c4285c8bc2 --test-lang c --libs nghttp2 --pkgconfig-name libnghttp2 --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --cmake-def ENABLE_LIB_ONLY=ON --cmake-def ENABLE_DOC=OFF --cmake-def BUILD_TESTING=OFF --out <输出根目录>
