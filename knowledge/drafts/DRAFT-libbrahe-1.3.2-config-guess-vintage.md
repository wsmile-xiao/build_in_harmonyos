# 老世代 config.guess/config.sub 上 patch-autotools-ohos.pl 失效：需要世代感知的最小三元组补丁

- **草稿 ID**: DRAFT-libbrahe-1.3.2-config-guess-vintage
- **来源**: libbrahe/1.3.2 适配（任务 8135，分支 `feat/libbrahe-1.3.2`，设备 OHOS PC aarch64）
- **分类**: autotools / configure / platform-detection / triplet / config.guess / config.sub
- **状态**: 本地草稿（未生成知识编号，无远端链接，无审核结论；提升与否由知识库主编决定）

## 问题 / 错误签名

对随包 `config.guess`(timestamp 2009-12-30) / `config.sub`(timestamp 2010-01-22) 的包，
按 E007/E205 的推荐命令执行一键补丁脚本会「看似执行、实际无效」：

```
$ perl scripts/patch-autotools-ohos.pl config.guess config.sub
[warn] Could not find __ANDROID__/LIBC=android in config.guess
Patching config.guess...
  [ok] Added HarmonyOS system identification
Patching config.sub...
  [warn] Could not find android-linux in config.sub
  [warn] Could not find linux-uclibc pattern in config.sub
Done. cg=1 sub=0 change(s).
--- Verification ---
config.guess: __OHOS__=0 HarmonyOS=1
config.sub:  ohos-linux=0 ohos*=0 linux-ohos=0
Score: 1/5
❌ Some patches may have failed.     # rc=1
```

紧接着 `./configure` 仍然失败（实测两条）：

```
config.guess: unable to guess system type
This script, last modified 2009-12-30, has failed to recognize the operating system you are using.
uname -s = HarmonyOS        # HongMeng Kernel 1.12.0，aarch64
./config.sub aarch64-unknown-linux-ohos
Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
```

关键判别命令（30 秒内可判定包属于哪个世代）：

```sh
grep -m1 "^timestamp=" config.guess config.sub
grep -c "android-linux\|linux-uclibc\*- )\|__ANDROID__" config.sub config.guess
sh config.sub aarch64-unknown-linux-gnu    # 老 config.sub 其实已经能直通 aarch64-*-linux-gnu
```

## 根因

1. **config.guess 的插入形态与老脚本结构不匹配**。脚本按新版 GNU config 的结构插入
   `GUESS=${MACHINE}-unknown-linux-ohos` 赋值；而 2012 年以前的 config.guess 是「每个 case 分支自己
   `echo <triplet> ; exit 0`」的写法（本包 case 起于 `config.guess:145`，其后全是机器限定分支，
   例如 `arm*:Linux:*:*)` 在 875 行、`x86_64:Linux:*:*)` 在 974 行；既无 `aarch64:Linux:*:*)`，
   也没有通配的 `*:Linux:*:*)`），赋值形式的分支不会终止脚本，控制流继续向下落到
   `unable to guess system type` 出口。所以日志显示 `[ok] Added HarmonyOS system identification`，
   但功能上完全无效（实测 `sh config.guess` 仍 rc=1）。插入点因此要在 case 顶部（`*:NetBSD:*:*)` 之前）
   才能先于任何机器限定分支命中。
2. **config.sub 的三处锚点在 2010-01-22 版中不存在**：`android-linux` 分支、`case $os` 的 ohos 白名单位、
   `linux-uclibc*-` 内核组合行全部 grep 不到（取证回执里四处锚点计数均为 0）。该 perl 脚本对 config.sub
   只打印两条 `[warn]`（`Could not find android-linux in config.sub`、
   `Could not find linux-uclibc pattern in config.sub`），第三处 OS 白名单没有 warn 分支、属静默不写，
   因此「未生效」的判定应以两行为准：`config.sub:  ohos-linux=0 ohos*=0 linux-ohos=0` 与
   `Done. cg=1 sub=0 change(s)`（写入 0 处）。取证回执：
   `task-data/libbrahe-1.3.2/refs/perl-probe-20260918-134200.log`
   （sha256 `e6e320db4487300ff47f9497aba19028f3837210a67ec166bb5fcc3bddb6bcfd`）。
