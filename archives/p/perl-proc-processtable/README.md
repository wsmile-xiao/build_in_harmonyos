# Proc::ProcessTable (perl-proc-processtable)

Perl XS 模块，通过 `/proc` 文件系统读取进程表信息，提供 PID、CPU 占用率、内存使用、命令行等进程属性查询功能。

## 功能概述

- 通过 `/proc` 读取进程列表和详细信息
- XS (C) 实现，性能优于纯 Perl 方案
- 提供 `Proc::ProcessTable` 面向对象接口和 `Proc::ProcessTable::Util` 工具函数
- 支持进程信号发送（SIGKILL 等）

## OHOS 适配

HarmonyOS (aarch64, musl libc) 平台适配要点：

1. **obstack 依赖**：musl libc 不提供 glibc 的 `obstack.h`，需从源码 `os/` 目录复制 bundled `obstack.c`/`obstack.h` 到根目录编译
2. **Makefile.PL 补丁**：移除 `-lobstack` 链接，改用 bundled obstack.c；修正 LDFROM 变量；添加 `-Ios` include 路径
3. **SELinux E046 限制**：XS 模块 `.so` 文件无法从 Conan cache 或用户目录加载（hmdfs context 不允许 dlopen），部署时需安装到系统 Perl 目录 `/data/service/hnp/perl.org/perl_5.42.0/lib/`（hnp_file context）
4. **Conan profile**：必须使用 `arch=armv8` 而非 `os.cpu.arch=armv8`（后者触发 settings 嵌套错误）

## 依赖关系

- **编译依赖**：Perl 5.x（含 ExtUtils::MakeMaker）
- **运行依赖**：Perl 5.x
- **无外部库依赖**（obstack 使用源码 bundled 版本）

## 参考资料

- 官网：https://metacpan.org/dist/Proc-ProcessTable
- 源码：https://cpan.metacpan.org/authors/id/J/JW/JWB/Proc-ProcessTable-0.637.tar.gz
- 许可证：Artistic-2.0

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.637](./0.637/) | published | 2026-06-26 |
