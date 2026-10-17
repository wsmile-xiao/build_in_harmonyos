#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://www.singular.uni-kl.de/ftp/pub/Math/Singular/SOURCES/4-4-1/singular-4.4.1.tar.gz --sha256 6a4fbaaed05b89c35bff3b1c5e124344a088097f81affe129c9ae619b282b49b --name singular --version 4.4.1 --build-system autotools --autotools-deps --libs Singular,polys,singular_resources,factory,omalloc --pkgconfig-name Singular --requires ntl/11.6.0,flint/3.2.2,readline/8.3,mpfr/4.2.2,cddlib/0.94m --force-requires gmp/6.3.0.1 --configure-extra=--disable-doc --configure-extra=--disable-polymake --configure-extra=--without-python --configure-extra=--disable-gfanlib --homepage https://www.singular.uni-kl.de --test-header singular/Singular/libsingular.h --test-lang cpp --test-symbol '' --out <输出根目录>
