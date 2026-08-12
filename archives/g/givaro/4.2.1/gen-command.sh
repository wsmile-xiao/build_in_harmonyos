#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/linbox-team/givaro/releases/download/v4.2.1/givaro-4.2.1.tar.gz --sha256 feefb7445842ceb756f8bb13900d975b530551e488a2ae174bda7b636251de43 --name givaro --version 4.2.1 --build-system autotools --autotools-deps --libs givaro --pkgconfig-name givaro --requires gmp/6.3.0.1 --with-dep 'gmp:--with-gmp={includedir}/..' --homepage https://github.com/linbox-team/givaro --test-header givaro/givconfig.h --test-lang cpp --test-symbol '' --out <输出根目录>
