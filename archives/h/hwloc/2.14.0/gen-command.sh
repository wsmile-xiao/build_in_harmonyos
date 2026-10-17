#!/bin/bash
set -euo pipefail
# 本 recipe 的生成命令（由 conan_packager.py gen 自动记录）。
#
# 重生成时**照这个改**，别凭 conanfile.py 反推参数：漏一个 flag 就静默少一项能力，
# 而且往往是构建装包全绿、下游才炸（graphviz 漏了 --post-install-cmd "bin/dot -c"，
# 插件索引 config8 不再生成，dlopen 全失效）。
#
# --out/--src 未记录（本地绝对路径），跑的时候自己补。
python3 <conan_packager.py 的路径> gen --name hwloc --version 2.14.0 --build-system autotools --test-lang c --pkgconfig-deps --libs hwloc --pkgconfig-name hwloc --probe-define 'HWLOC_MEMPOLICY_SYSCALL_UNUSABLE=syscall(__NR_get_mempolicy, 0, 0, 0, 0, 0);' --requires libxml2/2.15.3,cairo/1.18.4,zlib/1.3.1.1 --cli-tool '硬件拓扑查看与绑核工具集（lstopo 出拓扑图、hwloc-bind 把进程绑到指定核）' --homepage https://www.open-mpi.org/projects/hwloc/ --source-url https://download.open-mpi.org/release/hwloc/v2.14/hwloc-2.14.0.tar.gz --sha256 c4e473493cd5e75898bc72a8cbcd3cc722bfb271c9c8b9b4071fd21567835531 --configure-extra=--build=aarch64-unknown-linux-musl --configure-extra=--host=aarch64-unknown-linux-musl --configure-extra=--enable-libxml2 --configure-extra=--enable-cairo --configure-extra=--disable-cuda --configure-extra=--disable-nvml --configure-extra=--disable-gl --configure-extra=--disable-opencl --configure-extra=--without-x --configure-extra=--disable-doxygen --out <输出根目录>
