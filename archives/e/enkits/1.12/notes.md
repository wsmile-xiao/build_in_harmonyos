# enkits 1.12 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++ (clang 15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
source .build-context-enkits-1.12
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DENKITS_INSTALL=ON -DENKITS_BUILD_EXAMPLES=OFF -DENKITS_BUILD_SHARED=OFF \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX -DCMAKE_BUILD_TYPE=Release
make -j2
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连下载超时 | 鸿蒙网络环境无法直连 github.com | 手动通过 ghfast.top 镜像下载 tarball 并预置到 `$TMPDIR/builds/`，init-build 检测到已存在则跳过下载 |
| 2 | init-build 误判构建系统为 autotools | URL 含 `archive/refs/tags`，启发式猜测命中 autotools | 手动将 conanfile.py 改写为 CMake 配方（conan.tools.cmake.CMake/CMakeToolchain/cmake_layout） |

## 源码修改

无补丁。enkiTS v1.12 已包含 `#include <initializer_list>`（src/TaskScheduler.h:25），
早期 xmake-repo 的 on_install patch 在本版本上游已合入，无需适配。

## 依赖版本

无外部依赖。仅需系统 pthreads 库（package_info.system_libs = ["pthread"]）。

## 验证结果

```bash
file $TEST_PREFIX/lib/libenkiTS.a
# libenkiTS.a: ar archive
llvm-objdump -f $TEST_PREFIX/lib/libenkiTS.a
# file format elf64-littleaarch64 / architecture: aarch64
ls $TEST_PREFIX/include/enkiTS/
# LockLessMultiReadPipe.h  TaskScheduler.h  TaskScheduler_c.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libenkiTS.a | ~68KB | 静态库 (aarch64 OHOS ELF, 含 C/C++ TaskScheduler) |
| include/enkiTS/*.h | 3 files | TaskScheduler.h, TaskScheduler_c.h, LockLessMultiReadPipe.h |

## 注意事项

- conanfile.py 的 cmake target 名为 `enkiTS::enkiTS`（上游 CMake target 为 enkiTS）。
- enkiTS 是 C++11 库，但提供 C 接口（TaskScheduler_c.h），test_package 用 C 调用 C API，
  需显式链接 `-lc++ -lpthread`（C++ 运行时）。
- conandata.yml URL 保持官方 github.com（R39），conan-verify/finish 会自动注入 ghfast.top 镜像 fallback。
---

**编译结束**: 2026-08-19 10:55
**最终状态**: built
