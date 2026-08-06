#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name fftw --version 3.3.10.2 --build-system cmake --cmake-toolchain conan --source-url https://www.fftw.org/fftw-3.3.10.tar.gz --sha256 56c932549852cddcfafdab3820b0200c7742675be92179e59e6215b340e26467 --test-lang c --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --cmake-def BUILD_TESTS=OFF --cmake-def ENABLE_THREADS=ON --cmake-def WITH_COMBINED_THREADS=OFF --cmake-def ENABLE_OPENMP=OFF --cmake-def ENABLE_FLOAT=OFF --cmake-def ENABLE_LONG_DOUBLE=OFF --libs fftw3,fftw3_threads --pkgconfig-name fftw3 --out <输出根目录>
