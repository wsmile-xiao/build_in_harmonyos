# entityx 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

entityx 使用 CMake 构建，是 C++11 ECS (Entity-Component-System) 库。
源码包含头文件 + 5 个 .cc 源文件 (System.cc, Event.cc, Entity.cc, help/Timer.cc, help/Pool.cc)。

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DENTITYX_BUILD_TESTING=OFF -DENTITYX_BUILD_SHARED=OFF \
  -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j2
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置报错 "Compatibility with CMake < 3.5 has been removed" | entityx CMakeLists.txt 使用 cmake_minimum_required(VERSION 3.1)，与 CMake 4.x 不兼容 | 补丁 0001: bump cmake_minimum_required 到 3.10 |
| 2 | 编译报错 'std::iterator' is deprecated [-Werror,-Wdeprecated-declarations] | entityx 用 -Werror 编译，profile 使用 cppstd=17，std::iterator 在 C++17 中被标记 deprecated | 补丁 0001: 移除 -Werror，添加 -Wno-error=deprecated-declarations |
| 3 | conan-init 误检测为 autotools | init-build 默认 BUILD_SYSTEM=autotools | 手动重写 conanfile.py 使用 conan.tools.cmake |

## 源码修改

补丁 0001-bump-cmake-min-version.patch 修改 CMakeLists.txt：
1. cmake_minimum_required(VERSION 3.1) → 3.10 (CMake 4.x 兼容)
2. 移除 -Werror，添加 -Wno-error=deprecated-declarations (C++17 std::iterator 兼容)

## 依赖版本

无外部依赖，纯 C++11 标准库。

## 验证结果

```bash
$ file $TEST_PREFIX/lib/libentityx.a
libentityx.a: ar archive
$ llvm-objdump -f libentityx.a
libentityx.a(System.cc.obj): file format elf64-littleaarch64
architecture: aarch64
$ ls $TEST_PREFIX/include/entityx/
3rdparty  Entity.h  Event.h  System.h  config.h  deps  entityx.h  help  quick.h  tags
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libentityx.a | 449KB | aarch64 OHOS 静态库 |
| include/entityx/*.h | - | ECS 头文件 (Entity.h, Event.h, System.h, etc.) |

## 注意事项

- entityx 默认构建 shared lib (ENTITYX_BUILD_SHARED=ON)，OHOS 平台需用 OFF 构建 static lib
- CMake 4.x 兼容性通过 CMAKE_POLICY_VERSION_MINIMUM=3.5 解决，不需要修改源码
- entityx 自动检测 -stdlib=libc++ 可用性（check_cxx_source_compiles），OHOS clang 支持
---

**编译结束**: 2026-08-19 12:16
**最终状态**: built
