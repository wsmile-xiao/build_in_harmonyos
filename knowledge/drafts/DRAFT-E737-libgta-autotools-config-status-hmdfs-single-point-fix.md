# E737（草稿）：发布版 tarball（自带预生成 configure）在 HarmonyOS + HMDFS 上的两连杀——`config.guess` 不认 uname（第一关）与 `config.status` 暂存目录 2700 不可写（第二关），release 形态下**单点修 configure 即可**，与 autoreconf 族的两段式修法分层

> Draft: DRAFT-E737-LIBGTA-AUTOTOOLS-CONFIG-STATUS-HMDFS-SINGLE-POINT-FIX
> Stem: `DRAFT-E737-libgta-autotools-config-status-hmdfs-single-point-fix` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-E737-LIBGTA-AUTOTOOLS-CONFIG-STATUS-HMDFS-SINGLE-POINT-FIX
- **严重度**: 2
- **类别**: platform | portability | autotools | hmdfs-permission
- **触发工具**: configure | make
- **阶段**: compilation | configuration
- **来源任务**: libgta 1.2.1（平台 id 14210）W0 平台判据 + 探索期一跑两修
- **关联既有条目**: **E007**（config.guess/config.sub 陈旧族整文件补丁）、**DRAFT-E678**（autoreconf 族双杀 + `--build` 与 build() 期 sed 生成物——**本条是其 release-tarball 变体，单点传播结论不同**）、**E114**（HMDFS `umask 077` → 2700）、`device-facts §一.10`（目录模式落盘后不可改、属主映射）

## 错误特征（逐字，`error_signature` 4 条子模式对 4 条原文实测全命中）

**第一关（`config.guess`，2018-02-24 件）**：

```
checking build system type... ./build-aux/config.guess: unable to guess system type

This script (version 2018-02-24), has failed to recognize the
operating system you are using.
uname -m = aarch64
uname -r = HongMeng Kernel 1.12.0
uname -s = HarmonyOS
configure rc=1
```

**第二关（`config.status` 文件生成机制，第一关修好后立即接续踩中）**：

```
config.status: creating ./config.status
./config.status[1008]: can't create ./confbJLGCl/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
configure rc=1   （Makefile/config.h 全不落地）
```

两关日志（`$HOME/tmp/libgta-1.2.1/logs/expl-configure.log` 前后两轮逐字留档）。

## 根因分析

1. **第一关 · 平台识别**：`LT_INIT` 触发 `AC_CANONICAL_BUILD/HOST`，不给 `--build/--host` 时必调 `build-aux/config.guess`；旧件分派表无 HarmonyOS → rc=1。
2. **第二关 · HMDFS 目录 mode law**：autoconf 2.69 文件生成机制用 `(umask 077 && mktemp -d "./confXXXXXX")` 建暂存目录。**HMDFS 对目录的落盘 mode = `0777 & ~umask | setgid`，忽略请求 mode**——A/B 探针（同一 `mktemp -d` 都请求 0700）：

   | umask | 落盘 | `touch` 结果 |
   |---|---|---|
   | 0002 | `drwxrws--x`（2775，组 rwx） | writable-ok |
   | 077 | `drwx--S---`（2700，组/other 无位） | Permission denied |

   进程 euid 非共享属主（`20001006`）、egid 不在 group ⇒ 写 `subs1.awk` 被拒。
3. **单点传播机制（本条核心增量）**：该暂存块在 `configure` 里**只出现一次**，且位于 config.status 装配区（`for ac_config_target` 之后的 heredoc 段）——config.status 由 configure 生成时从该模板拷贝。**修 configure 一处，configure 自身与新生成的 config.status 同时被修**。

## 与既有条目的差异（可执行反证）

**vs DRAFT-E678（autoreconf 族）**——E678 的适用面是「tarball 只带 configure.ac、每次 build 都要 autoreconf 重新生成 configure」，故其正解是「`--build=<triplet>` 绕第一关 + build() 期对**生成物** sed 剥 `umask 077`（不进 git、每次重新生成）」。libgta 是**发布版 tarball 自带预生成 configure**，形态相反：

