# blendsel 0.11 适配笔记

## 软件简介

blendsel 是 Debian Pure Blends 安装选择器（tasksel 3.74 的 fork），Debian
官方源包（Section: tasks/admin，uploader: Holger Wansing，Debian Install
System Team）。**纯 Perl CLI + po/pot 翻译 + tasks 数据 + debconf 集成脚本
的 Debian native 源包**：sloc 统计 perl 703 / makefile 86 / sh 60，无 C/C++
文件，上游 Makefile 不编译任何代码，只做安装与文档生成。

## 语言判定与适配路径决策（R47 覆盖说明）

- **语言预检结论**：源码主体为 Perl（4 个可执行源全部 .pl：blendsel.pl
  主程序、doincludes.pl/makedesc.pl/listpackages.pl 构建辅助）+ po 翻译 +
  sh 数据脚本，非 C/C++（与任务默认 cpp 不匹配，R47 本应上报
  env_unsupported）。
- **用户决策（覆盖 R47）**：此类纯脚本/纯解释型包按仓库既有"脚本包正常
  适配先例"（abcselect/1.5 纯 Perl、abuild shell 系、alot 纯 Python、lv/
  check-jsonschema 等）走完整适配流程——Conan 配方以解释器为运行时依赖
  即可交付可安装可验证的包。**本次按成功路径适配，不因语言判定直接放弃。**

## 编译环境

- 构建系统：无编译（Debian native 纯脚本包；等效 build_system: make——
  Makefile 仅安装用途，recipe 直接接管安装布局）
- 编译日期：2026-09-07
- 解释器：conan perl/5.42.2（ohpcd 制品仓预编译 OHOS arm64 二进制）
- 状态：built

## OHOS 关键事实

| 项 | 结论 |
|----|------|
| OHOS perl | ✅ 系统自带 perl 5.42.0（`/data/service/hnp/bin/perl`，aarch64-linux），且 conan 制品仓有 perl/5.42.2（pkgid 6b129b06，os=OHOS/armv8/clang15）——abcselect 已消费 |
| Locale::gettext | ❌ 系统 perl 与 conan perl 均无（Debian 生态 XS 模块 liblocale-gettext-perl）→ 补丁可选加载 + 英文原文回退（等价 C locale 输出） |
| /usr/bin/perl | ❌ OHOS 无此路径 → shebang 改 `#!/usr/bin/env perl`（E049 先例） |
| dpkg/apt/debconf | ❌ 无 → install/remove 执行链与 debconf UI（blendsel-debconf source /usr/share/debconf/confmodule）不可运行，如实记录 runnable=0；纯 perl 数据链可完整运行 |

## 补丁：patches/0001-blendsel-portable-env-gettext-prefix.patch

对 blendsel.pl 三处最小改动（全部为 portability 类，Debian 布局语义不变）：

1. **shebang**：`#!/usr/bin/perl` → `#!/usr/bin/env perl`（OHOS 无 /usr/bin/perl）
2. **Locale::gettext 可选化**：`use Locale::gettext;` → eval require + import，
   缺失时以同名兜底子（textdomain 空操作、gettext/dgettext 原文返回）——
   程序在有模块（Debian）与无模块（OHOS/纯 perl core）环境行为一致
3. **数据路径前缀推导**：`$debconf_helper/$testdir/$packagesdir/$descdir/
   $localdescdir/$infodir` 原硬编码 `/usr/lib/blendsel`、`/usr/share/blendsel`
   等；追加 `if ($0 =~ m{^(.*)/bin/blendsel$})` 块，按脚本所在 `bin/..`
   推导数据目录 → Conan 自定义 prefix 安装 relocation-free，标准 Debian
   （/usr/bin/blendsel）布局完全不变。`$statusfile=/var/lib/dpkg/status`
   保留原义（无 dpkg 时读取路径为空，代码已有容错）。

## 构建与安装步骤（recipe 内实现）