3. **两个失败面容易被误当成同一个问题**：老 config.sub 对 `aarch64-*-linux-gnu` 是直接回显通过的，
   真正的缺口只有 `linux-ohos` 这一组合。若照搬「补 aarch64」或「补三处白名单」的思路，
   会补在不存在锚点的位置上（E072/E122 描述的三处修改面向的是有这些锚点的较新脚本）。

## 最小修复方案（实测有效）

只加两处、不动生成链，全部落在包目录 `patches/` 内：

1. `config.guess` — 在 `case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in`
   之后插入 **echo 形态** 分支（放在其它分支之前）：

   ```sh
       *:HarmonyOS:*:*)
           echo "${UNAME_MACHINE}-unknown-linux-ohos" ; exit 0
           ;;
   ```

   （文档示例用空格排版；`patches/0001` 内沿用 config.guess 原有分支的制表符缩进。）

2. `config.sub` — 在 `# Separate what the user gave into CPU-COMPANY and OS or KERNEL-OS (if any).`
   之前插入 early-exit 直通块，绕开该版本根本不存在的 ohos 白名单：

   ```sh
   case $1 in
     aarch64-*-linux-ohos | arm-*-linux-ohos | armv7-*-linux-ohos | x86_64-*-linux-ohos)
       echo "$1"
       exit 0
       ;;
   esac
   ```

两条补丁都不含 `__OHOS__` 平台宏（PF5/R8 口径），也不改 `configure.ac`（该包 configure 为 autoconf
生成物、umask 段不来自 configure.ac，另见 E011）。

## 实际验证结果（设备实测，libbrahe 1.3.2）

| 步骤 | 修复前 | 修复后 |
| --- | --- | --- |
| `sh config.guess` | rc=1 `unable to guess system type` | `aarch64-unknown-linux-ohos`，rc=0 |
| `sh config.sub aarch64-unknown-linux-ohos` | rc=1 `Invalid configuration` | 原样回显，rc=0 |
| `./configure --prefix=<任务私有>` | 在 build type 判定处失败 | rc=0 |
| `make -j2` / `make install` | — | rc=0；6 个上游测试程序全部执行 |
| `conan create`（含 test_package 消费者 43 断言） | — | 逐条门禁记录在设备工作树 `archives/l/libbrahe/1.3.2/reports/`；其中 `test-report.md` 按仓库规则 19 不入 PR，可核对事实同时写入 `notes.md` 与 PR 正文 |

关键连带事实（解释了为什么不必用 `--build/--host`）：直通块回显的仍是 `aarch64-unknown-linux-ohos`，
实测 `config.log` 记录 `build='aarch64-unknown-linux-ohos'`、`host='aarch64-unknown-linux-ohos'`、
`host_os='linux-ohos'`（autoconf 取第二个连字符之后的部分），且 `configure` 自报
`checking whether we are cross compiling... no`；因此 **2008 世代 libtool 的 `linux*)` 分支仍然命中**，
库命名、`-release`、静态/共享判定等行为与 Linux 一致，也没有触发 `cross_compiling=yes`
（E007 forbid_1 / E011 forbid_1 的禁令保持成立）。
注意 `archives/a/a52dec/0.7.4/conanfile.py` 走的是 `--build/--host=aarch64-unknown-linux-gnu` 伪装路线，
属本条禁止的形态，不应作为新任务的模板。

## 适用范围

- 随包 `config.guess`/`config.sub` 时间戳早于约 2012 年的 autotools 项目（含本任务清单里大量
  2005–2012 上游最后发布、由 Debian 维护原包的软件）。
