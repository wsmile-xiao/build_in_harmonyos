# GNU Debugger (GDB)

GNU Debugger 是 GNU 项目开发的调试器，用于调试 C、C++、Go、Fortran 等多种编程语言编写的程序。

## 基本信息

- **官网**: https://www.gnu.org/software/gdb/
- **版本**: 14.1
- **许可**: GPL v3+

## 功能特性

- 支持多种编程语言的源码级调试
- 支持断点设置、单步执行、变量查看
- 支持远程调试（gdbserver）
- 支持核心转转分析

## 编译信息

| 项目 | 信息 |
|------|------|
| 编译日期 | 2026-05-28 |
| 编译器 | clang 15.0.4 |
| 构建系统 | autotools |
| 依赖 | gmp/6.3.0, mpfr/4.2.1, readline/8.2 |

## 平台适配说明

### HMDFS 临时文件限制

在 HarmonyOS HMDFS 文件系统上编译 autotools 项目需要特殊处理：

- **问题**: `(umask 077 && mktemp -d "./confXXXXXX")` 创建的目录无法写入文件
- **解决方案**: 将所有 configure 脚本中的 `umask 077` 改为 `umask 022`
- **参考**: `/storage/Users/currentUser/Documents/solve/hmdfs.txt`

### OHOS 平台识别

需要修改 `config.guess` 和 `config.sub` 添加 OHOS 支持：

- 使用 `patch-autotools-ohos.pl` 补丁脚本
- 添加 `linux-ohos*` 到 kernel-os 白名单

## 已编译版本

- 14.1 (2026-05-28)