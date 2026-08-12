#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/malb/m4ri/releases/download/20260122/m4ri-20260122.tar.gz --sha256 7e033ca1fd36be8861e2f67d9d124c398fc0d830209bb0226462485876346404 --name m4ri --version 20260122 --build-system autotools --autotools-deps --libs m4ri --pkgconfig-name m4ri --requires libpng/1.6.58 --homepage https://github.com/malb/m4ri --test-header m4ri/m4ri.h --test-symbol mzd_init --out <输出根目录>
