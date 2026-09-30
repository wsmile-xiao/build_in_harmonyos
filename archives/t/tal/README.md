# tal — HarmonyOS PC 适配说明

`tal`（trailer alignment）是一个文本过滤器：读入若干行文本，找出它们共同的结尾字符（"trailer"，例如 C 注释收尾 `*/`、宏定义续行的 `\`），并把这些结尾对齐到同一列。常用于修复"破损"的注释框、对齐长宏定义的续行符，也可作为 vim 过滤器使用（`vmap ,t !tal<CR>`）。

- 上游：https://thomasjensen.com/software/tal/（Thomas Jensen；1.9 为最终版本）
- 形态：单文件 ANSI C（`tal.c`）+ 手写 Makefile，无 configure
- 产物：`bin/tal`、`share/man/man1/tal.1`
- 依赖：无（仅 libc）
- 许可证：作者自拟许可（`LicenseRef-tal`，原文随包安装在 `licenses/LICENSE`）

## 功能概述

- 自动识别公共结尾并对齐；`-l`/`-f` 控制结尾长度，`-e` 显式指定结尾
- 填充字符（`-c`）、结束列（`-k`）、最大行宽（`-m`）、内边距（`-p`）、制表位（`-t`）、忽略大小写（`-i`）
- 读写 stdin/stdout，或 `tal [options] [infile [outfile]]`

## OHOS 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | 上游平台目标 `make linux` 带 `-ansi`：musl 在 `__STRICT_ANSI__` 下隐藏 `strdup`/`strcasecmp` 声明，隐式 `int` 声明截断 64 位指针，编译只有告警、运行即 SIGSEGV | 改用通用目标 `make tal` + clang 默认 C 方言，`-Werror=implicit-function-declaration` 防回归；无补丁 |
| 2 | `make` 不带目标且未设环境变量 `OS` 时退出 0 却不产出二进制 | 配方显式指定 `tal` 目标 |
| 3 | 平台目标硬编码 `CC=gcc` | 编译器取自 Conan `tools.build:compiler_executables`（R33） |
| 4 | x86 运行器无法启动动态链接的 OHOS 产物 | `-static-pie` 链接（保留 PIE/RELRO/BIND_NOW），真机原生、x86 经 `qemu-aarch64` 运行同一产物 |

## 测试

- 上游：无自动化测试（源码包无 tests 目录，Makefile 无 check/test 目标），0 个。
- test_package：`test_tal.sh` 共 15 条断言，其中 9 条是上游示例页的输入/输出金样逐字节比对。
- 鸿蒙特有测试：消费者用例 `tal_consumer`。流程为：用 tal 对齐生成的 X-macro 头文件（1202 行，其中一行 3000 列）→ OHOS 工具链编译依赖该头文件的程序 → 运行程序。OHOS musl 的 `LINE_MAX` 为 4096，长行不会被拆开；若换成 `LINE_MAX` 为 2048 的 tal 构建，消费者程序直接编译失败。

## 参考

- 主页：https://thomasjensen.com/software/tal/
- 示例：https://thomasjensen.com/software/tal/examples.html
