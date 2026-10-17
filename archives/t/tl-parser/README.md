# tl-parser

TL (Type Language) schema compiler, originally part of telegram-cli. It reads a
Telegram TL schema file and exports it as a serialized `.tlo` binary
(`TLS_SCHEMA_V2`), the format consumed by MTProto code generators and runtime
libraries. This package tracks the `vysheng/tl-parser` Git snapshot at commit
`1933e76f` (2021-01-07), the version pinned by upstream consumers such as
Telegram Desktop.

## 功能概述

- 解析 TL schema（类型 / 函数 / 构造子声明，多命名空间，内建类型）
- `-e <file>` 把串行化后的 schema 导出为 `.tlo` 文件
- 输出统计与调试信息（`-v`）、表达式转储（`-E`）

## OHOS 适配

- 纯 C99 / POSIX 实现，仅依赖 `libm`（MHMT 原生提供）；CMake 无 OHOS 平台
  模块，对 OHOS 构建设置 `CMAKE_SYSTEM_NAME=Linux` 即可原生以 clang 编译。
- 上游 CMakeLists.txt 未声明 install 规则，配方通过补丁增加
  `install(TARGETS tl-parser RUNTIME DESTINATION bin)`。
- tl-parser 在部分解析失败时仍返回退出码 0，因此消费者测试以校验 `.tlo`
  输出非空且含 `0x3a2f9be2`（TLS_SCHEMA_V2）魔数来确认真实执行。

## 依赖关系

- 编译依赖：无（仅 C 标准库 + `libm`）。
- 运行依赖：无。

## 参考资料

- 官网 / 源码：https://github.com/vysheng/tl-parser
- TL 语法：https://core.telegram.org/mtproto/TL-tl