```bash
# 1. source(): conan get snapshot.debian.org tar.xz（sha256 校验），strip_root
# 2. build(): apply_conandata_patches
#    perl <src>/makedesc.pl <src>/tasks <build>/debian-tasks.desc
#      —— 生成任务描述数据（上游 make all 核心产物；apt-cache 缺失时
#         package lint 自动降级，同上游行为；doincludes #include 展开
#         tasks 数据未使用，跳过）
#    pod2man --section=8 ... blendsel.pod | gzip  → blendsel.8.gz
#      —— man 页（perl 制品含 pod2man 时；缺失则跳过并 info 记录）
# 3. package(): 忠实对齐 Debian 包布局：
#    bin/blendsel  lib/blendsel/{blendsel-debconf, tests/debconf,
#    tests/new-install, packages/list}  share/blendsel/descs/debian-tasks.desc
#    share/man/man8/blendsel.8.gz  licenses/copyright(debian/copyright)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 系统 perl `-MLocale::gettext` 直接 BEGIN 失败 | Debian XS 模块，OHOS perl core 无 | 补丁 2（可选加载 + 英文回退），验证 perl -c 通过 |
| 2 | shebang `#!/usr/bin/perl` 不存在 | OHOS 无 /usr/bin/perl（perl 在 /data/service/hnp/bin） | 补丁 1（env perl），conanrun PATH 注入 conan perl |
| 3 | 数据路径硬编码 /usr/lib/blendsel、/usr/share/blendsel | 脚本假设 Debian FHS | 补丁 3（\$0 前缀推导），保留 Debian 布局默认 |
| 4 | --list-tasks 在无 apt/dpkg 机器打印 exec 失败噪音 | task_avail/package_avail 探测 apt-cache/dpkg-query（上游设计，Debian 环境无此问题） | 非缺陷；test_package 选用不触发的 --task-packages/--task-desc 数据链路径 |
| 5 | /tmp 只读（E002） | OHOS hmdfs | 生成物全部写 $HOME/tmp 与 build 目录 |
| 6 | desc 生成依赖 apt-cache | makedesc.pl lint 探测包可用性 | lint 缺失自动降级（上游同构），desc 正常生成 |

## 依赖版本

- perl/5.42.2（conan，ohpcd 预编译；本机 local cache 亦有 5.42.0 系统 perl 可对照）

## 验证结果

```bash
# 探索期（系统 perl 5.42.0，模拟安装前缀树）：
perl -c blendsel.pl            # syntax OK（补丁后）
blendsel --task-packages=med-blend   # -> task-med-blend, rc=0
blendsel --help                # usage（stderr: blendsel [OPTIONS...]）, rc=1
blendsel --task-desc=astro-blend     # rc=0（desc 数据读取链）
pod2man ... | gzip              # blendsel.8.gz 生成正常

# 正式验证：conan create（见 reports/ 与 conan-verify G0-G4 输出）
```

## 上游测试说明（R51/R53）

- blendsel 无上游回归测试套件：tests/ 目录仅 debconf、new-install 两个
  文件，是 **运行期 task filter hooks**（blendsel.pl:463-464 按任务
  `Test-*` 字段以 `$testdir/$test` 调用，读 DEBIAN_HAS_FRONTEND/
  DEBCONF_READFD/NEW_INSTALL 等环境并以 exit 0-3 表达展示/安装语义），
  install/remove 与 debconf UI 依赖 dpkg/apt/debconf 生态 → OHOS
  runnable=0（生态绑定）。
- 上游 N=0 清点证据：`find <src>/tests -type f` 仅 2 个 hook 文件；
  `grep -nE '^test|^check' Makefile` 无匹配（Makefile 仅 all/%.o/
  po-build_stamp/updatepo/install/install-data/clean）；`grep -rln
  Test::More tests/` 无匹配（无 perl 测试框架）。
- test_package 实质验证替代（R34/R53）：test_blendsel.py 在 conanrun
  环境实跑 8 项独立断言——1) shebang `#!/usr/bin/env perl`；2) 包布局
  bin/ + lib/blendsel + share/blendsel 完整；3) desc 数据可读含
  med-blend；4) perl -c 语法；5) perl 解释器来自 conan perl/5.42.2
  制品路径；6) perl --version v5.42.2；7) --task-packages=med-blend
  输出 Key 包 task-med-blend；8) 未知选项 usage 且非零退出——逐项
  PASS 计数，任一失败非零退出。

## 注意事项

- 上游 bug 备忘（未修，不影响本包交付）：`--task-desc=<不存在的任务>` 路径
  调用未定义的 `fprintf`（perl 无内建 fprintf，行 886），上游在 Debian 同样
  触发；任务名存在时路径正常（dgettext + print）。
- scripts/packages/list 是 `#!/bin/sh` 包列表钩子（上游按 -m 755 安装），
  无 perl 依赖，已在 prefix 推导外保持原样安装。
- 系统 perl（/data/service/hnp/bin/perl）与 conan perl 均为 core-only；
  若未来启用 po 翻译（.mo），需要 Locale::gettext 制品级支持，属生态演进
  方向，非本版本范围。
---

**编译结束**: 2026-09-07 11:56
**最终状态**: built

### 2026-09-23 — 源码端点修复（CI 源码下载超时）
- 失败构建：#55982（conan-build-test ❌），诊断=源码下载超时（snapshot.debian.org 在 CI worker 不可达/超时）。
- 修复：conandata 主源切换为 Debian 官方 snapshot 服务的 Cloudflare CDN 前端 `snapshot-cloudflare.debian.org`（同源同字节，sha256 不变 `45e2d4d7…b0786`）；保留 `snapshot.debian.org` 兜底。仓库先例：archives/m/mencoder/38542。
- 本地复验：conan create（日志 ~/tmp/blendsel-w3-cdn.log）通过后再推送。
