#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name gf2x --version 1.3.0 --build-system autotools --source-url https://gitlab.inria.fr/gf2x/gf2x/uploads/c46b1047ba841c20d1225ae73ad6e4cd/gf2x-1.3.0.tar.gz --sha256 9472cd651972a1de38e3c4c47697a86e0ecf19d7d33454d4bc2a62bc85841b59 --libs gf2x --pkgconfig-name gf2x --test-header gf2x.h --test-symbol gf2x_mul --homepage https://gitlab.inria.fr/gf2x/gf2x --out <输出根目录>
