# dh-sysuser 1.6.0 适配笔记

## 软件简介

dh-sysuser 是 Debian debhelper 的 `dh` 序列插件（addon），在软件包安装/卸载时根据
`debian/*.sysusers`（或 `/usr/lib/sysusers.d/`）配置创建/清理系统用户与组。上游仓库
`https://salsa.debian.org/debian/dh-sysuser`，本次打包 1.6.0（2025-01-28）。

## 上游测试说明（已真实执行）

- 上游官方测试为 **Debian autopkgtest (DEP-8)**，位于 `debian/tests/`，实测用例数 **N=1**
  （`debian/tests/sysuser-helper`，`debian/tests/control` 声明 `Restrictions: needs-root`）。
- 测试断言内容：安装 `runit` 包后系统用户 `_runit-log` 被创建、remove 后保留。
- **真实执行结果：发现 1 / 执行 1 / 通过 1 / 失败 0，通过率 100%（1/1）**，
  完整方法与逐字日志见 `reports/upstream-autopkgtest-evidence.md`。

### 执行方式（为什么不在 OHOS 上跑）

上游脚本**逐字硬依赖 `apt-get`**，断言链路是「安装一个用 dh-sysuser 构建的 deb 包 →
其 postinst 调用 dh-sysuser 运行时组件 → 系统用户被创建」：

```
runit.postinst（由 dh_sysuser/1.6.0 自动生成）
  └─ /usr/sbin/minsysusers runit.conf        ← 本包产物 minsysusers（perl）
       └─ useradd --prefix=<root> … _runit-log
```

这条链路要求 apt/dpkg + root + 真实 `/etc/passwd`。OpenHarmony 侧既无 apt/dpkg，
也无 `useradd`/`groupadd`（shadow-utils），**该用例在 OHOS 目标环境内不可承载**。
因此在 **Debian 13 (trixie) chroot** 中真实执行上游测试脚本本体（原样、未改一字，
sha256 `46ebb38784fd80d177951bed52f31acfabe0e32218425adf8042f21e3abdb076`）：

- **RUN A（基线）**：发行版自带 `minsysusers 1.6.0` 运行时 → 退出码 0。
- **RUN B（适配产物）**：把本包 `conan create` 产出的 `minsysusers` / `sysuser-helper` /
  `dh_sysuser` / `sysuser.pm` / autoscripts 覆盖到 Debian 同名安装路径后再跑同一份脚本
  → 退出码 0；替换前后 `sha256sum /usr/sbin/minsysusers` 均等于本包产物哈希，
  证明断言确实由本包代码产生。

未修改上游任何测试文件（`debian/tests/` 保持原样）。

## OHOS 侧 test_package

`test_package/test.sh` 共 10 条断言（perl 可用时）：

1. `dh_sysuser` / `minsysusers` / `sysuser-helper` 存在性（3 条）
2. `dh_sysuser` 版本标记 `1.6.0`、`minsysusers` 内容标记、`sysuser-helper` sh shebang（3 条）
3. **真实执行**：`perl -c minsysusers`（真实 perl 完整编译该脚本）、
   `perl minsysusers`（无参用法路径，须非零退出）、`sh -n sysuser-helper`、
   `sh sysuser-helper prerm`（实际执行上游定义的 no-op 子命令）（4 条）

宿主无 perl 时跳过第 3 组并打印 `WARN`（OHOS worker 上 perl 位于
`/data/service/hnp/bin/perl`，与 `archives/d/debhelper` 的 test_package 取用方式一致）。

## 关键特性：Debian native 源、纯脚本包

