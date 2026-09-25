# libstxxl

STXXL 是超大数据集的外存标准模板库，提供外存容器与算法，在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 上游

https://github.com/stxxl/stxxl

## 许可证

BSL-1.0

## 特性

- 外存容器 `stxxl::vector`、`stxxl::sorter`、`stxxl::stack`、`stxxl::queue` 等
- 外存排序、扫描与流式算法
- CMake 构建，默认静态库，无外部依赖

## 版本信息

| 版本 | 状态 | 构建日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 1.4.1 | built | 2026-09-19 | cmake | 0 |

## 已知平台差异

- CMake 不识别 HarmonyOS，配方以 `CMAKE_SYSTEM_NAME=Linux` 兼容
- 上游测试含重型排序用例，真机执行时间较长
