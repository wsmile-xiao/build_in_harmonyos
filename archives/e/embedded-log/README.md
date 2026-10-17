# embedded-log

> 小巧漂亮的嵌入式日志库：彩色输出，可指定日志输出到串口、屏幕、FLASH 或通过 USB 输出到 PC。纯 C 语言实现，可用于 C51、ARM 等嵌入式设备。

## 简介

embedded-log 是 to9/embedded-log 的 HarmonyOS PC 适配版本（v1.0.1，MIT License）。
上游源码仅包含 `src/log.c` + `src/log.h` + `src/log_cfg.h` 三个文件，**没有任何构建系统**
（无 Makefile/configure/CMake），本适配以 `static-library` Conan 配方直接编译。

## OHOS 适配要点

- **零构建系统直接编译**：`clang -c -O2 -fPIC -std=c99` 编译 `log.c`，`llvm-ar rcs` 打包静态库 `libembedded-log.a`（`package_type = "static-library"`，绕开 Conan 2 的 `library` 类型 shared 选项契约）。
- **R33 合规取编译器**：`tools.build:compiler_executables:<key>` conf 子键在 OHOS 适配版 Conan 2.29.1 未注册（`ConanException`），配方 try/except 回退 PATH 上的 clang/llvm-ar。
- **平铺头文件安装**：`log.h` 以 `#include "log_cfg.h"` 相对包含，两个头文件平铺安装到同一 `include/` 目录；`LOG_ENABLE` 由上游 `log_cfg.h` 默认开启。
- **无上游测试**：上游 `tests/`、`tools/` 仅为空占位 readme.txt；消费者用例（test.c）与鸿蒙专项用例（test_ohos.c）由 test_package 自编提供，ctest 2/2 通过。

## 依赖

无第三方依赖（纯 libc：stdio/stdarg/string）。

## 参考

- 上游: https://github.com/to9/embedded-log （MIT License）
- 归档: archives/e/embedded-log/1.0.1/
