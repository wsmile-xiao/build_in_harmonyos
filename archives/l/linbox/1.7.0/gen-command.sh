#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/linbox-team/linbox/releases/download/v1.7.0/linbox-1.7.0.tar.gz --sha256 6d2159fd395be0298362dd37f6c696676237bc8e2757341fbc46520e3b466bcc --name linbox --version 1.7.0 --build-system autotools --autotools-deps --libs linbox --pkgconfig-name linbox --requires ntl/11.6.0,givaro/4.2.1,mpfr/4.2.2,flint/3.2.2,iml/1.0.5,fflas-ffpack/2.5.0,openblas/0.3.34 --force-requires gmp/6.3.0.1 --with-dep 'givaro:--with-givaro={includedir}/..' --with-dep 'ntl:--with-ntl={includedir}/..' --with-dep 'flint:--with-flint={includedir}/..' --with-dep 'iml:--with-iml={includedir}/..' --with-dep 'mpfr:--with-mpfr={includedir}/..' --with-dep 'fflas-ffpack:--with-fflas-ffpack={includedir}/..' --with-dep 'openblas:--with-blas-libs=-L{libdir} -lopenblas' --configure-extra=--disable-doc --homepage https://linbox-team.github.io/linbox/ --test-header linbox/linbox-config.h --test-lang cpp --test-symbol '' --out <输出根目录>
