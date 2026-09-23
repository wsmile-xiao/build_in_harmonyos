# libstropt

libstropt 是一个小型 C 语言选项字符串解析库，支持分隔符、参数、引号、转义、注释和字符串重建。

## 功能概述

- 通过 `stropt()` 解析常见的逗号、分号、空白和换行分隔选项。
- 通过 `stroptx()` 自定义特性、分隔符及引号保留行为。
- 通过 `stropt2buf()` 和 `stropt2str()` 将标签与参数重建为选项字符串。

## OHOS 适配

- 使用 HarmonyOS PC aarch64 原生 Clang 15 和 CMake 构建共享库。
- 库源码仅依赖 C 标准库/POSIX libc，无第三方依赖；字符串重建改用可移植的有界内存写入，以兼容 OHOS musl。
- 修正上游 0.1.2 标签中 CMake 项目版本仍为 `0.0.1` 的元数据错误，使 SONAME 和 pkg-config 版本与发行版本一致。
- 消费者测试覆盖全部四个公开 API，并额外验证 OHOS aarch64/musl 上的解析和字符串重建行为。

## 依赖关系

- 编译依赖：CMake、Clang。
- 运行依赖：HarmonyOS libc。
- 第三方依赖：无。

## 参考资料

- 上游仓库：https://github.com/rd235/libstropt
- 上游版本：https://github.com/rd235/libstropt/releases/tag/0.1.2
