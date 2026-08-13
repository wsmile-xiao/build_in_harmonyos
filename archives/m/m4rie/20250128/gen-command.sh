#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name m4rie --version 20250128 --build-system autotools --source-url https://github.com/malb/m4rie/releases/download/20250128/m4rie-20250128.tar.gz --sha256 96f1adafd50e6a0b51dc3aa1cb56cb6c1361ae7c10d97dc35c3fa70822a55bd7 --libs m4rie --requires m4ri/20260122 --autotools-deps --pkgconfig-name m4rie --test-header m4rie/m4rie.h --test-symbol mzed_init --homepage https://github.com/malb/m4rie --out <输出根目录>
