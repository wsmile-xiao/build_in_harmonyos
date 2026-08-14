# screen

GNU Screen — 终端多路复用器，在单个终端中管理多个会话、窗口分割、会话恢复。

## 描述

Screen 允许用户在一个终端窗口中创建多个虚拟终端会话，支持会话分离/恢复、窗口管理、滚动历史、日志记录等功能。广泛用于远程服务器管理和长时间运行任务。

## 已编译版本

| Version | Status | Date |
|---------|--------|------|
| 5.0.0 | published | 2026-08-04 |

## 构建说明

- 构建系统：autotools (configure + make)
- 构建命令：`./configure --prefix=$DEFAULT_PREFIX --disable-pam && make -j1 && make install`
- 补丁数：7
- 链接方式：静态链接 ncurses (R26)
- Conan profile：ohos-aarch64

## 关键适配问题

1. **configure umask 077 不兼容 HMDFS**：configure 脚本使用 `umask 077` 创建临时目录，HMDFS 文件系统下创建的目录权限不可写导致 configure 失败。修改为 `umask 022`。

2. **closeallfiles() 中 poll() 返回 ENOMEM**：OHOS 的 `poll()` 在轮询大量文件描述符时返回 ENOMEM 错误，导致 screen 在关闭文件时崩溃。改为 POSIX `close()` 循环（EBADF 无害）。

3. **seteuid/setegid/getspnam 不可用**：OHOS 不支持 `seteuid(0)`/`setegid(0)` 获取 root 权限和 `getspnam()` 读取 shadow 密码。改为失败容错处理（非 Panic）。

4. **glibc malloc mock 不兼容**：screen 测试框架使用 `__libc_malloc` 符号进行 malloc mock，OHOS 的 musl libc 无此符号。通过 macros.h 和 mallocmock.c 的 `#ifdef __GLIBC__` 守卫禁用 mock（非平台宏），测试聚焦核心功能验证。

5. **OHOS 无 PAM 支持**：configure 检测到 PAM 不可用，需显式 `--disable-pam`。

6. **getpwuid() 平台限制**：OHOS 无传统 Unix passwd 条目，`getpwuid()` 无法查找用户，影响会话管理功能 (`-ls`/`-dm`)。不影响编译和基础功能。

## 依赖

| Dependency | Version | Source |
|-----------|---------|--------|
| ncurses | 6.4 | cmd-pkgs (系统安装，非 Conan 依赖) |
| coreutils | 9.10 | cmd-pkgs (解决 toybox expr 复合正则 bug) |

> ncurses 头文件需从源码或 abook 归档 (ncurses-headers.tar.gz) 提取，cmd-pkgs 只发库不发头文件。

## 补丁说明

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001 | configure | umask 077→022 HMDFS 兼容 |
| 0002 | misc.c | closeallfiles() poll() ENOMEM → 直接 close() 循环 |
| 0003 | socket.c | seteuid/setegid 失败容错处理 |
| 0004 | tests/macros.h | 禁用 glibc malloc mock on OHOS |
| 0005 | tests/mallocmock.c | include config.h, guard `__libc_malloc` |
| 0006 | tests/test-winmsgbuf.c | guard FAILLOC assertions on OHOS |
| 0007 | tests/test-winmsgcond.c | 修复类型不匹配 char*→int |

## 构建产物

- `bin/screen-5.0.0` — 终端多路复用器可执行文件
- `bin/screen` → 符号链接到 `screen-5.0.0`
- `share/screen/utf8encodings/` — UTF-8 编码映射表

## 使用方法

```bash
# 查看版本
screen --version
# Output: Screen version 5.0.0

# 查看帮助
screen --help

# 创建新会话
screen -S mysession

# 分离会话：Ctrl+A 然后按 D

# 恢复会话
screen -r mysession
```

## 测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| configure | PASS | --disable-pam |
| make -j1 | PASS | 4 个无害警告 |
| make check | PASS | test-winmsgbuf + test-winmsgcond |
| screen --version | PASS | "Screen version 5.0.0" |
| screen --help | PASS | 完整帮助输出 |
| ELF NX | PASS | GNU_STACK RW (无 Execute) |
| ELF PIE | PASS | DYN (Position-Independent) |
| ELF RELRO | PASS | GNU_RELRO 段存在 |
| conan create | PASS | 干净构建成功 |
| conan-verify | PASS | G0-G4 + L2/L4/L5 全通过 |
| CI L0-L5 | PASS | L4 为非阻塞警告 |
| screen -ls / -dm | 平台限制 | getpwuid() 无法查找用户 |

## 验证安装

```bash
# Conan 安装
conan install --requires=screen/5.0.0 -pr:h=ci/conan/profiles/ohos-aarch64

# CI 验证
CI_PACKAGES="archives/s/screen/5.0.0" zsh ci/conan/build_and_test.sh
```

## 经验总结

1. cmd-pkgs ncurses 只发库不发头文件，需从源码或已有归档 (如 abook 的 ncurses-headers.tar.gz) 提取头文件。
2. screen 是命令行工具而非库，conanfile.py 需设 `package_type = "application"`、`bindirs = ["bin"]`，并创建 commands.json (R38)。
3. OHOS 的 musl libc 无 `__libc_malloc` 符号，任何使用 glibc malloc mock 的测试框架都需要 `#ifdef __GLIBC__` 守卫（非平台宏）。
4. HMDFS 文件系统对 `umask 077` 创建的目录权限处理与 ext4 不同，需统一改为 `umask 022`。
5. `getpwuid()` 在 OHOS 上不可用是平台级限制，不影响编译质量但会影响运行时会话管理，属于已知限制。

## 参考资料

- [GNU Screen 官方网站](https://www.gnu.org/software/screen/)
- [screen 5.0.0 源码下载](https://ftp.gnu.org/gnu/screen/screen-5.0.0.tar.gz)
- [GNU Screen 手册](https://www.gnu.org/software/screen/manual/screen.html)
- [Conan 文档](https://docs.conan.io/)
- [HarmonyOS PC 开发者](https://gitcode.com/OpenHarmonyPCDeveloper)
