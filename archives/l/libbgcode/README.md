# libbgcode

Prusa Block & Binary G-code（二进制 G-code）读写/转换库：把传统 ASCII G-code 转为带分块结构、压缩、校验和的二进制格式，也可转回。

## 功能概述

三个 C++ API（头文件见 `include/LibBGCode/`）：
- **core**：二进制 G-code 基本定义与读取（文件头、block 遍历、CRC32 校验）
- **binarize**：写入二进制 G-code（含 MeatPack/Heatshrink 编码）
- **convert**：ascii 与 binary 双向转换（`from_ascii_to_binary` / `from_binary_to_ascii`）

## OHOS 适配

- 构建系统为 CMake（C++17），无平台相关代码，Linux/OHOS 同源构建。
- 依赖全部来自制品仓：boost（头文件）、zlib（静态）；heatshrink v0.4.1 与测试框架 Catch2 v3.8.1 随配方 vendor，不进外部依赖。
- 补丁仅做 CMake 目标名映射（0001），无平台宏，不改测试逻辑。
- bgcode 命令行工具默认不构建（library-only 配方）；如需 CLI 可另起版本开启 `LibBGCode_BUILD_CMD_TOOL`。
- 上游 Catch2 测试经 `catch_discover_tests` 注册为 8 个 ctest 条目，在 `conan create` 内真实运行。

## 依赖关系

- boost/1.90.0.4、zlib/1.3.1.1（编译依赖）
- heatshrink v0.4.1（随配方 vendor，静态内嵌；binarize 链 heatshrink::dynamic）
- Catch2 v3.8.1（仅上游测试，随配方 vendor，不进交付包）

## 参考资料

- 上游仓库：https://github.com/prusa3d/libbgcode
- 格式说明：上游 doc/specifications.md
- 构建说明：上游 doc/building.md
