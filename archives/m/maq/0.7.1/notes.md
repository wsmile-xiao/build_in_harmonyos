# maq 0.7.1 — HarmonyOS PC 适配笔记

## 软件概述
MAQ（Mapping and Assembly with Qualities）是短读比对 / 一致性组装 / SNP 检测套件，
作者 Heng Li（lh3），SourceForge 项目 `maq`。0.7.1 发布于 2008-09-26（SVN r672）。
源码为 C/C++ 混编（23 个 .cc + 16 个 .c，主体 C++，链接用 CXXLINK），
构建产物为单个 CLI 工具 `maq`（子命令式：fasta2bfa/fastq2bfq/map/mapmerge/assemble/
glfgen/indelpe/cns2* 等 30+ 个子命令）+ 4 个随装 perl 前端脚本。

## 源码来源
- 官网：https://maq.sourceforge.net/ ；项目页：https://sourceforge.net/projects/maq/
- 源码包：`maq-0.7.1.tar.bz2`（tarball，85 条目）
- 官方 CDN 直链：`https://downloads.sourceforge.net/project/maq/maq/0.7.1/maq-0.7.1.tar.bz2`
  （SourceForge `/download` 页面重定向不携带扩展名，会误导解压器识别格式，故用 CDN 直链）
- sha256：`e1671e0408b0895f5ab943839ee8f28747cf5f55dc64032c7469b133202b6de2`
- 上游为 SVN 托管（`git ls-remote https://git.code.sf.net/p/maq/code` → repository not found），
  无官方 git tag；版本锚点 = tarball 0.7.1（`configure.ac:1 AC_INIT(MAQ, 0.7.1)`、`NEWS` 首行）。

## 编译环境
- 构建系统：autotools（tarball 自带 configure / Makefile.in，无 automake 也可构建）
- 编译日期：2026-09-30
- 编译器：clang 15.0.4 / clang++（OHOS aarch64，`os=OHOS arch=armv8 compiler=clang`）
- 宿主三元组（补丁后）：`aarch64-unknown-linux-ohos`
- 状态：built

## 编译步骤
1. `source()`：下载 tarball 并解压（strip_root）
2. `apply_conandata_patches`：应用 13 个 OHOS 适配补丁（见下）
3. `AutotoolsToolchain` + `Autotools.configure()`：`./configure --prefix=...`
   （zlib 头/库路径由 Conan toolchain 注入 `CPPFLAGS`/`LDFLAGS`）
4. `make -j1` → 单个可执行 `maq`
5. `Autotools.install()`：安装 `bin/maq` + `bin/{maq.pl,farm-run.pl,maq_plot.pl,maq_eval.pl}`

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 |
|---|----------------------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one`（`config.guess timestamp = 2006-07-02`） | 上游 2006 年版 `config.guess` 无 HarmonyOS 分支，`uname -s` = HarmonyOS 不匹配任何模式 | 知识库 **E007** → `scripts/patch-autotools-ohos.pl` 加 HarmonyOS 识别；但该分支原样只赋值 `GUESS=` 不输出（2006 版脚本按 `echo + exit` 输出），且 `*:HarmonyOS:*:*` 模式因 `uname -v`（`#1 SMP Wed Apr 29 10:16:03 UTC 2026`）含冒号而失配 → 补丁 0001 改为 `*:HarmonyOS:*` + `echo ${MACHINE}-unknown-linux-ohos; exit 0`；补丁 0002 给 2006 版 `config.sub` 加 `linux-ohos` kernel-os、`aarch64` CPU、`aarch64-*` cpu-company 支持 |
| 2 | `config.status[641]: can't create ./conflgEhOM/subs1.awk: Permission denied` → `could not setup config files machinery` | `configure`/`config.status` 以 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录，HMDFS 下 0700 目录对当前进程不可写 | 知识库 **E011** → 补丁 0003 将 `configure` 内 2 处 `umask 077` 改为 `umask 022`（configure 为生成文件，但 tarball 无 automake 无法 autoreconf，属 build-systems.md §3.6 层级②可接受） |
| 3 | `./stdhash.hh:415:13: error: explicit qualification required to use member 'direct_insert_aux' from dependent base class`（mapcheck.o 编译失败） | clang 15 严格两阶段名字查找：派生类模板访问依赖基类成员须显式限定；2008 年 GCC 容忍非限定调用 | 补丁 0013：`stdhash.hh` 3 处 `direct_insert_aux(...)` 改为 `this->direct_insert_aux(...)`（知识库未命中，已生成草稿待评审） |
| 4 | `maq.pl easyrun` 失败：`sh: .../scripts/maq.pl: No such file or directory`（文件存在且 0755） | 上游 perl 脚本 shebang 为 `#!/usr/bin/perl`，OHOS 该路径不存在（perl 在 `/data/service/hnp/bin/perl`），exec 报 ENOENT | 补丁 0004-0012：9 个 `scripts/*.pl` shebang 统一改 `#!/usr/bin/env perl`（与仓内 abi-compliance-checker 等先例一致） |

## 源码修改（patches/，共 13 个）

| 补丁 | 内容 |
|------|------|
| 0001-config.guess.patch | HarmonyOS 识别 + 输出 `aarch64-unknown-linux-ohos` |
| 0002-config.sub.patch | 接受 `linux-ohos` kernel-os / `aarch64` CPU / `aarch64-*` |
| 0003-configure.patch | config.status 临时目录 `umask 077 → 022`（HMDFS） |
| 0004-0012-scripts-*.pl.patch | 9 个 perl 脚本 shebang → `#!/usr/bin/env perl` |
| 0013-stdhash.hh.patch | `this->direct_insert_aux(...)`（clang 两阶段查找） |

