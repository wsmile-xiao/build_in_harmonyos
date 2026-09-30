# openddl-parser

openddl-parser 是一个轻量级 C++ OpenDDL（Open Data Description Language）解析器库，
用于解析 OpenDDL / OGEX 格式文本并构建节点树。Assimp 使用它解析 OpenDDL 场景描述。

## 功能概述

- 解析 OpenDDL 结构（Metric / GeometryNode / Transform / FloatArray 等）并构建 DDLNode 树。
- 公开 API：`OpenDDLParser::parse` / `getRoot` / `getVersion`，`DDLNode` 节点遍历与属性读取。
- 静态库产物 `libopenddlparser.a` + 公开头文件 `include/openddlparser/`。

## HarmonyOS PC 适配

- 构建系统：CMake（上游官方 tag v0.5.2），无第三方依赖。
- 使用 HarmonyOS PC Clang 工具链构建 AArch64 静态库，配合 Conan ohos-aarch64 profile。
- 上游测试：`openddlparser_unittest` 125 个 gtest 用例全部通过（125/125）。
- 消费者验证：`consumer/consumer_openddl_parser.cpp` 与 `test_package/` 均通过；
  `test_ohos/` 专项验证（ELF64 AArch64 / musl / 无宿主路径泄漏 / 真实解析）通过。
- 注意：上游 v0.5.2 tag 源码内嵌 `Version` 字符串仍为 "0.4.0"（上游未同步），
  配方版本以官方 tag 为准，`getVersion()` 返回 0.4.0 属上游事实。

## 依赖关系

无第三方编译或运行依赖。

## 参考资料

- 上游仓库：https://github.com/kimkulling/openddl-parser
- 官方源码归档（tag v0.5.2）：https://github.com/kimkulling/openddl-parser/archive/refs/tags/v0.5.2.tar.gz