```sh
# 差异读数 1：release tarball 的 configure 是受跟踪源文件 → 修法可进 patches/
# （autoreconf 族的 configure 是生成物，进 git 会被下一次 autoreconf 覆盖）
grep -c 'umask 077' "$HOME/ws/tmp/builds/libgta-1.2.1.work/configure"     # 修后 = 0
# 差异读数 2：config.status 自动继承，无需 E678/integrit 式「post-configure 第二遍」
grep -c 'umask 077' "$HOME/ws/tmp/builds/libgta-1.2.1.work/config.status"  # 修后 = 0（模板拷贝）
grep -n 'tmp=./conftmp' "$HOME/ws/tmp/builds/libgta-1.2.1.work/config.status" | head -1
# → 795:  tmp=./conftmp &&
# 差异读数 3：不给 --build，config.guess 原生跑通（E678 要求显式 --build）
sh "$HOME/ws/tmp/builds/libgta-1.2.1.work/build-aux/config.guess"           # aarch64-unknown-linux-ohos
```

**vs integrit 的四处归一（多根 + config.status 二遍修）**：integrit 是 autoconf 2.59 生成物、且 `fix` 作用对象要在 source/build 多根里各扫一遍（autoreconf 族形态）。2.69 release tarball 形态下**只需对 configure 源文件两处替换**，`config.status` 由模板继承——实测单点后 `creating Makefile/config.h` 全量落地、rc=0。**两段式在这里是多余的复杂度；反过来若在 autoreconf 族只修源 configure 而不在 build() 期修生成物，则完全无效**（E678 的顺序硬约束仍然成立）。分层判据：`configure` 在 git 里是「源」还是「生成物」。

**vs E114 / §一.10**：既有条目记的是「`mkdir(...,0700)` → 落盘 2700 → 不可写」这**一个方向**；本条探针把 law 收紧为「**mode 完全由 umask 决定、请求 mode 被忽略**」——同一 `mktemp -d`（恒请求 0700）在不同 umask 下落盘 2775/2700 两态，解释了「为什么剥掉 `umask 077` 就够、改 mktemp 不必要」。

## 修法（rec）

1. **第一关（E007 族正解，release 形态）**：`build-aux/config.guess`、`build-aux/config.sub` 整文件升级 2026-05-17 GNU config + `config.guess` 主 case 注入 `*:HarmonyOS:*:*` → `aarch64-unknown-linux-ohos`。**不给 `--build/--host`**（R1），判据 `checking build system type... aarch64-unknown-linux-ohos`。
2. **第二关（单点）**：对 configure 源文件两处归一：
   - 主：`tmp=\`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null\` && test -d "$tmp"` → `tmp=./conftmp && (umask 022 && mkdir -p "$tmp") && test -d "$tmp"`
   - fallback：`(umask 077 && mkdir "$tmp")` → `(umask 022 && mkdir -p "$tmp")`
   - 残余判据：`grep -c 'umask 077' configure` = 0；生成物 `config.status` 同为 0。
3. **落地**：`refresh-patch --auto`（编辑追踪器精准模式）→ `patches/0001-0003` + conandata 登记；三关自检 NUL=0 ∧ hunk≥1 ∧ 对 `.orig` apply rc=0。
4. **反静默**：修复后必须见 `config.status: creating Makefile` + `test -f Makefile && test -f config.h` 才进 make（rc=0 但生成物缺失 = 假绿，见止损先例 #9）。

## 验证（设备可直接执行）

```sh
# 两关复现（修复前日志）
grep -nE 'unable to guess system type|could not setup config files machinery|subs1.awk: Permission denied' "$HOME/tmp/libgta-1.2.1/logs/expl-configure.log"
# 单点传播自证
W=$HOME/ws/tmp/builds/libgta-1.2.1.work
grep -c 'umask 077' "$W/configure" "$W/config.status"       # 双 0
grep -n 'tmp=./conftmp' "$W/config.status" | head -1          # 795 行命中
test -f "$W/Makefile" && test -f "$W/config.h" && echo gen-ok
sh "$W/build-aux/config.guess"                                 # aarch64-unknown-linux-ohos
# HMDFS mode law A/B
cd "$HOME/ws/tmp" && d1=$( (umask 002; mktemp -d e737aXXXXXX) ) && ls -ld "$d1" && touch "$d1/x" && echo writable-ok; rm -rf "$d1"
cd "$HOME/ws/tmp" && d2=$( (umask 077 && mktemp -d e737bXXXXXX) ) && ls -ld "$d2" && (touch "$d2/x" || echo denied); rm -rf "$d2"
```
