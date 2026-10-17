#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name libidn2 --version 2.3.8 --build-system autotools --source-url https://ftpmirror.gnu.org/gnu/libidn/libidn2-2.3.8.tar.gz --sha256 f557911bf6171621e1f72ff35f5b1825bb35b52ed45325dcdee931e5d3c0787a --requires libunistring/1.0 --requires libiconv/1.17 --configure-extra=--disable-nls --configure-extra=--disable-doc --libs idn2 --out <输出根目录>
