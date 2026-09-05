# clipp

## 软件描述

clipp 是单头文件 C++11 命令行接口库（command line interfaces for modern C++），MIT 许可，作者 André Müller。全部功能位于 `include/clipp.h` 单个头文件中，无需链接任何库。

## 主要功能

- **选项解析**：`option()` 支持短/长选项、拼接 flags（如 `-abc`）、前缀/无前缀自由解析
- **值解析**：`value()`/`values()` 支持位置参数与重复值，内建常用类型转换（int/float/char/string 等）
- **分组**：`group` 支持嵌套、备选（alternative）、必填组（required）、阻塞（blocking）语义
- **回调**：action/call 机制在匹配时执行函数
- **自动帮助**：`make_man_page` 从定义生成 usage/帮助文本
- **错误处理**：未匹配参数、缺失必填项可自定义处理

## 库类型

**Header-Only Library**

- 无 `.so` / `.a` 二进制，仅 `include/clipp.h`
- 使用方式：`#include <clipp.h>`，无需链接

## 依赖关系

- **无外部依赖**
- 编译器要求：C++11 及以上
- 平台支持：已验证 OHOS aarch64（clang-15）、Linux 等

## 版本信息

- **版本**：1.2.3（2026-09-05 适配）
- **许可证**：MIT
- **项目地址**：https://github.com/muellan/clipp

## 鸿蒙适配状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 编译 | ✅ 成功 | header-only，clang++ 15.0.4 (aarch64-unknown-linux-ohos)，C++11 |
| 测试 | ✅ 38/39 | 上游 39 个独立测试可执行：38 通过；values_conversion_test 的 char '-128' 用例因 OHOS aarch64 默认无符号 char（AAPCS64）与上游有符号 char 假设不符，属平台 ABI 语义差异，非 clipp 缺陷，未修改上游测试 |
| 配方 | ✅ built | conanfile.py + conandata.yml + test_package（消费者测试 + HarmonyOS 专项测试） |
| 平台兼容 | ✅ 无问题 | 无平台特定代码；鸿蒙特有测试验证小端与 char 符号性 |

## 相关链接

- [官方仓库](https://github.com/muellan/clipp)
- [上游测试清单](1.2.3/test_package/MANIFEST.yml)
