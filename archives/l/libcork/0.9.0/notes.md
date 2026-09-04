# libcork 0.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang/clang++ (aarch64-linux-ohos, OHOS NDK 26.0.0.18)
- 状态: built

## 编译步骤

```bash
# conan create 配方构建（CORK_BUILD_TESTS=OFF，测试单独运行）
conan create archives/l/libcork/0.9.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 探索性构建（核验 OHOS 工具链下编译可行）
cmake -B build-explore -S . \
  -DCMAKE_TOOLCHAIN_FILE=$OHOS_NDK/build/cmake/ohos.toolchain.cmake \
  -DOHOS_ARCH=arm64-v8a -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 按 autotools 生成配方 | libcork 实际是 CMake 项目（conan-init 误判） | 按 templates/conanfile-cmake.py.tmpl 改写 conanfile.py，layout 用 cmake_layout |
| 2 | CMake 报 "Compatibility with CMake < 3.5 has been removed" | 上游 cmake_minimum_required(2.6) 过旧，本机 CMake 4.1.2 | generate() 设置 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | CMake 报 "Cannot determine version number" (exit 126) | version.sh shebang `#!/bin/bash` 在 /bin/bash 不存在时直接 126；且无 .git 时 git describe 失败 | patch 0001 改 `/usr/bin/env bash` + 引号修复；source() 写入 RELEASE-VERSION |
| 4 | 上游测试需 check 框架 | tests/CMakeLists.txt pkg_check_modules(CHECK REQUIRED check) | patch 0002 增加 CORK_BUILD_TESTS 选项，包构建 OFF；测试单独在 worktree 构建运行 |
| 5 | libcork 库类型硬编码 SHARED | add_library(libcork SHARED) 无视 Conan shared 选项 | patch 0003 改为 `add_library(libcork ${LIBCORK_SRC})` 由 BUILD_SHARED_LIBS 控制 |

## 源码修改

- patches/0001-version.sh.patch — shebang + 引号 + git describe 失败回退
- patches/0002-CMakeLists-tests-option.patch — CORK_BUILD_TESTS 选项
- patches/0003-src-CMakeLists-shared-libs.patch — BUILD_SHARED_LIBS 控制库类型

## 依赖版本

- 无运行依赖；上游测试需要 check/0.15.2（制品仓已发布，用于独立测试构建）

## 验证结果

```bash
# 见最终 result：bootstrap/source/adaptation 三段日志 + conan create + 上游测试台账
```

## 交付物

- libcork 库（libcork.a / libcork.so）与头文件、libcork.pc、cork-hash 工具

## 注意事项

- version.sh 依赖 RELEASE-VERSION 回退文件，配方 source() 必须生成，否则 configure 直接 FATAL
- 上游测试全部依赖 check 框架；OHOS 包构建关闭测试，测试统计以独立枚举/运行为准
---

**编译结束**: 2026-09-03 02:14
**最终状态**: built
