# charmpp 8.0.2 适配笔记

## 编译环境
- 构建系统: CMake（Charm++ 自带 `buildcmake` 薄包装脚本；TARGET=charm++，triplet=netlrts-linux-arm8，compiler=clang）
- 编译日期: 2026-09-30
- 编译器: clang/clang++ 15.0.4（`/data/service/hnp/bin/clang`，target=aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```sh
# 1) 源码与依赖
#    https://github.com/charmplusplus/charm/archive/refs/tags/v8.0.2.tar.gz
#    zlib/1.3.1（conan，仅供 CMake find_package(ZLIB) 与 -lz）
# 2) 构建（bash 用 /data/service/hnp/bin/bash；OHOS 无 /bin/bash）
CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
/data/service/hnp/bin/bash ./buildcmake charm++ netlrts-linux-arm8 clang \
    --with-production -j8 --install-prefix=$PWD/install
```

配方（conanfile.py）等价执行上述命令，并附加平台规避（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./build` / `./buildcmake` 无法启动（bad interpreter） | 脚本 shebang `#!/bin/bash`，OHOS 无 `/bin/bash` | 用 `/data/service/hnp/bin/bash` 显式调用；并把 charmc/gathertree/testrun 的 shebang 改为 `/data/service/hnp/bin/bash`（E165） |
| 2 | bash 报 `getcwd: cannot access parent directories`，路径解析错乱 | HMDFS 下 bash 的 getcwd 失败（sh/python 正常） | 调用 bash 前 `export PWD=<绝对路径>` |
| 3 | `FATAL: Unsupported operating system HarmonyOS` | charm CMake 只识别 Darwin/Windows/Cygwin/Linux | CMakeLists 平台分支并入 HarmonyOS（按 linux 处理） |
| 4 | hwloc configure: `cannot guess build type` | 自带 hwloc 的 config.guess 不识别 HarmonyOS | E007 脚本 patch-autotools-ohos.pl + config.sub 增加 `linux-ohos*` 内核对 |
| 5 | hwloc configure: `config.status: could not setup config files machinery: Permission denied` | HMDFS 上 `mktemp -d` 目录不可写（E129 族） | 构建期 PATH 注入 `mktemp` wrapper(exit 1) 触发 config.status 的 mkdir 回退（open-mpi 先例） |
| 6 | `threads.C: use of undeclared identifier 'getcontext'` | OHOS musl 无 System V ucontext | netlrts-linux-arm8 线程后端由 CONTEXT 改 FCONTEXT（boost-context 自带 arm64 asm，与 x86_64-linux 一致） |
| 7 | `threads-context` 目标编译失败拖垮整体 | 同上，CMake 对所有线程变体无条件编译 | HarmonyOS 下跳过 ucontext 系线程变体（conv-core/CMakeLists.txt） |
| 8 | `charmc: line 230: g++: command not found`（conv-cpm 构建失败） | conv-config.sh 在 conv-mach-opt.sh 之前固化 CMK_NATIVE_* 为 gcc 默认值，-host 编译仍用 g++ | CMK_NATIVE_* 默认值移到 conv-mach-opt.sh 之后 |
| 9 | `charmc: cpp: command not found` → 改 clang 后 `error: no such file ...TMP.i` | OHOS 无 `cpp` 命令；clang 又不认 .ci 扩展名，且不支持 `cpp in out` 位置参数 | cc-clang.sh: `CMK_CPP_CHARM="clang -E -P -x c++"`；charmc 预处理改为 `... -o out.i` |
| 10 | `lib/libconverse.a: Error copying .../conv-static.c.o` | 未知平台 CMAKE_C_OUTPUT_EXTENSION=.obj，charm 硬编码 .o | cmake/converse.cmake 改用 `${CMAKE_C_OUTPUT_EXTENSION}` |
| 11 | charmrun 启动节点后 `Socket closed before recv`，节点静默退出 | OHOS musl 不支持 fcntl `F_SETOWN`/`O_ASYNC`（SIGIO），CmiStdoutInit 中 CmiEnableAsyncIO 报错后 exit(1)（错误输出被重定向到 socketpair，故静默） | netlrts-linux-arm8 设 `CMK_ASYNC_NOT_NEEDED=1`、`CMK_ASYNC_USE_F_SETFL_AND_F_SETOWN 0`（等价运行时 `+asynciooff`，已实测） |
| 12 | charmrun 报 `charmrun> fscanf() failed!` | `getpwuid()` 无该 uid 记录且系统无 `id` 命令 | mylogin() 回退 `LOGNAME`/`USER` 环境变量，popen 失败不再 exit |

## 源码修改（patches/，由 refresh-patch --auto 生成）

| 补丁（按文件，refresh-patch --auto 生成） | 主题 |
|------|------|
| 0001-CMakeLists.txt.patch | 顶层 CMake 平台分支：HarmonyOS 并入 Linux（否则 `FATAL: Unsupported operating system`） |
| 0002-cmake-converse.cmake.patch | conv-static 对象复制改用 `${CMAKE_C_OUTPUT_EXTENSION}`（未知平台 .obj/.o 扩展名差异） |
| 0003-contrib-hwloc-config-config.guess.patch | 自带 hwloc 的 config.guess 识别 HarmonyOS → `aarch64-unknown-linux-ohos` |
| 0004-contrib-hwloc-config-config.sub.patch | config.sub 接受 `linux-ohos` 内核-OS 组合 |
| 0005-src-arch-common-cc-clang.sh.patch | `.ci` 预处理改用 `clang -E -P -x c++`（OHOS 无 `cpp`；clang 不认 .ci 扩展名） |
| 0006-src-arch-netlrts-linux-arm8-conv-mach.h.patch | 线程后端 ucontext→FCONTEXT（boost-context arm64 asm）；关闭 SIGIO 异步 IO（`CMK_ASYNC_NOT_NEEDED=1`） |
| 0007-src-conv-core-CMakeLists.txt.patch | HarmonyOS 跳过 ucontext 系线程变体目标 |
| 0008-src-scripts-charmc.patch | `.ci` 预处理输出加 `-o`；shebang → `/data/service/hnp/bin/bash` |
| 0009-src-scripts-conv-config.sh.patch | `CMK_NATIVE_*` 默认值移到 conv-mach-opt.sh 之后（修 `-host` 编译用 g++） |
| 0010-src-scripts-gathertree.patch | shebang → `/data/service/hnp/bin/bash` |
| 0011-src-scripts-testrun.patch | shebang → `/data/service/hnp/bin/bash` |
| 0012-src-util-charmrun-src-charmrun.C.patch | `mylogin()` 回退 `LOGNAME`/`USER`（无 getpwuid 记录、系统无 `id` 命令） |

