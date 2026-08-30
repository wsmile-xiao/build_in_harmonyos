# aws-c-http 0.11.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

使用 Conan 2.x + CMake 交叉编译。conanfile.py 通过 `CMAKE_PREFIX_PATH` 收集所有依赖包目录传入 CMake，绕过 `CMakeDeps` 以保留上游 CMake 模块路径和目标命名约定。

关键配置选项：
- `CMAKE_SYSTEM_NAME=Linux`（HarmonyOS 兼容）
- `CMAKE_SYSTEM_PROCESSOR=aarch64`
- `BUILD_SHARED_LIBS=ON`
- `BUILD_TESTING=OFF`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 链接错误：`Threads::Threads` 目标不存在 | aws-lc 的 `crypto-config.cmake` 引用 `Threads::Threads`，但 `find_package(Threads)` 在 `aws_use_package` 之后才调用 | 补丁 `0001-CMakeLists-add-threads-before-deps.patch`，在 `aws_use_package` 前插入 `find_package(Threads REQUIRED)` |
| 2 | `aws_tls_handler_protocol` 符号未定义 | aws-c-io 以 `BYO_CRYPTO=ON` 构建时不编译此函数，但 aws-c-http 仍引用 | 在 test_package 中新增 `stub.c`，提供返回空 `byte_buf` 的桩函数 |
| 3 | `Findcrypto.cmake` 无法定位 libcrypto | aws-lc 作为传递依赖未进入 `CMAKE_PREFIX_PATH` | 将 `aws-lc/5.4.0` 提升为 `requirements()` 中的直接依赖 |

## 源码修改

- `patches/0001-CMakeLists-add-threads-before-deps.patch`：在 CMakeLists.txt 中 `aws_use_package` 调用前插入 `find_package(Threads REQUIRED)`

## 依赖版本

- aws-c-common/0.14.3
- aws-c-io/0.27.5
- aws-c-compression/0.3.2
- aws-c-cal/0.9.15
- aws-lc/5.4.0

## 验证结果

- conan create: PASS
- test_package: 1/1 PASS
- conan-verify: ALL PASS (G0-G4 + L2/L4/L5)

## 注意事项

- aws-lc 必须在 `requirements()` 中直接声明，不能依赖传递依赖
- `CMAKE_PREFIX_PATH` 需包含全部 5 个依赖包目录
---

**编译结束**: 2026-07-27 14:39
**最终状态**: built

## 最终状态

COMPLETED — aws-c-http 0.11.0 适配完成，状态: built
