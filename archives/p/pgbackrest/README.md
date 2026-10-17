# pgBackRest for HarmonyOS

## 概述

pgBackRest 是面向 PostgreSQL 的可靠备份与恢复工具（命令行程序，MIT 许可）。它支持全量/差异/增量备份、
并行备份与恢复、备份加密与压缩（gz/lz4/zstd/bz2）、远程仓库（S3/Azure/GCS/Posix）以及 SFTP 传输。

本归档为 pgBackRest 在 HarmonyOS PC / OpenHarmony（aarch64）上的 Conan 适配与打包记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | pgbackrest |
| 官网 | https://pgbackrest.org |
| 上游仓库 | https://github.com/pgbackrest/pgbackrest |
| 许可证 | MIT |
| 类别 | 数据库工具（命令行） |
| 构建系统 | Meson |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC（HongMeng Kernel） |
| 架构 | aarch64（ELF64，小端） |
| 编译器 | clang 15（OHOS SDK） |
| C 标准库 | musl |
| Conan profile | `ci/conan/profiles/ohos-aarch64` |

## 适配要点

- 上游 2.59.0 使用 Meson 构建。发布用分发 tarball 已携带生成好的 help/interface 头，因此构建纯 C 核心
  不需要上游的代码生成工具链与 libyaml，也不调用 Perl（Perl 仅在 git 检出树里构建文档/测试工具时才需要）。
- Meson 把 OHOS 目标报告为 `harmonyos`，需要为它补上 `_POSIX_C_SOURCE=200809L`。
- bzip2 由上游以 `cc.find_library('bz2')` 定位（不走 pkg-config），需要显式注入 include/lib 目录。
- 上游查找 `liblz4`，Conan 的 lz4 包提供 `lz4.pc`，用一个转发 `.pc` 桥接。
- 安装后需要用 `binary-sign-tool` 重新签名：`meson install` 重写 RUNPATH 会使链接器写入的 `.codesign`
  段签名失效，HarmonyOS 会拒绝执行未匹配签名的 ELF。

## 依赖

运行时依赖 `libpq`、`openssl`、`libxml2`、`libssh2`、`lz4`、`zstd`、`bzip2`、`zlib`，
均取自 OpenHarmony PC 制品仓（ohpcd）。

## 参考

- 上游用户手册：https://pgbackrest.org/user-guide.html
- 上游命令手册：https://pgbackrest.org/command.html
- 各版本适配细节见对应版本目录下的 `notes.md` 与 `manifest.yaml`。
