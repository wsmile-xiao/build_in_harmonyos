#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://mirrors.tuna.tsinghua.edu.cn/gnu/gmp/gmp-6.3.0.tar.xz --sha256 a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898 --name gmp --version 6.3.0.1 --build-system autotools --libs gmpxx,gmp --pkgconfig-name gmp --configure-extra=--enable-cxx --homepage https://gmplib.org --test-header gmpxx.h --test-lang cpp --test-symbol '' --out <输出根目录>
