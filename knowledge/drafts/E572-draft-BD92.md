# E572 — 老式 config.guess/config.sub 不识别 HarmonyOS/aarch64：最小补丁（+7/-1 行）替代整文件替换（补丁文件 5841 行）

## 错误特征

`./configure` 在平台识别阶段直接失败：

```
config.guess: unable to guess system type

This script, last modified 2003-05-09, has failed to recognize
the operating system you are using.  It is probably necessary to
update your version of this file ...

UNAME_MACHINE = aarch64
UNAME_SYSTEM  = HarmonyOS
UNAME_RELEASE = HongMeng Kernel 1.13.0
UNAME_VERSION = #1 SMP ...
config.guess: unable to guess system type
```

`configure` 侧对应报错（取决于 autoconf 版本）：

```
configure: error: cannot guess build type; you must specify one
```

另一类症状不报错但更隐蔽：`config.sub` 把 triplet 归一成 `aarch64-unknown-linux-gnu`，
`configure` / `libtool` 据此走 **Linux-GNU** 平台分支，老式 libtool 平台表里没有 `linux-ohos`
条目 → `deplibs_check_method` 落到 `file_magic` 判定，共享库/插件链接判定随之为假。

## 触发条件

- 构建系统: autotools（自带 autoconf 2.5x 时代 `config.guess` / `config.sub`，如 2003-05-09 版）
- 阶段: configure（平台识别）
- 平台: HarmonyOS，`uname -s` 返回 `HarmonyOS`（老固件为 `HongMeng`），`uname -m` 返回 `aarch64`

## 根因分析

两个独立原因叠加，必须都修：

1. **config.guess 分支缺失**：2003 版脚本的 `case "${UNAME_MACHINE}:${UNAME_SYSTEM}:..."` 分支表
   只有 `*:Linux:*:*` 一类条目，既没有 `aarch64`，也不认识 `HarmonyOS`/`HongMeng`
   → 落默认诊断分支，打印上面那段 "unable to guess system type"。
2. **config.sub 双重改写**：
   - `maybe_os` 白名单（`nto-qnx* | linux-gnu* | freebsd*-gnu* | ...`）不含 `linux-ohos`，
     于是 `linux-ohos` 被当作机器名的一部分进入后续解析；
   - 通用分支 `-linux*)` 执行 `sed 's|linux|linux-gnu|'`，把 `-linux-ohos` 改写成 `-linux-gnu-ohos`
     （再归一为 `linux-gnu`），OHOS 语义丢失。

> 只修 config.guess 不够：`configure` 会用 `$ac_config_sub`（config.sub）二次归一化 guess 的输出，
> 所以两个文件必须一起改。

## 解决方案

### 推荐方案：最小补丁（共 +7/-1 行）

`patches/0001-config.guess.patch` —— 在 case 首插入一条命中分支（+3 行）：

```sh
 case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in
+    aarch64:HarmonyOS:*:* | arm64:HarmonyOS:*:* | aarch64:HongMeng:*:* | arm64:HongMeng:*:*)
+	echo aarch64-unknown-linux-ohos
+	exit 0 ;;
     *:NetBSD:*:*)
```

`patches/0002-config.sub.patch` —— 两处守卫（+4/-1 行）：

```sh
 # 1) maybe_os 白名单加入 linux-ohos*
-  nto-qnx* | linux-gnu* | freebsd*-gnu* | ...
+  nto-qnx* | linux-gnu* | linux-ohos* | freebsd*-gnu* | ...

 # 2) 在通用 -linux*) 之前截住，避免 linux -> linux-gnu 改写
+	-linux-ohos*)
+		os=-linux-ohos
+		;;
 	-linux*)
 		os=`echo $os | sed -e 's|linux|linux-gnu|'`
 		;;
```

要点：

- 命中分支写在 `case` 首、且 `echo` 直接给出目标 triplet，**不依赖** `set_cc_for_build` 探针
  （探针在受限 TMPDIR / HMDFS 上会因写 `dummy.c` 失败而放大问题）。
- 输出固定 `aarch64-unknown-linux-ohos`，让 `host_os=linux-ohos` 与既有的
  `configure` 平台表补丁（`linux-ohos*` + `deplibs_check_method="pass_all"`）对齐。
- 补丁中**不需要** `__OHOS__` 等平台宏：守卫条件是 `uname` 文本（`HarmonyOS` / `HongMeng`），
  因此不触发 CI 的 R8 平台宏审查，也无需申报例外。
- 与仓库事实标准的整文件替换（OHOS-aware 探针，12 个包复用，sha256
  `02a2b4483f0f6d9514f0b938eba95fb6`）结果**逐字节等价**：`checking build system type... aarch64-unknown-linux-ohos`。

体量对比（cpu 1.4.3 实测）：

| 方案 | 补丁规模 | 审查影响 |
|------|---------|---------|
| 最小补丁（推荐） | +7/-1 行 / 33 行文件 | PR 体量下降 99.8%，AI 检视可正常覆盖 |
| 整文件替换（回退） | 补丁文件 5841 行（config.guess 2631 行 = +1235/-810、config.sub 3210 行 = +1687/-1232） | 单补丁占 PR 69% 行数，审查 bot 判“变更过大/需多轮 review”并跳过 AI 检视 |

### 禁止做法

- ❌ 用 `--host=aarch64-unknown-linux-ohos` 等参数手工指定 triplet 绕过识别链
  （违反 R1/R2 参数最少化；且平台表/libtool 判定与真实环境脱节）。
- ❌ 用 `sed -i` 就地改写 `config.guess`/`config.sub`（破坏 shell 缩进与 `case` 结构，
  且无法回归到 pristine 生成可复用补丁）。
- ❌ 整文件替换后不做上游化说明：数千行 diff 会掩盖真正的适配改动，审查无法逐条核对。

## 验证

```sh
# 1. 脚本层（改动后立即验证，不依赖完整构建）
sh config.guess                          # 期望: aarch64-unknown-linux-ohos
sh config.sub "$(sh config.guess)"       # 期望: aarch64-unknown-linux-ohos（不可被改写为 linux-gnu）
sh config.sub riscv64-unknown-linux-gnu  # 回归: 其它架构/OS 结果不变

# 2. 补丁可精确应用（strict，不允许 fuzz 漂移）
patch -p1 --dry-run < patches/0001-config.guess.patch
patch -p1 --dry-run < patches/0002-config.sub.patch

# 3. 构建层（端到端）
conan create <ver_dir> -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
grep 'checking build system type\|checking host system type' <log>  # 二者均应为 aarch64-unknown-linux-ohos
```

cpu 1.4.3 实测：`sh config.guess` = `aarch64-unknown-linux-ohos`；`conan create` 日志
`checking build system type... aarch64-unknown-linux-ohos` / `checking host system type... aarch64-unknown-linux-ohos`；
`test_package` 11/11 通过（与整文件替换方案完全一致）。

## 关联条目

- 相似: **E007**（config.guess/config.sub 不识别 OHOS —— 本条是其「最小补丁」实施细化）
- 配套: **E046**（HMDFS 上 chmod 无效 → 老式 configure 的 umask 077 需 patch 为 022）
- 原则: P001（鸿蒙是原生编译环境）、P003（生成文件可 patch）、P011（补丁含来源说明）
