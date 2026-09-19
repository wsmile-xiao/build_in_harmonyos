# shhopt

shhopt 是一个小型 C 命令行选项解析库，支持传统短选项与 GNU 风格长选项，并可直接写入变量或调用回调函数。

## 功能概述

- 支持 flag、string、int、unsigned int、long 和 unsigned long 参数类型。
- 支持组合短选项、内联参数、`--long=value` 形式以及 `--` 扫描终止符。
- 解析后从 `argv` 中移除已消费的选项，仅保留位置参数。
- 可允许负数作为位置参数，并可替换默认的致命错误处理函数。

## OHOS 适配

- 使用 HarmonyOS PC aarch64 原生 Clang 15 和上游 Makefile 构建。
- 库源码仅依赖 C 标准库，无第三方依赖，HarmonyOS 上无需源码补丁。
- 消费者测试覆盖全部参数类型、回调、组合选项和参数保留行为，并额外验证 HarmonyOS aarch64 的 64 位整数边界。

## 依赖关系

- 编译依赖：Make、Clang。
- 运行依赖：HarmonyOS libc。
- 第三方依赖：无。

## 参考资料

- 上游主页：https://shh.thathost.com/pub-unix/
- 上游版本：https://shh.thathost.com/pub-unix/files/shhopt-1.1.7.tar.gz
