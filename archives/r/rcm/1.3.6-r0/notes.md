# Adaptation Notes — rcm 1.3.6-r0 (upstream v1.3.6)

## Software
- **Name**: rcm
- **Version**: 1.3.6-r0 (upstream v1.3.6, Alpine Linux package revision r0)
- **Description**: rc file (dotfile) management — manage dotfiles with rcup, rcdn, lsrc, mkrc
- **License**: BSD-3-Clause
- **Source**: https://github.com/thoughtbot/rcm/releases/download/v1.3.6/rcm-1.3.6.tar.gz
- **SHA256**: f4fdfbc451d1fb5764531290a202a0a871f6b81ba3c01a6b76c49435c85080a5

## Build System
- **Type**: Autotools (configure + make)
- **configure.ac**: AC_INIT([rcm],[1.3.6]), AM_INIT_AUTOMAKE([subdir-objects])
- **无 AC_CANONICAL_HOST**: configure 不做平台检测，不生成 config.guess/config.sub
- **AUTOMAKE_OPTIONS = foreign**: 简化模式，不要求 NEWS/AUTHORS/ChangeLog 等文件
- **Release tarball**: 已预生成 configure (106KB)、Makefile.in、aclocal.m4、man 页，无需 autoreconf 或 ruby-mustache

## Build Configuration
- **无 --build/--host 参数**: rcm 的 configure.ac 无 AC_CANONICAL_HOST，不做平台检测，不需要 triplet
- **无编译器选项**: rcm 是纯 shell 脚本工具，无 C 编译
- **make -j1**: 单线程构建（shell 脚本安装，无编译并行需求）

## Dependencies
- **构建依赖**: 无（tarball 已预生成所有需要文件）
- **运行时依赖**: bash（OHOS 使用 /data/service/hnp/bin/bash）
- **测试依赖**: cram 框架（LOG_COMPILER=cram）、perl（test/helper.sh 的 resolved_path 函数）
- **无 Conan 依赖**: rcm 是自包含的 shell 脚本工具

## Issues Encountered
1. **OHOS shebang (E165)**: configure 脚本使用 `#! /bin/sh`，OHOS 无 /bin/sh。在 build() 中替换为 `#!/system/bin/sh`。
2. **OHOS umask (E110)**: configure 中 `umask 077` 在 HMDFS 上导致临时目录权限问题。替换为 `umask 002`。
3. **bin/*.in 脚本 shebang (E165)**: 所有四个 bin/*.in 文件（lsrc/mkrc/rcdn/rcup）均使用 `#!@SHELL@`，configure 会将其替换为 $SHELL（默认 /bin/sh），OHOS 无 /bin/sh 和 /bin/bash。在 build() 中统一替换：
   - bin/lsrc.in, bin/mkrc.in, bin/rcdn.in, bin/rcup.in: `#!@SHELL@` → `#!/data/service/hnp/bin/bash`（直接替换，避免 configure 将 @SHELL@ 替换为 /bin/sh）
4. **无 config.guess/config.sub (E007 不适用)**: rcm 的 configure.ac 无 AC_CANONICAL_HOST，tarball 不含 config.guess/config.sub，无需 E007 修复。
5. **cram 测试框架**: rcm 上游测试使用 cram 框架 (LOG_COMPILER=cram)，OHOS 环境可能未安装 cram。在 build() 中通过 `shutil.which("cram")` 检查：如果可用则运行 make check，否则输出 warning 跳过。
6. **perl 依赖**: test/helper.sh 的 resolved_path 函数使用 perl，部分测试可能因 perl 缺失而失败。test_package 中的烟雾测试不依赖 perl。

## Test
- **上游测试**: rcm 自带 47 个 cram 测试文件 (test/*.t)，覆盖 lsrc/mkrc/rcup/rcdn/rcrc 的各种场景。build() 末尾条件性调用 `autotools.make(target="check")`，仅当 cram 可用时执行。
- **test_package**: 验证 rcm 四个命令的基本功能
  - Test 1: `lsrc` — 列出 ~/.dotfiles 中的 dotfiles
  - Test 2: `rcup` — 创建符号链接（.dotfiles/bashrc → ~/.bashrc）
  - Test 3: `rcdn` — 移除符号链接
  - Test 4: `mkrc` — 将 ~/.vimrc 引入 .dotfiles 目录并创建符号链接

## Installed Files
- bin/lsrc — 列出 dotfiles 符号链接
- bin/mkrc — 将 dotfile 引入 dotfiles 目录
- bin/rcup — 安装/更新 dotfiles
- bin/rcdn — 卸载 dotfiles
- share/rcm/rcm.sh — 共享库脚本（被四个命令 source）
- share/man/man1/lsrc.1, mkrc.1, rcdn.1, rcup.1 — man 手册页
- share/man/man5/rcrc.5 — rcrc 配置文件手册
- share/man/man7/rcm.7 — rcm 总览手册
- licenses/LICENSE — 许可证文件

## Notes
- rcm 是 CLI 应用程序 (application)，非库。package_info 中 libs=[]，bindirs=["bin"]。
- 版本号 1.3.6-r0 来自 Alpine Linux 包格式（pkgver=1.3.6, pkgrel=0），对应上游 v1.3.6。
- rcm 是 noarch（架构无关）工具，所有产物均为 shell 脚本和文本文件。
- Windows 环境无法进行 OHOS aarch64 本地验证，status 标记为 built，待 CI 验证。
