# dh-sysuser

dh-sysuser 是 Debian 的 debhelper 插件（`dh` 序列自动加载），用于在软件包安装/卸载时根据 `sysusers.d`/`debian/*.sysusers` 配置创建或删除系统用户与组。

## 功能概述

- 提供 `dh_installsysusers`（由 `dh_sysuser` 序列 addon 触发）创建系统用户与组
- 提供 `minsysusers`（gencode CLI，解析 sysusers 配置生成 postinst/maintscript 片段）与 `sysuser-helper`（POSIX sh helper，实际执行 useradd/groupadd）
- 生成 `postinst` / `postrm` 自动脚本片段（autoscripts），安装时调用 `systemd-sysusers` 或回退到 useradd 命令
- 上游版本：1.6.0（2025-01-28，Debian bookworm/trixie 维护版，原生打包，无构建系统）

## OHOS 适配

- 本包为**纯 Perl / POSIX sh 脚本包**，上游 tarball 是 Debian native 源：没有 Makefile、configure 或任何编译产物，文件按 `debian/dh-sysuser.install` 布局安装
- 安装布局镜像 Debian：`bin/dh_sysuser`、`bin/minsysusers`、`bin/sysuser-helper`，`share/perl5/Debian/Debhelper/Sequence/sysuser.pm`，`share/man/man8/minsysusers.8`，`share/debhelper/autoscripts/`
- **已知限制**：`dh_sysuser` 需要 `Debian::Debhelper::Dh_Lib`，只能在具备 debhelper 的系统中执行；`minsysusers`（纯 perl，仅核心模块）与 `sysuser-helper`（POSIX sh）则可用真实解释器直接执行，CI test_package 会实际运行二者
- 上游官方测试 `debian/tests/sysuser-helper`（Debian autopkgtest）依赖 apt-get/root + `useradd`，OHOS 目标环境无法承载；已在 Debian 13 chroot 中用本包产出的运行时文件替换发行版同名文件后真实执行上游脚本，结果 1/1 通过，证据见 `archives/d/dh-sysuser/1.6.0/reports/upstream-autopkgtest-evidence.md`
- L2 运行探测（`--version`/`--help`）属警告级，不阻塞 CI

## 依赖关系

- 编译依赖：无（零编译）
- 运行时依赖：perl（上游）、用户管理后端（systemd-sysusers / useradd + groupadd）
- Conan 引用：`dh-sysuser/1.6.0`（package_type=application）

## 参考资料

- 源码仓库：<https://salsa.debian.org/debian/dh-sysuser>
- Debian 包页面：<https://packages.debian.org/sid/dh-sysuser>
- 归档路径：`archives/d/dh-sysuser/`