#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/dimpase/autocliquer/releases/download/v1.23/cliquer-1.23.tar.gz --sha256 c1d7cc927b7efe76ff4f11e1f01bee473e37360fb54843b16b287e3ad161287b --name cliquer --version 1.23 --build-system autotools --libs cliquer --pkgconfig-name libcliquer --test-header cliquer/cliquer.h --test-symbol clique_unweighted_max_weight --test-lang c --homepage https://github.com/dimpase/autocliquer --sign-so --out <输出根目录>
