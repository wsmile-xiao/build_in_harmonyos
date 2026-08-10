#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name gdbm --version 1.24 --build-system autotools --source-url https://ftpmirror.gnu.org/gnu/gdbm/gdbm-1.24.tar.gz --sha256 695e9827fdf763513f133910bc7e6cfdb9187943a4fec943e57449723d2b8dbf --test-lang c --libs gdbm --pkgconfig-name gdbm --configure-extra=--disable-libgdbm-compat --configure-extra=--without-readline --configure-extra=MAKEINFO=true --out <输出根目录>
