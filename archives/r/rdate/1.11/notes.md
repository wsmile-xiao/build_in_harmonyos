# rdate 1.11 — 适配笔记

任务：平台 10032｜档位【易】｜语言 c｜构建系统 autotools（tarball 无生成版 configure）｜首次适配
上游：https://github.com/resurrecting-open-source-projects/openrdate（经 Debian pool orig tarball 引入）
源码：`rdate_1.11.orig.tar.gz` 20210 B，sha256 `931c4ad143421e516bfd8c964a6e125ec193d5f1e524262a8a6a011181df4721`（与 Debian 索引 Checksums-Sha256 一致）

---

## 1. libbsd 假依赖的卸除（本包核心适配点）

- **依赖面实测**：SCT 台账写「无外部依赖」但漏了 libbsd——`configure.ac:39-40` 硬检
  `bsd/stdlib.h`（缺失即 `exit -1`）、`src/Makefile.am:12` 硬编码 `rdate_LDADD = librdate.a -lbsd`；
  而全源码树对 libbsd 符号的**唯一消费点**是 `src/ntp.c:62` 的 include 与 `:287` 的一次 `arc4random()`。
- **OHOS 实测**：musl 的 `<stdlib.h>` 直接提供 `arc4random()`（链接探针 `~/tmp/uc2/z35-rdate/ar4-probe.c`
  rc=0）。⇒ libbsd 在 OHOS 是**假依赖**。
- **制品仓核验**：`conan download libbsd/0.12.2 --only-recipe -r ohpcd` 报 `system acceleration policy
  not enabled`（同轮对照 zlib rc=0）⇒ libbsd 未发布。即便走依赖适配链也无制品证据可用，卸除假依赖是唯一正解。
- **补丁 0001（三处）**：① configure.ac 删硬检；② ntp.c `#include <bsd/stdlib.h>` → `#include <sys/types.h>`；
  ③ src/Makefile.am 的 LDADD 去掉 `-lbsd`。

## 2. u_char 与 musl 特性宏默认值（含一次失败的探索路径，留档防重蹈）

- `ntp.c` 全篇使用 `u_char`；musl 在 `sys/types.h:64` 于 `_GNU_SOURCE || _BSD_SOURCE` 分支下定义它；
  glibc 默认 `_DEFAULT_SOURCE` 自动暴露 ⇒ 上游从未意识到这个依赖。
- **弯路**：第一版尝试 `-D_BSD_SOURCE` extra_cflags——**仍然失败**。根因：ntp.c 的 include 集
  （sys/param.h / sys/socket.h / netinet/in.h 等）在 musl 下**没有一条会把 sys/types.h 带进来**
  （glibc 的 sys/param.h 会；musl 用 __NEED_ 机制按需取类型，不含 u_char），命令行 define 无头可作用。
- **终解**：补丁 0001 显式引入 `<sys/types.h>` 后，musl 的 features.h 在"未定义任何特性宏"时自动置
  `_BSD_SOURCE`（features.h:13-15；openrdate 自身不定义任何特性宏），u_char 直接可见——实测 ntp.o
  编译通过，无需任何额外 define。

## 3. adjtime(3) 缺失 → adjtimex(2) shim（E534 家族，判 hit）

- 链接期 `undefined symbol: adjtime`（ld.lld 建议 adjtimex；实测留痕 create-r1 前版日志）。
  musl 只有 `adjtimex(2)`，`adjtime(3)` 这层 BSD/glibc 便利封装不存在；`rdate.c:209` 的 `-a` 渐调模式用到。
- **补丁 0002**：`!HAVE_ADJTIME` 守卫的 adjtime shim，基于 `ADJ_OFFSET_SINGLESHOT`——与 glibc 自身
  adjtime 的内部分层完全一致；真实 libc 提供方可 `-DHAVE_ADJTIME` 选出。

## 4. autotools 家族复用（判 hit，不新建草稿）

- tarball 无生成版 configure ⇒ `autoreconf -fi`（probabel 先例）；E386：autoreconf/configure/make 全程
  `env -u CONFIG_SHELL SHELL=/bin/sh` 路由；E011/E114：configure 的 `umask 077` 移除。
- **构建机 automake 代际差异（CIW-8 2026-09-26 整改留档）**：A 机系统 automake 1.16.5（`~/usr/local/bin`，GNU
  automake 1.16.5）随附 2023 版 config.guess/config.sub，实测原生识别 `aarch64-unknown-linux-ohos`——原记「E544
  例外留档」那句就出自这里。但 CI worker 上没有 automake/aclocal/libtoolize，本配方按 E178 以 `tool_requires` 引
  ohpcd 上唯一在册的 automake/1.18（1.16.x/1.17 精确检索均 not found），其随附 aux 件是 2024-07-27 版、**无
  HarmonyOS 分支**（`uname -s` = HarmonyOS、内核 HongMeng Kernel 1.12.0），于是 configure 报
  `cannot guess build type; you must specify one` ⇒ **本包需要** E007（patch-autotools-script）成对补丁，施加位置
  在 build() 内、`autoreconf -fi` 之后：aux 件由 autoreconf 现场安装、不在 tarball 里，conandata 补丁够不着。
  ⛔ 不用 `--build/--host` 绕过（E007/E205：configure 会当交叉编译、跳过 AC_RUN_IFELSE）。老 bundle（rrdtool 2018
  版）同属需要补丁的一类。

## 5. 功能实测（五维账本）

| 维度 | 读数 |
|---|---|
| 上游静态注册 N_static | **0**（Makefile.am 无 TESTS/check 目标） |
| 本环境注册/执行 | 0 / 0 |
| 通过 | 0 |
| 未执行 | 0（无注册即无未执行；上游本来就没有测试面） |
| 消费者 | **1 程序 / 4 组断言**，4/4 PASS |

消费者断言（test_package/test_rdate.sh，真实执行打包产物）：① PATH 解析；② 无参 → usage + rc=1；
③ 非法选项 `-Z` → rc=1；④ `-p -o 1 127.0.0.1`（RFC868 查询闭端口）→ rc=1 + `Could not connect socket:
Connection refused`（真实走通 getaddrinfo/socket/connect 错误路径）。
**能力边界（诚实声明）**：`-s` 设置系统时需要 CAP_SYS_TIME 级特权，属设备权限面，未纳入消费者断言。

## 6. CI 取源风险预声明

源 URL = deb.debian.org（CI 镜像改写只覆盖 github.com 域，本包直接拉取）。sha256 已双向核对（实测 +
Debian 索引），E299 类 404-HTML 伪装风险由 sha256 硬闸兜底。

## 7. B 判定

- **create**：`DRAFT-rdate-1.11-musl-builtin-arc4random-vestigial-bsd-header`——「libbsd 兼容头假依赖」：
  硬检+硬链接三件套对着一个 musl 已内建的符号。已随本 PR 提交 knowledge/drafts 并跑 draft-review。
- **hit(E534 家族)**：adjtime shim 属「musl 缺 GNU/BSD 函数 → 自实现兼容层」既有工艺，不新建同名草稿。
---

**编译结束**: 2026-09-25 02:34
**最终状态**: built
