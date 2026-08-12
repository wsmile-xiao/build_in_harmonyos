#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/cddlib/cddlib/releases/download/0.94m/cddlib-0.94m.tar.gz --sha256 70dffdb3369b8704dc75428a1b3c42ab9047b81ce039f12f427e2eb2b1b0dee2 --name cddlib --version 0.94m --build-system autotools --autotools-deps --libs cddgmp,cdd --pkgconfig-name cddlib --requires gmp/6.3.0 --homepage https://github.com/cddlib/cddlib --test-header cddlib/cdd.h --test-symbol dd_set_global_constants --out <输出根目录>
