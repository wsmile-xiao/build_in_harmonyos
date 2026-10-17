# DRAFT: 老 config.guess/sub 不识 HarmonyOS + autoconf `umask 077` 临时目录在本设备必炸

- **草稿 ID**: DRAFT-E685-autotools-legacy-configscripts-harmonyos-hmdfs-umask
- **来源库**: simstring 1.0（OHOS PC aarch64, clang 15.0.4 / OHOS SDK 26.0.0.18, HongMeng Kernel 1.12.0）
- **状态**: 草稿（待主编 promote 为正式 E 条目）
- **同族条目**: E007（平台三元组）、E110 / E125（config.status 临时目录权限）

## 问题（两处独立机制，均真机实测）

simstring 1.0 是 2010-03 的 autotools 发行包（bundle 的 `config.guess`/`config.sub`
时间戳 2009-04-27），在本设备 `./configure` 连续撞两道闸：

### 闸 1：老 config 脚本不识 HarmonyOS / aarch64

```
UNAME_SYSTEM  = HarmonyOS
configure: error: cannot guess build type; you must specify one
```

官方一键脚本 `scripts/patch-autotools-ohos.pl`（E007 推荐）**对老基线只成功一半**：

```
[ok] Added HarmonyOS system identification   (config.guess)
Score: 1/5
❌ Some patches may have failed.
patch_rc=1
Invalid configuration `aarch64-unknown-linux-ohos': machine `aarch64-unknown-linux' not recognized
```

根因：脚本的定位锚（`__ANDROID__/LIBC=android`、`android-linux`、`linux-uclibc`）
只存在于现代 config 脚本，老基线上 config.sub 的改动全部 `[warn] Could not find ...`，
于是 guess 打出来了、sub 不认（`grep -c aarch64 config.sub` = 0）。

对照：把设备 automake-1.19 自带现代版（`timestamp='2026-05-17'`，含全部锚点）
先整体替换、再跑同一脚本 → `cg=2 sub=1, Score 4/5, rc=0`，
`sh ./config.guess` → `aarch64-unknown-linux-ohos`。

### 闸 2：`umask 077 && mktemp -d "./confXXXXXX"` 必炸（E110/E125 的真实根因）

闸 1 修完后 configure 仍死在：

```
./config.status[758]: can't create ./confDjHabc/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

真根因不是"HMDFS 限制临时文件"这种环境玄学，而是**属主映射 + 丢 group-w**：

| 事实 | 读数 |
|---|---|
| 进程 euid/egid | `20020085`（groups 含 1006） |
| 任何落盘目录的属主 | 恒 `20001006`，gid `1006` |
| 写权限来源 | 只剩共享组 group-w |

autoconf（2.6x 与 2.7x 同款）内置 `umask 077 && mktemp -d "./confXXXXXX"`，
而** toybox `mktemp -d` 的目录权限对 umask 敏感**（三态实测）：

```
umask 077 → drwx--S--- (042700) → touch: Permission denied   ← configure 采用
umask 022 → drwxr-s--x (042755) → 写入 OK
umask 002 → drwxrws--x (042775) → 写入 OK
```

owner=20001006 但 euid=20020085 ⇒ 0700 目录没有任何可用的写路径 ⇒
config.status 写 `subs1.awk` 必失败；`configure` 内嵌同一模板，
**由它生成的 config.status 继承同款代码，只改 configure 一处即可双修**。

同时证伪 E110/E125 的推荐方案：**换 VPATH/非 HMDFS 构建目录在同文件系统下无效**
（同一 mktemp+umask+属主映射机制），只会把失败挪进新目录。

## 方案（两条最小补丁，仓内先例同形）

1. **config.guess**（老基线）：在主 case `case "${UNAME_MACHINE}:${UNAME_SYSTEM}:...`
   首分支前插入 HarmonyOS 分支——按 `UNAME_MACHINE` 映射 aarch64/x86_64/i686 后
   `echo ${MACHINE}-unknown-linux-ohos; exit`（语义 = 官方脚本对现代基线的产出）。
   **config.sub** 加三处：maybe_os 组合表 `linux-ohos*`、CPU 表 `aarch64`、
   os 字段表 `-linux-ohos*`（a52dec `0001-config-sub-aarch64.patch`、
   aalib `0001-config.sub-ohos.patch` 同形）。
2. **configure** 两处 `umask 077 &&` → `umask 022 &&`（mktemp 与 mkdir 回退分支），
   a52dec `0002-configure-umask-022.patch` 正是此形。

**禁止** `--build=`/`--host=`（E007：翻成 cross_compiling=yes → AC_RUN_IFELSE 全跳过、
config.h 失真）。native 成功判据：`checking build system type... aarch64-unknown-linux-ohos`
且未传 --build/--host。

## 复现命令（设备可直接执行，落 $TASK_DIR）

```sh
. "$HOME/tmp/simstring-1.0/env.sh"
# 闸 2 umask 三态
cd "$TASK_DIR/w0"
( umask 077; d=$(mktemp -d permAXXXXXX); ls -ld "$d"; touch "$d/x"; echo rc=$? )   # drwx--S--- rc=13
( umask 022; d=$(mktemp -d permBXXXXXX); ls -ld "$d"; touch "$d/x"; echo rc=$? )   # drwxr-s--x rc=0
# 闸 1 官方脚本老基线半成功（工作树内）
perl "$TARGET_REPO/scripts/patch-autotools-ohos.pl" config.guess config.sub       # rc=1, Score 1/5
# 修后全链
sh ./config.guess            # aarch64-unknown-linux-ohos
sh ./configure --prefix="$DEFAULT_PREFIX"   # rc=0（两处补丁均已落）
```

## 影响面

- **闸 1**：一切 bundle 老 GNU config 脚本（时间戳 <2011、CPU 表无 aarch64）的
  autotools 包——与 E007 的关系是「脚本适用基线」判据：脚本自检 Score <4 或 rc≠0
  即判"老基线"，走手写最小补丁或先升级基线。
- **闸 2**：一切跑 autoconf configure 的包（idiom 是 autoconf 内置、与包无关）；
  本设备上任何以 `umask 077` 建目录再写入的路径同理（`config.guess` 的
  `cgXXXXXX/dummy.c` 探针也撞过同一机制，报错后落入兜底分支）。
