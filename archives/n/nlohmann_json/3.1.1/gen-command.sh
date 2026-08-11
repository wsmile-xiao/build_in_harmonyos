#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/nlohmann/json/archive/refs/tags/v3.1.1.tar.gz --sha256 9f3549824af3ca7e9707a2503959886362801fb4926b869789d6929098a79e47 --name nlohmann_json --version 3.1.1 --build-system cmake --libs '' --header-only --cmake-def JSON_BuildTests=OFF --cmake-def CMAKE_POLICY_VERSION_MINIMUM=3.5 --include-dirs include --test-header nlohmann/json.hpp --test-lang cpp --out <输出根目录>