> 注：`refresh-patch --auto` 生成的补丁同时包含个别行尾空白的规范化（代码规范要求），
> 已核对，无功能改动。

## 依赖版本
- `zlib/1.3.2`（唯一强制第三方依赖；`Makefile.am:8 maq_LDADD = -lm -lz`，`configure.ac:43 AC_CHECK_HEADER(zlib.h)`）
- libm / libc / libc++：工具链 sysroot 自带
- perl 5.42（`/data/service/hnp/bin/perl`）：perl 前端脚本运行时需要（非 conan 包）
- zlib 无传递依赖（`archives/z/zlib/1.3.2/conanfile.py requirements(): pass`）

## 上游测试结果
上游 **无自动化测试套件**（tarball 85 条目内无 `tests/`、无测试源与样例数据；
`Makefile.am` 无 `TESTS`/`check_PROGRAMS`；`configure.ac` 无 `AC_CONFIG_TESTDIR`；
`make check` 为 automake 空目标）。因此按 `maq.pod`（man 手册）文档化的接口构造真实样例，
逐命令执行并统计：

- 测试命令：`bash /storage/Users/currentUser/Desktop/ran_workspace/maq-logs/upstream/run_all.sh`
- 用例总数 **45**，通过 **45**，失败 **0**，跳过 **0**（`maq` 顶层 34 个子命令覆盖 33 个；`mapass2maq` 因上游 pod 未文档化且无 mapass2 格式样例输入，未实测）
- 结果表：`maq-logs/upstream/RESULTS.tsv`；逐用例日志：`maq-logs/upstream/case_T*.log`
- 覆盖：上游 EXAMPLES 全流程（fasta2bfa / fastq2bfq / map / mapmerge / assemble）+ 全部主要子命令
  （mapcheck/pileup/mapview/mapstat/mapvalidate/submap/cns2fq/cns2snp/cns2view/cns2ref/cns2win/
  snpreg/subpos/glfgen/rmdup/indelpe/indelsoa/fasta2csfa/sol2sanger/bfq2fastq/fakemut/simutrain/
  simulate/simustat/simucns/eland2maq/export2maq/novo2maq）+ perl 前端（`maq.pl easyrun`、`maq.pl demo`）
- 鸿蒙（OHOS）专项 **5 条**：ELF AArch64 架构、动态段/interpreter 可解析、NEEDED 依赖清单、
  RUNPATH/RPATH 状态、staging 安装产物可运行（`make install` 后直接执行）

## 验证结果

```bash
# 1) conan create（真实构建 + test_package）
$ python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify maq 0.7.1
# 2) 上游样例套件（见上，45/45 PASS）
$ bash maq-logs/upstream/run_all.sh
# 3) 安装产物
$ <package_folder>/bin/maq        # 打印 Version: 0.7.1 与 30+ 子命令用法
```

## 注意事项
- `maq` 无参数时打印用法到 **stderr** 并以 rc=1 退出（上游行为，非缺陷）；test_package 已按此断言。
- `cns.cns` 为 gzip 压缩的自有格式，不能按文本 grep；内容断言需经 `maq cns2ref`。
- `indelpe` 仅支持短插入 mate-pair（插入约 100bp 量级）；长插入时上游会打印
  `the indel detector only works with short-insert mate-pair reads.`
- HMDFS 上 `mktemp -d` 目录不可写（E011/E112）：test_package 用 `mkdir -p "$PWD/maq-testwork"`，
  不使用 `mktemp -d`。

## 对话

### 对话 #

- **2026-09-30 · 任务：maq/0.7.1 适配 HarmonyOS PC（aarch64/clang 15）**
  1. 依赖（W0）：唯一强制第三方依赖 `zlib/1.3.2`，配方级 + 二进制级 `conan download` 均 rc=0。
  2. 首个错误：`configure: error: cannot guess build type; you must specify one`
     （config.guess 2006 版无 HarmonyOS 分支）→ 知识 E007 + 手工补齐 config.sub →
     补丁 0001/0002。
  3. 第二错误：`config.status` 报 `can't create ./conflgEhOM/subs1.awk: Permission denied`
     （HMDFS + `umask 077`）→ 知识 E011 → 补丁 0003。
  4. 第三错误：`./stdhash.hh:415:13: error: explicit qualification required to use member
     'direct_insert_aux' from dependent base class`（clang 两阶段名字查找）→ 补丁 0013，
     知识库未命中 → 生成草稿 DRAFT-maq-0.7.1-stdhash-dependent-base-this-qualifier。
  5. 第四错误：`maq.pl easyrun` 报 `scripts/maq.pl: No such file or directory`
     （shebang `/usr/bin/perl` 在 OHOS 不存在）→ 知识 E049 → 补丁 0004-0012。
  6. 构建：`./configure` rc=0 → `make -j1` rc=0 → `make install DESTDIR=$TEST_PREFIX` rc=0。
  7. 上游测试：上游无自动化测试套件 → 按 `maq.pod` 文档接口执行 **45 项真实样例**
     （45 PASS / 0 FAIL / 0 SKIP，含 5 项 OHOS 平台专项），日志 `maq-logs/upstream/`。
  8. 配方：`conan create` rc=0（test_package PASS）；`conan-verify` G0-G4 全 PASS；
     `finish maq 0.7.1 built` 的 W3 本地 CI 模拟通过。
---

**编译结束**: 2026-09-30 01:03
**最终状态**: built
