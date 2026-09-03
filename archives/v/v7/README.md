# v7

v7 是一个用 C 编写的嵌入式 JavaScript 引擎，同时提供静态库和命令行解释器。

## 功能概述

- 在嵌入式 C 程序中执行 JavaScript。
- 提供 `v7.h` 公共 API、`libv7.a` 静态库和 `v7` 命令行程序。

## OHOS 适配

- 使用上游 raw Makefile，并从 Conan 配置读取 OHOS Clang、`llvm-ar` 和 `llvm-ranlib`。
- 上游测试通过已有的 `CFLAGS_EXTRA` 入口加入 `V7_FILENAMES_SUPPRESS_CFUNC_ADDR`，不修改测试源码。
- 设备端 Conan、上游测试和消费者验证因当前 SSH 认证失败尚未执行。

## 依赖关系

- Conan 生产依赖：无；链接时使用系统数学库 `libm`。
- 软件级 `commands.json` 声明 `v7` 命令行工具。

## 参考资料

- 上游仓库：https://github.com/cesanta/v7
