# DRAFT — 现代 config.guess/config.sub 的 OHOS 适配（libicns 0.9.0）

## 现象 (What happened)

libicns 0.9.0（kornelski/libicns master）源码**不捆绑任何生成式 Autotools
文件**（无 configure/config.guess/config.sub/Makefile.in/m4），配方的
build() 必须自行 bootstrap（aclocal → autoconf → autoheader → libtoolize →
automake，绕开 HMDFS 上 autoreconf 链的 autoconf.m4f 冲突）。bootstrap
得到的是**现代** 2023-08-22 版 config.guess/config.sub（automake 1.16.5
生成），随后 configure 首跑报两处错误：

1. `checking build system type... ./config.guess: unable to guess system type`
   ——本机 `uname -s` = `HarmonyOS`，现代 config.guess 无匹配分支，C 探测程序
   输出为空。
2. 修完 config.guess 后 `sh config.sub aarch64-unknown-linux-ohos` 仍报
   `Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not recognized`。

另外 config.guess 的临时目录创建 `(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")`
在 HMDFS setgid 父目录下得到 `drwx--S--- 2700`，有效用户无法写入，报
`./config.guess[1733]: can't create .../dummy.c: Permission denied`，进一步
导致 "unable to guess system type"。

## 根因 (Root cause)

- **现代 config.guess 无 HarmonyOS 分支**：2023-08-22 版脚本有 LIBC 探测
  块（`cc_set_libc`），但系统识别 case 仍无 `*:HarmonyOS:*:*`，UNAME_SYSTEM
  = HarmonyOS 落到 C 探测程序且无输出分支 → 空 SYSTEM_NAME → 报 unable。
- **现代 config.sub 的 maybe_os 已覆盖 linux-ohos，但验证列表未含 ohos**：
  现代版 maybe_os 分支用 `nto-qnx* | linux-* | ...` 通配，`linux-ohos` 已被
  `linux-*` 命中，basic_os 直接得 `linux-ohos`——**E072 描述的第 1 处修改
  （android-linux 后加 ohos-linux → basic_os=linux-ohos 映射）在新版脚本不
  再需要**。但 kernel-OS 验证列表（`case $kernel-$os in`）与 OS accept 列表
  （`case $os in` 尾部）仍不含 ohos，三元组被拒（"OS 'ohos' not recognized"）。
- **config.guess 自身 umask 077 临时目录**：E011 已记录 configure/config.status
  的 umask 077 问题（HMDFS uid 错位语义）；本条新增的是 **config.guess 自己**
  也有 3 处 `umask 077 && mktemp -d`（cgXXXXXX 模式），同样触发 Permission
  denied。

## 解法 (Fix)

对 bootstrap 生成的现代脚本做 4 处契约式改写（count 检查，布局变化即
fail-closed，防止静默失效）：

| # | 文件 | 锚点（现代 2023-08-22 版） | 改写 |
|---|------|---------------------------|------|
| 1 | config.guess | `    aarch64:Linux:*:*)` 之前 | 插入 `*:HarmonyOS:*:*` case：按 UNAME_MACHINE 映射 MACHINE（aarch64/arm64→aarch64，armv7*/armv8*→arm，x86_64/amd64→x86_64，i?86→i686，默认原样），`GUESS=${MACHINE}-unknown-linux-ohos` |
| 2 | config.sub | `linux-gnu* \| linux-dietlibc* \| linux-android* \| linux-newlib* \` 续行 `\| linux-musl* \| linux-relibc* \| linux-uclibc* )` | 末尾追加 `\| linux-ohos* )` |
| 3 | config.sub | OS accept 列表尾部 `\| nsk* \| powerunix* \| genode* \| zvmoe* \| qnx* \| emx* \| zephyr*)` | 追加 `\| ohos*)` |
| 4 | config.guess（3 处）+ configure（2 处） | `umask 077` | → `umask 022` |

②③缺一不可：只加 ③ 不加 ② 会报 "Kernel 'linux' not known to work with OS
'ohos'"（E072 同款）；只加 ② 不加 ③ 会报 "OS 'ohos' not recognized"。

## 与既有知识的关系 (vs existing knowledge)

| 条目 | 覆盖部分 | 本条新增部分 |
|------|---------|-------------|
| E007 | config.guess 不识 HarmonyOS（perl 工具打 build-aux 静态文件） | 现代脚本（2023-08-22）锚点；配方内 build() 后对生成文件做契约改写（源码无生成文件，无法静态打 patch） |
| E072 | config.sub 三元组验证 3 处修改 | 现代版 maybe_os `linux-*` 已覆盖，**第 1 处（ohos-linux 映射）不再需要**，只需 kernel-OS + OS accept 两处 |
| E011 | configure/config.status 的 umask 077 | config.guess 自身 3 处 umask 077（cgXXXXXX 临时目录） |
| E052/E060 | config.status 临时目录 | —（互补，非冲突） |
| DRAFT-6507 | mktemp -d 强制 0700 须 mkdir -m 0777 | 本条 config.guess 的 `umask 077 && mktemp -d` 改 022 后实测得 2751 可写，**无需弃 mktemp**——边界差异：cln 场景 mktemp 恒 0700 为真，本条场景 mktemp 受 umask 影响 |
| DRAFT-E564 | 2012 旧式 config.guess/config.sub 换锚点（无 GUESS= 机制） | 现代版（有 GUESS= 机制）互补锚点 |

## 验证 (Verification)

- 手动：插桩+改写后 `sh config.guess` → `aarch64-unknown-linux-ohos`；
  `sh config.sub aarch64-unknown-linux-ohos` 与 `aarch64-linux-ohos` 均 RC=0。
- conan create（ohos-aarch64）：bootstrap 后打补丁 → configure/make/check
  全绿；conan-verify G0-G4 + L2/L4/L5 全 PASS；消费者 test_libicns +
  test_ohos_libicns 实跑 "all checks passed"（2026-09-18，
  reports/conan-create.log，log sha256 8565226876...）。

## 适用边界 / 反例 (Boundaries)

- 适用于源码不含生成式 autotools 文件、需 build() 内 bootstrap 的包，以及
  捆绑 2023-08-22 版（automake 1.16.5 生成）脚本的包。
- 若源码**捆绑**旧式（pre-2016）脚本，走 DRAFT-E564 的换锚点方案；若捆绑
  静态生成文件且可用 perl 工具，E007 的 patch-autotools-ohos.pl 仍为首选。
- cln 类 mktemp -d 恒 0700 场景仍需 DRAFT-6507 的 mkdir -m 0777 方案；本条
  的 umask 022 处方不适用该场景（先实测目录模式再选路）。
