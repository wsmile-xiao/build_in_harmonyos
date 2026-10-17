# units-cpp 2.3.4 适配笔记

## 编译环境
- 构建系统: CMake（上游）+ Conan 2.29.1
- 编译日期: 2026-09-17
- 编译器: OHOS clang 15（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 任务版本 `2.3.4` 对应上游 tag `v2.3.4`（`nholthaus/units`）。
- 源码：`https://codeload.github.com/nholthaus/units/tar.gz/refs/tags/v2.3.4`
  sha256 `e7c7d307408c30bfd30c094beea8d399907ffaf9ac4b08f4045c890f2e076049`。
- 库形态：单头文件 `include/units.h`，零依赖，要求 C++14。
- 注意：仓库内已有 `archives/u/units`（GNU units 2.22，application），与本包
  `units-cpp` 同名不同源，不构成重复适配。

## 打包步骤

header-only，仅复制头文件与许可证：

```
include/units.h
licenses/LICENSE
```

`package_info` 暴露 CMake 目标 `units::units`，`libs/libdirs/bindirs` 为空。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 拒绝配置 | 上游 `cmake_minimum_required(VERSION 3.2...3.5)`，CMake 4 移除 <3.5 兼容 | `generate()` 设 `CMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | locale 用例失败 | `UnitContainer.to_string_locale` 断言 `de_DE.utf8`/`en_US.utf8`，OHOS bionic 无 locale 数据（`setlocale` 返回 NULL） | 运行上游套件时按名称排除该用例 |
| 3 | `cout` 用例 SIGABRT | `UnitContainer.cout` 用 gtest `CaptureStdout`，其临时文件路径硬编码 `/tmp`；真机 `/tmp` 属 root 且普通用户只读 | 运行上游套件时按名称排除该用例（gtest 1.12.1 不支持 TMPDIR 重定向） |
| 4 | 上游测试依赖 | GoogleTest 1.12.1 | 上游以 `3rdParty/gtest/googletest-1.12.1.zip` 随源码分发，FetchContent 本地解压，无需联网 |

## 源码修改

无补丁（`patches/` 为空）。两处平台相关用例通过 `--gtest_filter` 排除，未改动上游源码。

## 依赖版本

无外部依赖。

## 验证结果

```bash
# 上游测试（build() 内，实测注册 188 项）
unitTests/unitLibTest --gtest_filter=-UnitContainer.to_string_locale:UnitContainer.cout
# -> 186/188 通过；2 项为平台环境差异（无 locale 数据、/tmp 只读）

# test_package（消费者视角）
ctest -R test_units
# -> units-cpp consumer test PASS (20 checks)
```

`conan create units-cpp/2.3.4` 退出码 0。

## 注意事项

- 若在具备 locale 数据且 `/tmp` 可写的平台构建，可去掉 `--gtest_filter` 以运行全部 188 项。
