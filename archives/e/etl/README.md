# etl (Embedded Template Library)

ETL 是一个面向嵌入式应用的 C++ 模板库，提供与 C++ 标准库 API 兼容的容器、
算法和实用工具（如 `etl::vector`、`etl::string`、`etl::array`、`etl::variant`、
`etl::flat_map` 等），支持从 C++03 到 C++20 的多种标准，专为受限资源环境设计。

## 功能概述

- **容器**：`vector`、`deque`、`list`、`map`、`set`、`array`、`string`、`bitset`、`stack`、`queue` 等
- **算法**：`transform`、`for_each`、`sort`、`find`、`min`/`max`、`count` 等（对齐 STL 接口）
- **实用工具**：`variant`、`optional`、`expected`、`callback`、`delegate`、`timer`、`byte_stream`、`checksum`、`CRC` 等
- **头文件库**：全部实现位于 `include/etl/`，无编译产物，无动态链接

## OHOS 适配

- **构建系统**: CMake（官方以 `INTERFACE` 库提供，仅安装头文件）
- **适配方式**: header-only，无编译步骤。配方直接拷贝 `include/etl/` 与 LICENSE 到包内
- **平台差异**: 无。头文件为标准 C++，OHOS (aarch64 clang) 可直接包含使用
- **已知问题**: 无（本版本适配未发现阻塞项）

## 依赖

- 编译依赖: 无（纯头文件，仅需 C++ 编译器）
- 运行依赖: 无

## 参考资料

- 官网: https://www.etlcpp.com
- 源码: https://github.com/ETLCPP/etl
- 许可证: MIT
