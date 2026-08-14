#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name e2fsprogs --version 1.47.1 --build-system autotools --source-url https://github.com/tytso/e2fsprogs/archive/refs/tags/v1.47.1.tar.gz --sha256 db95ff1cb6ef741c9aa8875d9f3f52a34168360febba765b6377b80bada09a8c --test-lang c --libs ext2fs,com_err,e2p,ss --pkgconfig-name ext2fs --configure-extra=--disable-fsck --configure-extra=--disable-e2initrd-helper --configure-extra=--disable-nls --configure-extra=--enable-symlink-build --configure-extra=--enable-symlink-install --out <输出根目录>