- 上游 tarball 是 **Debian native 源**：没有 Makefile、configure、CMake 或任何编译产物；
  文件按 `debian/dh-sysuser.install` 直接安装
  - `dh_sysuser`（perl，dh 序列 addon）→ `/usr/bin`
  - `minsysusers`（perl，gencode CLI）、`sysuser-helper`（/bin/sh）→ `/usr/bin`
  - `sysuser.pm`（perl 模块）→ `/usr/share/perl5/Debian/Debhelper/Sequence`
  - `minsysusers.8` → `/usr/share/man/man8`
  - `postinst-sysuser` / `postrm-sysuser` / `postinst-minsysusers` → `/usr/share/debhelper/autoscripts`
- License：GPL-3.0-or-later（`minsysusers*` 单独为 BSD-3-clause）

## 编译环境

- 构建系统: custom（零编译，`build()` 为空操作，`package()` 镜像 Debian 安装布局）
- 编译日期: 2026-09-11
- 编译器: clang/clang++（无编译步骤，字段保留）
- 状态: built

## 编译步骤

1. `conan create` 由 recipe 驱动：`get()` 解包官方 Debian pool 的 `tar.xz`
2. `build()` 空操作（无编译任务）
3. `package()` 安装脚本 + perl 模块 + 手册页 + autoscripts 至包前缀

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 无 debhelper 用户管理后端，`dh_sysuser --version` 无法执行（需 `Debian::Debhelper::Dh_Lib`） | 脚本依赖 debhelper 与本机用户管理后端 | test_package 以产物断言 + 可独立执行的脚本（`minsysusers`/`sysuser-helper`）真实执行覆盖；L2 `--version` 探测属警告级非阻断 |
| 2 | 无构建系统，init-build 默认 autotools 模板不可用 | Debian native 源无 Makefile/configure | 手写 custom 配方，镜像 `debian/dh-sysuser.install` 布局 |
| 3 | 上游 autopkgtest 在 OHOS 无法执行（apt-get + root + useradd） | 上游脚本断言的是 deb 包安装行为 | 在 Debian 13 chroot 真实执行上游脚本本体，并用本包产物替换运行时后复跑（RUN A/B 均通过），证据见 `reports/upstream-autopkgtest-evidence.md` |
| 4 | `perl -w` 运行时 `minsysusers` 报 `Use of uninitialized value $_[1] in string at line 81` | 上游 1.6.0 自身行为 | 不改动上游代码；基线 RUN A 同样出现该警告，不影响退出码与断言，已在证据文档中如实记录 |

## 源码修改

无补丁（`patches/` 为空）。
> 说明：原样打包，未修改任何上游文件（含 `debian/tests/`）；补丁为空保持最小文件集（ARCHIVE-SPEC v3）。

## 依赖版本

- 编译依赖：无（零编译）
- 运行时依赖：perl、用户管理后端（systemd-sysusers 或 useradd/groupadd）

## 验证结果

```bash
# 1) 本包构建与 OHOS 侧测试（CI: conan create → test_package）
conan create archives/d/dh-sysuser/1.6.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
archives/d/dh-sysuser/1.6.0/test_package/test.sh <pkg>/bin   # 10/10 断言通过

# 2) 上游官方测试（Debian 13 trixie chroot，真实执行）
debootstrap --variant=minbase trixie /tmp/dhroot http://deb.debian.org/debian
#   RUN A: 发行版运行时            → sh -x debian/tests/sysuser-helper  == 0
#   RUN B: 本包产物替换运行时后     → sh -x debian/tests/sysuser-helper  == 0
#   结果: N=1 执行 1 通过 1 → 100%
```

## 遗留风险

- 该包在 OpenHarmony 上无实际执行能力（纯 Debian 工具链组件），仅作为"原样打包"制品交付，
  供需要时在具备 perl/debhelper 的环境中消费；已如实记录于 manifest 与 commands.json（binary=false）。
- 上游 autopkgtest 的执行环境是 Debian 用户态而非 OHOS 目标机（原因见上），
  本档案不声称该用例在 OHOS 上执行过。
---

**编译结束**: 2026-09-11 14:53
**上游测试真实执行**: 2026-09-15
**最终状态**: built