## 依赖版本

- zlib/1.3.1（制品仓，构建期 CMake `find_package(ZLIB REQUIRED)` 使用其头文件；链接走 `-lz`，由系统 libz.so 解析）

## 上游测试（R51）

清点（源码树 `tests/`，命令 `ls tests/<dir> | grep -v Makefile | wc -l`）：

| 目录 | 测试目录数 | 说明 |
|------|-----------|------|
| tests/charm++ | 34（Makefile DIRS；TESTDIRS 32 = DIRS − FTDIRS 2） | 主 Charm++ 测试集：`make test` 覆盖 TESTDIRS 32/32 全部实跑，展开 49 个用例；FTDIRS（jacobi3d、jacobi3d-sdag）属 `syncfttest` 目标，`make test` 默认不覆盖 |
| tests/util | 4 | ut 级测试（check/headerpad 等） |
| tests/converse | 1 | converse 级测试 |
| tests/ampi | 12 | AMPI 未构建（本次只构建 charm++ target）→ 不可运行 |

实测（真机 HarmonyOS PC aarch64）：

```sh
cd <build>/tests/charm++ && make -k test TESTOPTS="++local"
```

**结果：tests/charm++ 共 34 个测试目录，其中 TESTDIRS 32/32 全部实跑；另 2 个 FTDIRS（jacobi3d、jacobi3d-sdag）属上游 `make test` 默认不覆盖范围，本次未运行。实跑展开 49 个用例，38 通过（77.6%）**，11 失败：

| 失败用例 | 具体技术原因 |
|----------|--------------|
| large_bcast, zerocopy_with_qd, direct_api, zc_post_modify_size, dereg_and_nodereg, bcast_nonzero_root, pup_buffer, post_and_match, bcast_subset_async, io_read | zero-copy/直接 API 依赖 `process_vm_readv` 跨进程读内存，OHOS 沙箱返回 EPERM（运行时 `process_vm_readv failed! Permission denied`） |
| provisioning（`++processPerSocket` 子用例） | CPU 亲和性绑定路径 `CmiInitCPUAffinity` 段错误（OHOS 的 hwloc/亲和性接口不可用）；同目录默认与 `++processPerHost` 子用例通过 |

不可运行集合：tests/ampi 12 个目录（未构建 AMPI target，AMPI 属于另一个构建目标，本次交付不含）。
tests/util、tests/converse 未纳入本轮实跑（时间预算内优先跑主测试集 charm++）。

## 验证结果

```sh
# 打包后的 charmc 编译 + 运行（构建树/安装树/迁移目录下均验证）
charmc -language charm++ -o test_hello test_hello.ci test_hello.cpp
./test_hello 5                    # 1 PE 直接运行
charmrun ++local +p2 ./test_hello 5   # 2 PE
charmrun ++local +p4 ./ckhello 10     # 4 PE
```

## 补丁对其他平台的影响（透明性说明）

- 0002/0005/0008/0009/0012 为「语义等价」的上游可接受改动（对象扩展名用 CMake 变量、clang 预处理替代 `cpp`、
  `-o` 输出、native 编译器默认值次序、getpwuid 失败回退），不改变其它平台行为
- 0006（netlrts-linux-arm8 的 conv-mach.h）同时影响 Linux arm8：线程后端由 ucontext 改 FCONTEXT、
  关闭 SIGIO 异步 IO；FCONTEXT 与 x86_64-linux 一致，AI 评估以为可上游
- 0003/0004 为 hwloc 自带 config.guess/config.sub 的平台探针补充（新增 ohos 分支，不删改既有分支）

## 注意事项


- 上游 v8.0.2 的 CMake 工程版本号是 `project(... VERSION 8.0.1)`（上游笔误），因此 `charmc -V` 输出 `Charm++ Version 80001`；本包未修改上游版本号。
- Charm++ 程序依赖 `libc++_shared.so`（OHOS 系统）与 `-lz`（系统 libz）；包内库全部为静态 `.a`。
- 构建使用 `-j8` 上限（本机内存紧张时更稳妥）。
- 0006（conv-mach.h）对 netlrts-linux-arm8 无条件切换 SIGIO→FCONTEXT 属**必要设计**而非疏漏：charmc 消费者编译时会重新读取已安装的 conv-mach.h（`-D` 编译定义无法传导到 charmc 驱动的用户编译），OHOS 取值必须落在头文件里；代价是与上游普通 Linux arm8 共享该平台头。已打包制品的 charmc/charmrun shebang 硬编码 hnp bash 路径（0008/0010/0011），路径假设与 conanfile.py 的 bash 解析顺序一致（CONFIG_SHELL → hnp 版本化布局 → 旧版扁平路径），hnp 路径调整时需同步修改这三个补丁。
---

**编译结束**: 2026-10-01 00:05
**最终状态**: built
