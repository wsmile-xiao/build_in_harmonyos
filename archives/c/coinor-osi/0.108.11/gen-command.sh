#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name coinor-osi --version 0.108.11 --build-system autotools --source-url https://github.com/coin-or/Osi/archive/refs/tags/releases/0.108.11.tar.gz --sha256 1063b6a057e80222e2ede3ef0c73c0c54697e0fee1d913e2bef530310c13a670 --test-lang cpp --pc-cflags 'coinutils=-I${includedir}/coin' --requires coinutils/2.11.13,zlib/1.3.1 --libs Osi,OsiCommonTests --pkgconfig-name osi --pkgconfig-deps --out <输出根目录>
