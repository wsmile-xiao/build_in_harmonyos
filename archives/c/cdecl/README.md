# cdecl

cdecl 是一个 C/C++ 声明翻译器（C gibberish translator），可将英文描述翻译成 C
声明，也可反向将 C 声明翻译成英文，并支持类型转换（cast）与 C 预处理器宏展开。

## 功能概述

- `declare a as array 3 of int` → `int a[3];`（英文 → C）
- `explain int *p` → `declare p as pointer to integer`（C → 英文）
- 支持 C/C++、const/volatile、函数指针、类型转换、命名空间等
- 支持 C 预处理器宏的逐步展开与调试（`expand` 命令）

## OHOS 适配

- 构建系统为 autotools，release tarball 已含生成的 configure/parser/lexer
- config.guess 无法识别 HarmonyOS，configure 需强制指定 `--build=aarch64-unknown-linux-gnu`
- 可选依赖 readline（交互编辑）与 term-size（curses）已禁用，核心功能不受影响

## 依赖关系

- 无外部编译依赖
- 内置 gnulib 组件（lib/ 目录），静态链接

## 参考资料

- 官网: https://github.com/paul-j-lucas/cdecl
