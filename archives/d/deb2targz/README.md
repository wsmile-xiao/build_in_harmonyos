# deb2targz

把 Debian 的 `.deb` 包转换成普通的 `.tar.gz` 归档 —— 单文件 Perl 脚本，
源自 Mike Taylor（2002 年编写，Gentoo / FreeBSD 长期打包维护）。

## Description

`.deb` 本质上是一个 **ar 归档**，内部含三个成员：`debian-binary`、
`control.tar.gz`、`data.tar.gz`。本工具从 ar 归档中取出 `data.tar.gz` 并
按原样写出为 `<原文件名>.tar.gz`，因此**输出与其中的 data.tar.gz 逐字节一致**
（不做重新压缩）。

适用于想直接查看/提取某个 `.deb` 内容、而不愿安装 `dpkg` 工具链的场景。

## ⚠️ 与 debarchiver 无关

两者名字相近但**是完全不同的软件**：

| | **本包**（deb2targz）| debarchiver |
|---|---|---|
| 用途 | 把单个 `.deb` 转成 `.tar.gz` | Debian 仓库管理（收包、建索引、签名）|
| 形态 | 单文件 Perl 脚本（1947 字节）| Perl 程序（`debarchiver.pl`，114 KB）|
| 来源 | miketaylor.org.uk（作者个人站点）| Debian 官方仓库 |
| 依赖 | 仅核心模块 `strict` + `IO::File` | `OpaL::*`（opalmod）+ apt-ftparchive/gpg 等外部工具 |

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 20100710 | built | 2026-09-12 | 单文件脚本；`conan create` EXIT=0 |

> 上游文件**不带版本号**。`20100710` 取自 Gentoo（`app-arch/deb2targz-1-r3`）
> 与 FreeBSD（`archivers/deb2targz/20100710`）的发行版本号，本仓库沿用。

## OHOS 适配要点

| # | 要点 | 说明 |
|---|------|------|
| 1 | **裸文件而非归档** | 上游是单个脚本文件 → 配方用 `download()` 而**不能**用 `get()`（后者会尝试解压）|
| 2 | **shebang 改 `env perl`** | OHOS 无 `/usr/bin/perl`（perl 由 ohpcd 的 `perl/5.42.2` 提供，位于包内 `bin/`）→ 改为 `#!/usr/bin/env perl` 由 PATH 解析 |
| 3 | ★ **必须同时去掉 `-w`** | `#!/usr/bin/env perl -w` 是**错误写法**：内核把 shebang 首空白之后的全部内容当作**一个参数**传给解释器，`env` 会去找名为 `perl -w` 的程序而失败。脚本内已有 `use strict;`，无功能损失 |
| 4 | 改写后自校 | `source()` 中校验首行确为 `#!/usr/bin/env perl` 且不含 `-w`，避免补丁静默失效 |

## 依赖

**运行期**：`perl/5.42.2`（ohpcd 已发布）。

脚本仅使用核心模块 `strict` 与 `IO::File`，无 CPAN 依赖。

## Installation

```bash
conan create archives/d/deb2targz/20100710 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

使用：

```bash
deb2targz package.deb      # 生成 package.tar.gz
```
