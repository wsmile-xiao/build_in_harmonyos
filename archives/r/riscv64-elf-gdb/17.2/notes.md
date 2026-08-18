# riscv64-elf-gdb 17.2 适配笔记

## 概述

GNU GDB 配置为**交叉调试器**，目标 `riscv64-elf`（裸机 ABI）。产出的
`riscv64-elf-gdb` 运行于 HarmonyOS PC (aarch64) 宿主，调试 riscv64-elf 裸机目标
对象；不在宿主执行 riscv64 代码。

## 构建系统 / 编译器

- autotools（`./configure && make`），顶层 GDB build tree
- 编译器：clang / clang++（来自 ohos-aarch64 profile，`/data/service/hnp/bin/clang`）

## 关键配置选项

| 选项 | 作用 |
|------|------|
| `--target=riscv64-elf` | 交叉目标；工具自动加 `riscv64-elf-` 前缀 |
| `--build=aarch64-unknown-linux-ohos` | 显式 build triplet，绕过 config.guess 探测（E007） |
| `--with-gmp-include/--with-gmp-lib` | GMP include 路径取 conan 依赖包目录，lib 路径取 staged 目录（.dep-archives，build-private 无 .la，缓存零改动） |
| `--with-mpfr-include/--with-mpfr-lib` | MPFR 同上（lib 路径取 staged 目录 .dep-archives） |
| `--with-system-readline` | 使用 conan readline/8.3 |
| `--with-expat` | 使用 conan expat/2.8.2 |
| `--disable-gdbserver` | 交叉裸机目标无意义 |
| `--disable-sim` | 避免 sim/riscv 构建复杂度 |
| `--disable-tui` | 避开 ncurses C++ 冲突（gdb 14.1 先例） |
| `--without-python` | 简化构建，避免 Python 3.12 兼容风险 |
| `--disable-nls --disable-werror` | 去 i18n；防止 clang 告警当错误 |

## 适配补丁

- `0001-config.guess.patch`：添加 `__OHOS__` → `LIBC=ohos` 分支 + `*:HarmonyOS:*:*`
  → `<arch>-unknown-linux-ohos` 分支（E007）
- 19 个 configure 的 `umask 077`→`022`：在 `build()` 内 glob 替换（flint 先例，E011）

## 依赖链

| 依赖 | 版本 | 用途 | OHOS 适配 |
|------|------|------|-----------|
| gmp | 6.3.0 | 顶层 configure 硬性要求 | 已适配 |
| mpfr | 4.2.2 | 同上 | 已适配 |
| readline | 8.3 | GDB 交互式命令行 | 已适配 |
| expat | 2.8.2 | GDB XML 远程协议 | 已适配 |
| zlib | 1.3.2 | 调试段压缩 | 已适配 |

## 测试策略

- **upstream_test_in_build: false**：gdb 官方套件（`gdb/testsuite`）需 DejaGNU +
  expect + tclsh + 目标运行时/模拟器；设备当前无 DejaGNU（`which runtest` 无输出），
  交叉裸机场景无 riscv64 目标运行时 → 无法跑 `make check-gdb`
- **test_package（R34 合规）**：`riscv64-elf-gdb` 命令族 5 项验证（--version、set/show
  architecture riscv:rv64、maintenance print architecture、show data-directory、clang 交叉编译 test.s → test.elf + gdb 反汇编 _start）；避免 ptrace（E222）

## 已知限制

- TUI 不可用（`--disable-tui`），因 ncurses C++ 冲突
- Python 脚本不可用（`--without-python`），避免 Python 3.12 兼容风险
- 上游测试套件未运行（交叉场景 + 设备无 DejaGNU）
