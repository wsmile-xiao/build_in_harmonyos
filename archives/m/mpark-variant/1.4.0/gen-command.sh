#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name mpark-variant --version 1.4.0 --build-system cmake --source-url https://github.com/mpark/variant/archive/refs/tags/v1.4.0.tar.gz --sha256 8f6b28ab3640b5d76d5b6664dda7257a4405ce59179220431b8fd196c79b2ecb --header-only --homepage https://github.com/mpark/variant --test-header mpark/variant.hpp --test-lang cpp --out <输出根目录>