- 需要输出标准 OHOS 三元组、同时不希望引入 `--build/--host` 语义副作用的适配任务。
- 判定顺序建议：先看时间戳 → 有 `android-linux`/`linux-uclibc*-` 锚点则走 E007/E205 的 perl 脚本
  并按 E268 复核 kernel 行 → 无锚点则用本条两处最小补丁。

## 非适用边界

- 2024+ 版 config.sub 的 linux-ohos kernel 校验缺失场景：那是 E268 的范围，本条不重复其结论。
- 内嵌第三方子项目自带老 config.guess 的包（如 pkg-config 内嵌 glib）：主包补丁覆盖不到，
  仍受 build-systems.md §3.6「内嵌依赖」策略约束。
- 不使用 autoconf 三元组机制的构建系统（CMake/Meson/裸 Makefile）不适用。
- 本条不主张「HarmonyOS 等价于 Linux 用户态」这一更强结论：仅描述为了让 config.guess 产出
  `*-linux-ohos` 所需的最小脚本改动及其连带行为。

## 查重差异（编号跨主线与相关工作树核对）

| 既有条目 | 覆盖内容 | 与本条差异（增量） |
| --- | --- | --- |
| E007 | config.guess 不识别 HarmonyOS 的现象 + 一键 perl 脚本 + 禁用 `--build/--host` | 未区分脚本世代；其 `rec_command`（perl 脚本）在 2009/2010 世代实测无效（本条给出实测证据与可用形态） |
| E160 | 提出 `sed` 方式给 config.guess 加 HarmonyOS 分支（识别为 Linux + LIBC=musl） | 其 `rec_command` 的 `case $UNAME_SYSTEM in` 锚点在本世代脚本中不存在（该版本是四元组 `"$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION"` 单 case 结构），且给出的三元组是 `linux-gnu` 而非标准 `linux-ohos` |
| E072 | config.sub 三处白名单修改（ohos-linux 映射 / OS 白名单 / kernel-os 白名单） | 面向**有** `android-linux`、`linux-uclibc*-` 锚点的较新 config.sub；本条实测这三处锚点在 2010 版全部缺失，改用 early-exit 直通块 |
| E122 | `case $kernel-$os-$obj` 需补 `linux-ohos*-` | 同一现象的白名单细节，仍要求脚本里存在该 case 块；本条不依赖它 |
| E205 | 统一口径：打 perl 脚本、绝不用 `--build/--host` | 与 E007 同源，未涉及老世代失效问题 |
| E268 | perl 脚本对 **2024+** config.sub 误判跳过 kernel 校验补丁 | 与本条互补的另一端（新世代）；本条覆盖 2012 年前老世代，并给出 30 秒世代判定命令 |
| 归档先例 | `archives/a/a52dec/0.7.4/patches/0001-config-sub-aarch64.patch`（aarch64 白名单 + 另用 `--build/--host`）、`archives/a/aiksaurus/.../0002-config.sub.patch`（整文件替换 1549→1964 行） | 本条给出的是比重复整文件替换更小、且不引入 `--build/--host` 语义副作用的形态 |

增量结论：把「OHOS 三元组支持」从单一命令升级为**按 config.guess/config.sub 世代分支的决策**，
并给出老世代可复制的两处最小补丁 + 验收命令 + 为什么这样仍不违反 `--build/--host` 禁令的实测依据。

## 关联交付

- 与 `archives/l/libbrahe/1.3.2/**`（配方 `patches/0001-config.guess-harmonyos-triplet.patch`、
  `patches/0002-config.sub-ohos-triplet.patch`）同属一个 PR（`feat/libbrahe-1.3.2`）。
- 本轮只生成草稿，不自行 promote、不修改他人条目、不改 `knowledge/graph/index.tsv` 与 SUMMARY；
  最终编号由知识库主编审核确定。
