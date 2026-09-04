# binary_log 0.1.0 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-09-03
- 目标平台：HarmonyOS PC aarch64
- 编译器：clang/clang++ 15.0.4
- Conan：2.29.1
- 类型：C++20 header-only 库
- 状态：built（已完成设备验证，待 PR CI）

## 源码与校验

- 上游仓库：https://github.com/p-ranav/binary_log
- 上游 tag：v0.1.0
- tag commit：589c4e609c203d6fef275f16dbc43aae849b0bda
- 归档 SHA256：464c5452ba6061c3b0c5d195b82b8acee8317bfe64c9d56993abfd339fb188ed

## 编译步骤

1. 使用官方 `v0.1.0.tar.gz`，核对 SHA256。
2. CMake 配置：`-DBINARY_LOG_DEVELOPER_MODE=ON -DBUILD_TESTING=ON`。
3. 关闭 `BUILD_UNPACKER`、`BUILD_BENCHMARKS` 和 `BUILD_EXAMPLES`，仅构建库及上游测试。
4. 在 OHOS 配方的 `generate()` 中将 `CMAKE_SYSTEM_NAME` 映射为 `Linux`，并设置处理器为 `aarch64`。
5. `conan create` 中运行上游 `cmake.test()`，然后安装头文件和 CMake package config。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `init-build` 将项目 URL 误判为 Autotools | 初始化器按 URL 后缀推断，仓库实际为 CMake | 读取上游 `CMakeLists.txt` 后校正 manifest，并使用 CMake 配方模板 |
| 2 | OHOS CMake 提示 `Platform/HarmonyOS` 未知 | CMake 4.1.2 没有 `Platform/HarmonyOS.cmake` | 仅在 OHOS 生成阶段设置 `CMAKE_SYSTEM_NAME=Linux` 和 `CMAKE_SYSTEM_PROCESSOR=aarch64` |
| 3 | Conan profile 的 `compiler.cppstd=17` 拒绝配方 | `check_min_cppstd` 会把 profile 声明值当成硬门槛；上游 target 已通过 CMake 要求 C++20 | 移除配方级 `validate()` 硬校验，由上游 INTERFACE target 和消费者的 `cxx_std_20` 传递 C++20 要求 |
| 4 | `test_package` 找不到 `binary_log/binary_log.hpp` | 上游安装头文件实际位于 `include/binary_log/` 下，配方将 include 根声明为 `include` | 将 `cpp_info.includedirs` 修正为 `include/binary_log` |

## 源码修改

- 未修改上游源码，也未添加补丁。
- 仅新增 Conan 配方、消费者测试和归档元数据。

## 依赖版本

- Conan requires：无。
- 上游源码自带 doctest 2.3.5 头文件；未引入外部构建依赖。

## 验证结果

设备端执行：

```text
clang++ 正确分离 main/test translation units：通过
doctest test cases: 10 | 10 passed | 0 failed | 0 skipped
doctest assertions: 522 | 522 passed | 0 failed
CMake configure/build：通过
ctest：1/1 passed，100% tests passed
```

## 交付物

- `include/binary_log/**`：上游头文件及 CMake package config。
- 不产生库二进制文件，因此不创建 `commands.json`。

## 注意事项

- `binary_log` 要求消费者使用 C++20；配方的 CMake target 为 `binary_log::binary_log`。
- 上游库是同步、非线程安全 logger；这是上游设计约束，不是 OHOS 限制。
