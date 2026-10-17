# dh-shell-completions

dh-shell-completions 是 Debian 的 debhelper 插件（`dh` 序列 addon，`--with shell_completions` 挂载），
用于按各 shell 的约定安装 bash / fish / zsh 补全脚本。它类似 bash-completion 提供的
`dh_bash-completion`，但原生支持多种 shell。

## 功能概述

- 提供 `dh_shell_completions`（Perl 脚本，含 POD），把补全脚本安装到各 shell 的 vendor 目录：
  - bash → `/usr/share/bash-completion/completions`
  - fish → `/usr/share/fish/vendor_completions.d`
  - zsh → `/usr/share/zsh/vendor-completions`
- 提供 `shell_completions.pm`（Perl 模块，`Debian::Debhelper::Sequence` addon）：以
  `insert_after("dh_installman", "dh_shell_completions")` 注册到 dh 序列
- 支持三种工作模式（优先级从高到低）：
  - **generation**：按 `debian/shell-completions` 中 `mode=gen` 的指令调用命令生成补全
  - **composite**：从 `debian/shell-completions` 文件列表按行安装多 shell 补全
  - **separate**：按 `debian/$shell-completions`（如 `debian/bash-completions`）分别安装
- 上游版本：0.1.0（2025-01-11，Debian unstable，native 打包，无构建系统）

## OHOS 适配

- 本包为**纯 Perl 脚本包**，上游 tarball 是 Debian native 源（`debian/source/format` = `3.0 (native)`）：
  没有 configure / CMake / autotools，也没有任何编译产物；文件按 `debian/install` 布局安装
- 安装布局镜像 Debian：`bin/dh_shell_completions`（0755）、
  `share/perl5/Debian/Debhelper/Sequence/shell_completions.pm`
- **上游测试真实执行（3/3 PASS）**：配方 `build()` 内搭建 perl 测试工具链后执行上游
  `tests/run.sh gen|composite|separate`（即顶层 `Makefile` 的 `test` target），任一失败即构建失败
  - perl 5.42.0：HNP 提供（`/data/service/hnp/bin/perl`，位于 PATH）
  - debhelper 13.3.4：官方源码 tarball（`dh` + 全部 `dh_*` + `Dh_Lib`/`Sequence`）
  - dh-autoreconf 20：官方 `.deb`（compat 13 默认启用的 `autoreconf` 序列 addon）
  - `dpkg-architecture`：以 `DEB_*` 环境变量替代（OHOS 无 dpkg）
- **源码改动 1 处**：`dh_shell_completions` 的 shebang 由 `#!/usr/bin/perl` 改为
  `#!/usr/bin/env perl`（`patches/0001-dh_shell_completions-env-perl-shebang.patch`）——
  OHOS 无 `/usr/bin/perl`，原 shebang 会导致 `bad interpreter`；上游测试脚本未修改
- 手册页（`dh_shell_completions.1`）由上游 `debian/rules` 用 `pod2man` 生成（依赖 perl），
  配方不生成、不安装该手册页
- L2 运行探测（`--version`/`--help`）属警告级，不阻塞 CI：该探测需 debhelper 的
  `Debian::Debhelper::Dh_Lib`（debhelper 是本包运行时依赖，不在包内）

## 依赖关系

- 编译依赖：无（零编译）
- 运行时依赖：perl、debhelper（`dh` 与 `Debian::Debhelper::Dh_Lib`）
- Conan 引用：`dh-shell-completions/0.1.0`（`package_type=application`）

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.1.0 | built | 2026-09-17 | Debian native 纯 Perl 脚本包，零编译；上游测试 3/3 + 包产物断言 10/10；无 Require；`binary=false` |

## 参考资料

- 源码仓库：<https://salsa.debian.org/debian/dh-shell-completions>
- Debian 包页面：<https://packages.debian.org/sid/dh-shell-completions>
- 归档路径：`archives/d/dh-shell-completions/`
