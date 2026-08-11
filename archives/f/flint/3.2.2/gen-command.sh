#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --source-url https://github.com/flintlib/flint/releases/download/v3.2.2/flint-3.2.2.tar.gz --sha256 577d7729e4c2e79ca1e894ad2ce34bc73516a92f623d42562694817f888a17eb --name flint --version 3.2.2 --build-system autotools --libs flint --requires gmp/6.3.0,mpfr/4.2.2 --pkgconfig-name flint --include-dirs include --make-jobs 20 --with-dep 'gmp:--with-gmp-include={includedir}' --with-dep 'gmp:--with-gmp-lib={libdir}' --with-dep 'mpfr:--with-mpfr-include={includedir}' --with-dep 'mpfr:--with-mpfr-lib={libdir}' --configure-extra=flint_cv_check_cpu_set_t=no --test-header flint/flint.h --test-symbol flint_malloc --test-lang c --sign-so --out <输出根目录>
