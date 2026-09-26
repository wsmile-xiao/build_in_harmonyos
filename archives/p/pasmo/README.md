# pasmo

`pasmo` 是一个**便携式 Z80 交叉汇编器**，用标准 C++ 编写，可在多种平台轻松编译。输入 Z80 汇编源文件，输出多种机器码/镜像格式：原始二进制、Intel HEX、CP/M Plus PRL（RSX）、Spectrum +3DOS、TAP/TZX/CDT（Spectrum 与 Amstrad CPC 模拟器磁带镜像）、Amsdos（Amstrad CPC 磁盘）与 MSX（Basic BLOAD）等；自 0.5.0 起还能把 Z80 源码翻译为 8086 代码，产出 MS-DOS COM 或 CP/M 86 CMD 文件。广泛用于 ZX Spectrum / Amstrad CPC / MSX / CP/M 等 8 位复古计算场景。

上游为作者 [Julián Albo](https://pasmo.speccy.org/) 的项目站（GPL-2.0-or-later）。

## 功能概述

- 多格式输出：`--bin`（原始二进制）、`--hex`（Intel HEX）、`--prl`（CP/M Plus RSX）、`--cmd`（CP/M 86 CMD）、`--plus3dos`、`--tap`/`--tapbas`、`--tzx`/`--tzxbas`、`--cdt`/`--cdtbas`、`--amsdos`、`--msx`
- 8086 代码生成：`--86`（从 Z80 源码产出 .COM/.CMD 代码）
- 符号表与公开符号：第 3/4 参数、`--public`、`--name`
- 预处理与语法控制：`INCLUDE`/`INCBIN`、`-I` 搜索路径、`MACRO`/`REPT`/`IRP`、条件汇编、`--nocase`、`--bracket`、`--equ`、`--alocal`、`--w8080`
- 诊断控制：`--err`（错误改走 stdout）、详细/调试输出（`-v`、`-d`、`-1`）

## 依赖关系

- 编译依赖：无（标准 C++ + libc；上游为 autotools 发行包，自带 configure/Makefile.in）
- 运行依赖：无（单一可执行文件）
- Conan 依赖：无（`requirements()` 为空，W0 检查通过）

## OHOS 适配要点

- 上游发行包自带 Autoconf 2.60 生成的 `configure`；configure.ac 仅 `AC_PROG_CXX`（无 `AC_CANONICAL_HOST`），**无需 config.guess/config.sub**，直接以 Conan 工具链的 OHOS clang 执行 `configure && make`
- **单个可移植性补丁**（`patches/0001-configure.patch`）：config.status 以 `umask 077` 创建临时目录，在 HMDFS 上不可写（知识 E011）→ 改为 `umask 022`；无平台宏、无系统前缀注入（R8/PF5/PF6 合规）
- 上游 0.5.3 **无测试套件**：无 tests/ 目录、Makefile.am 无 TESTS/check_PROGRAMS、`make check` 为空目标执行 0 用例（清点证据见 [0.5.3/test_package/MANIFEST.yml](0.5.3/test_package/MANIFEST.yml)）；`build()` 仍执行 `make check` 作为零用例证据
- 消费者回归（R51 补全）：`test_package/test_pasmo.sh` 22 条断言，逐字节验证二进制/HEX/TAP/TZX/MSX/8086 输出与 +3DOS/Amsdos/CMD 容器、诊断与退出码，**22/22 通过**（详见 [0.5.3/reports/test-report.md](0.5.3/reports/test-report.md)）
- 上游 0.5.3 无 `--version/--help` 开关（无参数时打印版本横幅）；平台 CI L2 的 `--version/--help` 探测失败为**非阻塞告警**（L2_RESULT=skip）

## 参考资料

- 上游项目站：<https://pasmo.speccy.org/>
- 文档：<https://pasmo.speccy.org/pasmodoc.html>（随源码附 `pasmodoc.html` 与 `README`）

## 版本

- `0.5.3` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8）；1 个 configure 可移植性补丁；上游 0 用例（已清点）+ 消费者回归 22/22；见 [0.5.3/notes.md](0.5.3/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/pasmo` | Z80 交叉汇编器（arm64 ELF） |
| `licenses/COPYING` | 上游 GPL-2.0 许可证原文 |
