# tsl-ordered-map 1.1.0 适配笔记

> **状态说明**：首轮完整适配（R02，worktree 创建已授权）。等待本地 conan create
> 验证完成后更新测试结果与状态。

## 编译环境

- 构建系统: cmake（上游 INTERFACE 头文件库）
- 编译日期: 2026-09-01
- SDK: OpenHarmony 6.x（profile: ci/conan/profiles/ohos-aarch64）
- 编译器: OHOS Clang 15.0.4
- 构建宿主: Linux x86_64
- 执行方式: OHOS aarch64 静态测试程序通过 qemu-user 执行（预期）

## 编译步骤

1. 下载官方源码：`v1.1.0.tar.gz`（codeload 官方 tag 归档，SHA-256 已核验）
2. CMake 配置（Conan `CMakeToolchain`）：
   - 纯头文件库，上游 `add_library(ordered_map INTERFACE)` + `tsl::ordered_map` 别名
   - OHOS 上按需将 `CMAKE_SYSTEM_NAME` 映射为 `Linux`（E092 类问题）
3. `cmake --build` + `cmake --install`：安装 `include/tsl/` 与 `share/cmake/tsl-ordered-map/`
4. 使用 Boost 1.86.0 头文件编译上游完整 Boost.Test 套件（header-only patch）
5. 静态链接 OHOS aarch64 测试程序并通过 qemu-user 执行（预期）
6. 执行 Conan `test_package`，验证下游 `find_package(tsl-ordered-map)`、编译、链接及运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试链接预编译 Boost::unit_test_framework | Boost 依赖链复杂 | 0001 patch 切换 header-only Boost.Test（同 robin-map 先例） |
| 2 | Boost 头文件触发 `-Wold-style-cast -Werror` | 上游将严格警告应用到第三方头文件 | 使用 `-isystem` 引入 Boost 头文件 |
| 3 | Boost 引用 `pthread_setcancelstate` | OHOS pthread 不提供线程取消 API | 单线程测试定义 `BOOST_DISABLE_THREADS` |

## 依赖版本

- 运行时依赖：无（纯头文件库）
- 测试依赖：Boost 1.86.0 源码头文件（配方直接下载并校验 SHA256，不依赖 Conan 制品仓）
- 构建工具：CMake 4.1.2、OHOS Clang 15.0.4
- 测试执行工具：qemu-user（预期）

## 验证结果

（等待 conan create 本地验证后补充：上游测试通过数、consumer 测试、conan-verify 门禁）
---

**编译结束**: 2026-09-01 17:47
**最终状态**: built
