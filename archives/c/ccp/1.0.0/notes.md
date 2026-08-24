# ccp 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake（上游同时提供 Makefile 与 CMakeLists.txt；CMake 提供 install 规则，选 CMake）
- 编译日期: 2026-08-23
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
# 1. 解压源码（ccp-project/libccp tag v1.0）
# 2. conan create 走 CMake 构建：
#    cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake <src>
#    cmake --build . -- -j20
#    cmake --install . --prefix <pkg>
# 3. 产物：libccp.so + libccp_static.a + include/ccp/{ccp.h,types.h,ccp_error.h}
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 配方 | libccp 是纯 CMake/Makefile 项目，无 configure 脚本，init-build 按 URL 误判构建系统 | 改用 templates/conanfile-cmake.py.tmpl 重写 conanfile.py |
| 2 | 上游 unittest 中 ccp_invoke 返回 -96 (LIBCCP_PROG_IS_NULL) | test_package 消费者直接调用 ccp_invoke，但未先安装 program（invoke 依赖 program 状态） | test.c 改为调用无 program 依赖的 API：ccp_init/connection_start/lookup/set_impl/get_impl/write_ready_msg/free |
| 3 | W3 CI L5 soname gate：libccp.so 缺 DT_SONAME | OHOS 未被 CMake 识别（无 Platform/HarmonyOS 模块），CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 未定义，SOVERSION 属性被忽略 | conanfile.py generate() 注入 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,` 与 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`（参照 attica5 已验证模式）；补丁在 CMakeLists.txt 设置 VERSION/SOVERSION |
| 4 | test_ccp 运行时找不到 libccp.so | libccp.so 带 SONAME 后，动态加载器按 SONAME 解析，CTest 不加载 conanrun 环境 | test_package test() 显式注入 LD_LIBRARY_PATH=包 lib 目录后运行消费者二进制 |

## 源码修改

| 补丁 | 修改内容 |
|------|----------|
| patches/0001-CMakeLists.txt.patch | CMakeLists.txt 为 ccp 共享库添加 `set_target_properties(ccp PROPERTIES VERSION 1.0.0 SOVERSION 1)`（配合 generate() 注入的 SONAME 标志生成 DT_SONAME，满足 L5 soname gate） |

## 依赖版本

- 无外部依赖（纯 C，仅 libc；ccp_priv.h 引用 pthread 头文件，链接无需 -lpthread——未使用其符号）

## 验证结果

```bash
# 上游测试：make test（unittest）—— 8 个测试函数全部通过（8/8 = 100%）
#   test_init / test_basic / test_primitives / test_multievent /
#   test_fallthrough / test_read_implicit / test_update_fields / test_close
# test_package 消费者测试：test_ccp —— 1/1 通过（100%）
#   ccp_init / ccp_connection_start / ccp_connection_lookup /
#   ccp_set_impl / ccp_get_impl / write_ready_msg / ccp_connection_free / ccp_free
# W3 本地 CI 模拟：Pass rate 100% (1/1)，L0/L1/L4/L5 全通过，L2 skip（无 bin/）
```

## 交付物

| 文件 | 说明 |
|------|------|
| libccp.so / libccp_static.a | 共享/静态库（libccp.so 带 DT_SONAME=libccp.so） |
| include/ccp/{ccp.h,types.h,ccp_error.h} | 公共头文件 |
| lib/cmake/libccp/ | CMake package config（libccp::ccp / libccp::ccp_static） |

## 注意事项

- CMake 在 OHOS 平台未知，所有共享库构建都需要在 generate() 中注入 SONAME 标志（E092/E298 相关模式）
- 上游 `make` 同时构建 .so/.a/unittest；CMake 构建时 unittest 目标也会编译（test_package 不依赖它）
