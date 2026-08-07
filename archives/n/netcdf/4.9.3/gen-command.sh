#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name netcdf --version 4.9.3 --build-system cmake --cmake-toolchain conan --source-url https://github.com/Unidata/netcdf-c/archive/refs/tags/v4.9.3.tar.gz --sha256 990f46d49525d6ab5dc4249f8684c6deeaf54de6fec63a187e9fb382cc0ffdff --test-lang c --requires hdf5/1.14.6,libaec/1.1.7,curl/8.15.0,zlib/1.3.1.1,zstd/1.5.7,libxml2/2.15.3.1 --libs netcdf --pkgconfig-name netcdf --inject-dep-includes --inject-dep-libdirs --cmake-def cache:CMAKE_POLICY_VERSION_MINIMUM=3.5 --cmake-def NETCDF_ENABLE_HDF5=ON --cmake-def NETCDF_ENABLE_EXAMPLES=OFF --cmake-def NETCDF_ENABLE_TESTS=OFF --cmake-def NETCDF_ENABLE_DAP_REMOTE_TESTS=OFF --out <输出根目录>
