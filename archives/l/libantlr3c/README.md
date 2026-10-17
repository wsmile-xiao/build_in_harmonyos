# libantlr3c

## 简介

libantlr3c 是 ANTLR v3 的 C 语言运行时库（C runtime / target）。ANTLR 是
一套递归下降解析器生成器：开发者在构建机上用 ANTLR 工具（Java 实现）从
语法文件生成解析器骨架代码，运行时行为由目标语言的 runtime 库提供。
libantlr3c 是其中面向 C 的一支：字符/token 流、词法/语法分析基类、树构造、
ATN/DFA 驱动、错误处理等基础设施都在本库中实现。

生成的解析器代码只依赖本库的公开头（`antlr3.h` 等 30 个头文件 +
`antlr3config.h`），在目标设备上链接 `libantlr3c` 即可运行——Java 生成器
仅在开发机生成源码时使用，不是目标产物的运行依赖。

## 上游信息

- 官方仓库: https://github.com/antlr/antlr3
- 官方站点: https://www.antlr3.org/
- License: BSD-3-Clause（`runtime/C/COPYING`，Jim Idle / Temporal Wave LLC）
- 构建系统: Autotools（`runtime/C/configure.ac` + `Makefile.am`，
  上游 git tag 归档不含生成的 `configure`，需 `autoreconf -fi` 引导）

## 上游测试

上游 `runtime/C` 的 `Makefile.am` 未注册任何 `TESTS` / `check_PROGRAMS` /
自定义 check 目标：`make check` 只做依赖重编译检查，零测试注册
（与 libxext 1.3.7 零测试上游同模式）。上游仓库的 C runtime 部分没有
自带单元测试目录。消费者级验证见各版本 `test_package/`。

## OHOS 适配

见各版本目录 `notes.md` 与 `manifest.yaml`。

## 依赖

无第三方运行时依赖：仅 libc（memset/memmove/strdup 等）与可选的
sys/socket、netinet/tcp 头文件探测。

## 版本

| 版本 | 状态 |
|------|------|
| 3.5.3 | built（配方 + test_package 已验证，未上传制品仓） |
