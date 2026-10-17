# debarchiver

Debian **存档仓库管理工具** —— 把上传到 `incoming/` 的 `.changes` 包整理进仓库，
生成 apt 索引（`Packages` / `Sources` / `Release`），并可选对 `Release` 做 gpg 签名。

## ⚠️ 硬前置：opalmod

`debarchiver.pl` 在 **BEGIN 阶段**即加载 OpaL 模块：

```perl
use OpaL::action qw(pdebug action cmdaction ...);
use OpaL::read   qw(readfile readcommand);
```

Debian `control` 亦声明 `Depends: opalmod (>= 0.1.10)`。缺它连 `--version` 都跑不起来
（实测 `Can't locate OpaL/action.pm` → `BEGIN failed`）。

→ 本仓库已先行适配 **opalmod 0.2.2.1**（PR #9708），本包依赖它。

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.11.7 | built | 2026-09-12 | 纯 Perl 脚本；`conan create` EXIT=0；`test_package` 9/9 |

## OHOS 适配要点

| # | 要点 | 说明 |
|---|------|------|
| 1 | **shebang 改 `env perl`** | OHOS 无 `/usr/bin/perl`（perl 由 ohpcd 的 perl 包提供）→ `#!/usr/bin/env perl` 由 PATH 解析 |
| 2 | ★ **不调 `make install`** | 上游 Makefile 用 `install -m755`/`-m644`，而 **OHOS 无 coreutils `install`（E188）** → 由配方按上游布局自行落盘 |
| 3 | **man 页改用 `Pod::Man`** | 上游 `po4a` 流程需 `podselect`（ohpcd 的 perl 包内无 `Pod::Select`）与 `po4a`（未适配）→ 改为 perl 自带的 `Pod::Man` 直接从内嵌 POD 生成 |
| 4 | **运行期目录用配置覆盖** | `$inputdir`/`$destdir`/`$cachedir` 默认指向 `/var/lib`、`/var/cache`；目录不存在时脚本 `chdir` 失败 → `EXIT: 2`。**实测 `--configfile` 可覆盖**，故包内保持上游默认值 |

## ⚠️ 已知限制：核心功能依赖的外部工具在 OHOS 上不可得

| 外部工具 | 用途 | OHOS |
|---------|------|------|
| `apt-ftparchive` | 生成 Packages/Sources 索引 | ❌ |
| `dpkg-scanpackages` | 包扫描建索引 | ❌ |
| `dpkg-deb` | 解析 .deb | ❌ |
| `gpg` | 签名 Release | ❌ |
| `adduser` | 用户管理 | ❌ |

→ 本包在 OHOS 上**可安装、可运行**（`--help` / `--version` / 参数解析 / 配置加载均正常），
但**无法完成完整的收包与建索引流程**。属**功能限制**（同 apt 链的既有结论），非适配缺陷。
配方与测试均**如实声明**，未伪称功能可用。

> 与 `cron-apt` 同类情形：脚本本身能跑，其功能所依赖的上游工具链在 OHOS 不可得。

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| **opalmod/0.2.2.1** | 运行期（硬前置） | 提供 `OpaL::action` / `OpaL::read` |
| **perl/5.42.2** | 运行期 | shebang 经 `/usr/bin/env perl` 解析 |

> ⚠️ **消费者须直接声明 `opalmod`**（或自行设置 `PERL5LIB`）：
> 本包 `package_type = "application"`，实测其依赖 `opalmod` 在消费者图中被判为
> `Skipped binaries`，导致 opalmod 的 `runenv_info`（`PERL5LIB`）**不会传播**到
> 消费者环境（对照实验：仅经传递时 runenv 中 opalmod 路径数 = 0；直接声明后 = 8）。
> 因此运行 `debarchiver` 的工程应在自己的 `[requires]` 里**同时写上 `opalmod`**。

## Installation

```bash
conan create archives/d/debarchiver/0.11.7 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

使用（需自备配置以覆盖硬编码目录，并确保 `opalmod` 已在依赖图中）：

```bash
debarchiver --configfile /path/to/debarchiver.conf --version
```
