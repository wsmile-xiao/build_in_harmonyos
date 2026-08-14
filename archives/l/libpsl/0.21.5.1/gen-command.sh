#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name libpsl --version 0.21.5.1 --build-system autotools --source-url https://github.com/rockdaboot/libpsl/releases/download/0.21.5/libpsl-0.21.5.tar.gz --sha256 1dcc9ceae8b128f3c0b3f654decd0e1e891afc6ff81098f227ef260449dae208 --test-lang c --requires libidn2/2.3.7.1,libunistring/1.0 --libs psl --pkgconfig-name libpsl --autotools-deps --configure-extra=--enable-runtime=libidn2 --configure-extra=--enable-builtin=libidn2 --configure-extra=--disable-gtk-doc --out <输出根目录>
