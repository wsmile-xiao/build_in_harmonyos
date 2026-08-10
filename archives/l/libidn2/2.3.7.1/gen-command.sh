#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name libidn2 --version 2.3.7.1 --build-system autotools --source-url https://mirrors.ustc.edu.cn/gnu/libidn/libidn2-2.3.7.tar.gz --sha256 4c21a791b610b9519b9d0e12b8097bf2f359b12f8dd92647611a929e6bfd7d64 --test-lang c --libs idn2 --pkgconfig-name libidn2 --configure-extra=--disable-doc --configure-extra=--disable-gtk-doc --configure-extra=--disable-valgrind-tests --out <输出根目录>
