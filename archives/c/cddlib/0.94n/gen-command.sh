#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/cddlib/cddlib/releases/download/0.94n/cddlib-0.94n.tar.gz --sha256 b87ee07ba2c1d0ab92a3e4eccacdf568f981a095a392e3b9efd7e7e4a9e125b1 --name cddlib --version 0.94n --build-system autotools --autotools-deps --libs cddgmp,cdd --pkgconfig-name cddlib --requires gmp/6.3.0 --homepage https://github.com/cddlib/cddlib --test-header cddlib/cdd.h --test-symbol dd_set_global_constants --out <输出根目录>
