#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/linbox-team/fflas-ffpack/releases/download/v2.5.0/fflas-ffpack-2.5.0.tar.gz --sha256 dafb4c0835824d28e4f823748579be6e4c8889c9570c6ce9cce1e186c3ebbb23 --name fflas-ffpack --version 2.5.0 --build-system autotools --autotools-deps --libs '' --pkgconfig-name fflas-ffpack --requires gmp/6.3.0.1,givaro/4.2.1,gsl/2.8,openblas/0.3.34 --with-dep 'givaro:--with-givaro={includedir}/..' --with-dep 'openblas:--with-blas-libs=-L{libdir} -lopenblas' --homepage https://linbox-team.github.io/fflas-ffpack/ --header-only --test-header fflas-ffpack/fflas-ffpack.h --test-lang cpp --test-symbol '' --out <输出根目录>
