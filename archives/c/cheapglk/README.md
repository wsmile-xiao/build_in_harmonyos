# CheapGlk

极简 Glk（Graphics Library Kit）实现，用于交互式小说/文字冒险游戏的文本界面。

## 简介

CheapGlk 是一个极其精简的 Glk API 实现，提供基本的窗口管理、文本输入/输出、菜单和事件处理功能。它是许多交互式小说引擎（如 Zoom、Gargoyle）的底层依赖。

## OHOS 适配

- 纯 Unix Makefile 工程，无 configure、无 CMake、无外部依赖
- Makefile 使用 `CC = cc` 默认值，交叉编译需通过 make 命令行参数覆盖为 OHOS 工具链
- `make -j1 CC="<clang>" AR="<llvm-ar>" RANLIB="<llvm-ranlib>" CFLAGS="--target=aarch64-linux-ohos --sysroot=<sysroot> -O2"`
- CheapGlk 自带 `main()` 函数，消费者程序不得再定义 `main`，应提供三个用户回调：`glk_main`、`glkunix_arguments`、`glkunix_startup_code`
- 仅生成静态库 `libcheapglk.a`，无 shared Makefile target

## 依赖

无外部依赖，纯 ANSI C 实现。

## 功能验证

```bash
# 通过消费者测试程序链接验证
find_package(cheapglk REQUIRED)
target_link_libraries(test cheapglk::cheapglk)
```

## 参考

- 上游仓库: https://github.com/erkyrath/cheapglk
- Glk 规范: https://www.eblong.com/glk/glk-spec-075.html
