#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name mpfi --version 1.5.2 --build-system autotools --source-url https://mirrors.mit.edu/sage/spkg/upstream/mpfi/mpfi-1.5.2.tar.bz2 --sha256 c04f52cb306824b91b6d6eacf4f675b91fdee47c30f14d5b346dbfcd2492d274 --libs mpfi --requires mpfr/4.2.2.1,gmp/6.3.0.1 --autotools-deps --pkgconfig-name mpfi --test-header mpfi.h --test-symbol mpfi_init --homepage https://gitlab.inria.fr/mpfi/mpfi --out <输出根目录>
