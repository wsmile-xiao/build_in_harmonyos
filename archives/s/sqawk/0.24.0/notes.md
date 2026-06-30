# sqawk 0.24.0 适配笔记

## 编译环境
- 构建系统: makefile (Tcl script assembly)
- 编译日期: 2026-06-09
- 编译器: N/A (pure Tcl script - assembled with tclsh)
- 状态: built

## 编译步骤

1. **安装 Tcl 8.6.14**（编译依赖 - 需要 tclsh）
   - 从 GitHub 下载 Tcl core-8-6-14 源码
   - `./configure --prefix=$DEFAULT_PREFIX`
   - `make -j2`
   - 手动安装 tclsh, libtcl8.6.a, libtclstub8.6.a, tclConfig.sh
   - 安装 Tcl library 目录到 $DEFAULT_PREFIX/lib/tcl8.6

2. **构建 sqawk**
   - `cd $BUILD_SRC_DIR`
   - `make sqawk` — 运行 `tclsh tools/assemble.tcl sqawk-dev.tcl > sqawk.tcl`
   - 产物: sqawk.tcl (56938 bytes, 自包含的 Tcl 脚本)

3. **安装 sqawk**
   - `make install DESTDIR=$TEST_PREFIX INSTALL=ginstall prefix=$DEFAULT_PREFIX`
   - 安装 sqawk 到 $TEST_PREFIX/$DEFAULT_PREFIX/bin/sqawk

4. **测试**
   - `make test` 被跳过 - 运行时依赖 Tcllib 和 sqlite3-tcl 未安装
   - 测试脚本需要 `package require fileutil` (Tcllib) 和 `package require sqlite3`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原指定URL nicowilliams/sqawk 404 | 仓库地址错误，实际为 dbohdan/sqawk | 使用 dbohdan/sqawk 仓库 |
| 2 | 版本 2.3.2-beta 不存在 | sqawk 最新tag 是 v0.24.0 | 使用 v0.24.0 |
| 3 | tclsh 不可用 | HarmonyOS 没有预装 Tcl | 从源码编译安装 Tcl 8.6.14 |
| 4 | Tcl configure config.status 无法创建临时目录 | HMDFS 文件系统权限问题（uid不匹配） | 修改 config.status 使用固定TMPDIR |
| 5 | `install` 命令不可用 | HarmonyOS 只有 `ginstall` (coreutils) | 修改 Makefile: INSTALL=ginstall |
| 6 | make test 失败 | 缺少 Tcllib (fileutil) 和 sqlite3-tcl | 跳过测试，记录运行时依赖 |

## 源码修改

补丁: 0001-ginstall.patch
- 将 Makefile 中的 `INSTALL = install` 改为 `INSTALL = ginstall`
- 原因: HarmonyOS 没有 `install` 命令，只有 `ginstall` (GNU coreutils)

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| Tcl | 8.6.14 | 编译时需要 tclsh 来组装 sqawk 脚本 |
| Tcllib | 1.21 | 运行时: cmdline, snit, fileutil 模块 |
| sqlite3-tcl | 3.49.1 | 运行时: SQLite3 Tcl 绑定 |
| zlib | 系统自带 | Tcl 编译时链接 |

## 验证结果

```bash
# sqawk 组装成功
tclsh tools/assemble.tcl sqawk-dev.tcl > sqawk.tcl  # 成功
# DESTDIR 安装成功
make install DESTDIR=$TEST_PREFIX INSTALL=ginstall prefix=$DEFAULT_PREFIX  # 成功
# 测试跳过 (缺少运行时依赖)
make test  # 跳过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| $DEFAULT_PREFIX/bin/sqawk | 56938 | 自包含 Tcl 脚本 |

## 注意事项

- sqawk 是纯 Tcl 脚本软件，不是 ELF 二进制
- 运行时需要: Tcl 8.6+, Tcllib, sqlite3-tcl
- 版本号 0.24.0 是 sqawk 最新稳定版本（原任务指定 2.3.2-beta 不存在）
- sqawk 的 assemble 过程将所有 lib/ 目录下的模块打包进 sqawk.tcl
---

**编译结束**: 2026-06-09 21:02
**最终状态**: built
