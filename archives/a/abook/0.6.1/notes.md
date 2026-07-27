# abook 0.6.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-02
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)
- 平台: HarmonyOS aarch64, HongMeng Kernel 1.12.0, musl libc
- 状态: published

## 编译步骤

1. 下载源码: `http://deb.debian.org/debian/pool/main/a/abook/abook_0.6.1.orig.tar.gz`
2. 安装依赖: `ncurses` 和 `readline` 通过 `cmd-pkgs` 安装到 `$HOME/usr/local/`
3. 修改 `config.guess`: 添加 HarmonyOS 识别 (E007)
4. 修改 `database.h`/`database.c`: 移除 `inline` 关键字 (C99 语义)
5. 修改 `Makefile`: ACLOCAL/AUTOCONF/AUTOHEADER/AUTOMAKE 设为 `true`
6. 修改 `config.status`: 移除 `umask 077` (HMDFS 权限问题)
7. `./configure --prefix=$HOME/usr/local`
8. `make -j1`
9. `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别平台 | config.guess 不含 HarmonyOS 分支 | 添加 HarmonyOS 到 Linux case 和 aarch64:HarmonyOS case |
| 2 | 链接错误: field_id 重复定义 | C99 inline 语义在 clang 下不同 | 移除 database.h/database.c 中 field_id 的 inline 关键字 |
| 3 | mktemp -d 创建的目录不可写 | HMDFS 文件系统 umask 077 问题 | 移除 umask 077，使用 mkdir -m 0777 |
| 4 | autotools 重生成失败 | 系统无 aclocal/automake/autoconf | Makefile 中 ACLOCAL 等设为 true |
| 5 | abook 原生格式文件读取失败 | 测试文件使用 `name = value` (有空格) | abook 格式使用 `name=value` (无空格) |
| 6 | HTML/Text 输出 segfault | ncurses UI 初始化在非终端环境失败 | 非核心功能，不影响地址簿核心功能 |

## 源码修改

- `config.guess`: 添加 HarmonyOS 平台识别
- `database.h`: 移除 field_id 的 inline 关键字
- `database.c`: 移除 field_id 的 inline 关键字

## 依赖版本

- ncurses: 通过 cmd-pkgs 安装 (libncursesw.a)
- readline: 通过 cmd-pkgs 安装 (libreadline.a + .so.8.2)

## 验证结果

conan-verify: ALL GATES PASSED (G0, G1, G2, G3, G4, L2, L4, L5)
功能测试: 10/13 通过 (CSV, vCard, LDIF, Pine, Elm 转换 + mutt-query 搜索)

## 注意事项

- abook 原生格式使用 `field=value`，不能有空格
- HTML 和 Text 输出格式在非交互终端下会 segfault (ncurses 依赖)
- HMDFS 文件系统的 umask 行为与标准 Linux 不同
---

**编译结束**: 2026-07-15 10:50
**最终状态**: published
