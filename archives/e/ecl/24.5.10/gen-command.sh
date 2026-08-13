#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://common-lisp.net/project/ecl/static/files/release/ecl-24.5.10.tgz --sha256 e4ea65bb1861e0e495386bfa8bc673bd014e96d3cf9d91e9038f91435cbe622b --name ecl --version 24.5.10 --build-system autotools --autotools-deps --src-subdir src --libs ecl --pkgconfig-name ecl --requires gmp/6.3.0.1,readline/8.3,gc/8.2.12,libffi/3.4.4 --homepage https://ecl.common-lisp.dev --test-header ecl/ecl.h --test-symbol cl_boot --out <输出根目录>
