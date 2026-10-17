# ell 0.71 适配笔记

## 编译环境
- 构建系统: autotools（`configure.ac` + `Makefile.am`，automake）
- 编译日期: 2026-10-06
- 编译器: clang 15.0.4（HarmonyOS SDK ohos-sdk_26.0.0.18 / aarch64-linux-ohos，musl sysroot）
- 构建主机: B 机（`frp-bar.com:19214`，sshd 6022）；worktree `~/qzy/主理-2-ell-0.71`，分支 `feat/ell-0.71`
- CONAN_HOME: `~/tmp/ch/home-ell`（三步播种，`ohpcd` 远端 + `core.sources:download_cache` 已自检）
- 状态: built（本地 W3 全绿；CI 未跑，本轮终点在 W4 审计前）

## W0 能力面复核（B 机实测 2026-10-06 00:37:50）

| 能力 | 读数 | 结论 |
|---|---|---|
| `AF_NETLINK`（NETLINK_ROUTE proto 0） | fd=5 OK | ✅ netlink 路由面可用 |
| `epoll_create1` | fd=5 OK | ✅ 事件循环核心可用 |
| `inotify_init` | fd=5 OK | ✅ |
| `AF_UNIX` / `AF_INET` | OK | ✅ |
| `/proc/net/netlink` | 66 行 | ✅ |
| `AF_NETLINK` 其他 proto（4/10/12/**16 GENERIC**） | `PermissionError [Errno 13]` | ⚠ 进程权限限制，非能力缺失 |
| `AF_VSOCK` | Permission denied | ⚠ 本包不需要 |
| DBus socket（`/run/dbus` `/var/run/dbus` `/dev/socket/dbus`） | 三处全 MISSING | ❌ 无 DBus 运行期（可选功能面） |
| `dbus-daemon` | NOT FOUND | ❌ 同上 |
| `/sys/class/net` | `[Errno 13] Permission denied` | ⚠ 进程权限，非能力缺失 |
| **`AF_ALG` socket** | `socket(PF_ALG, SOCK_SEQPACKET\|CLOEXEC)` **成功 fd=3**，但 **`bind()` 全部 `Permission denied`**（`hash/sha256`、`hash/sha1`、`hash/md5`、`skcipher/ecb(aes)`、`aead/gcm(aes)` 5/5 被拒） | ❌ **内核加密后端不可用** ⇒ `l_checksum_new()` 返回 NULL、`l_checksum_is_supported()` 恒 false |

> **AF_ALG 读数的连锁（必须知道，否则会误判"测试全过"）**：ell 的 `checksum.c` 后端是 AF_ALG
> （`init_supported()` 里 `bind` 失败即 `continue`，`supported` 保持 false）。因此
> `unit/test-checksum.log` **只打印了 `TEST: unsupported` 一行**——所有算法用例都被
> `if (l_checksum_is_supported(...))` 静默跳过，automake 仍记 **PASS**（属"假通过"）。
> `test-cipher` 之所以真跑（`arc4`/`rc2` 有 ell 内置软件实现），是因为 cipher 不走 AF_ALG。
> **据此，`test_package` 的消费者测试刻意只用 base64 / `l_strdup_printf` 这类不依赖
> AF_ALG、epoll、netlink、DBus 的纯计算 API**（已做正反双向验证：期望值改错即 rc=1）。
> 该读数与主理 A 机探针卡不冲突（卡内未测 `AF_ALG`），**以本机实测为准**。

**判断**：核心面（epoll + netlink route + inotify）实测可用，DBus 属可选功能面 ⇒ 与 `can-utils`（核心 `AF_CAN` 完全不可用）不同，可继续。
**与主理 A 机探针的差异（以本机实测为准）**：A 机卡未测 `NETLINK_GENERIC` 等其它 netlink 协议；B 机实测 **proto 4/10/12/16 全部 EACCES，仅 proto 0 (ROUTE) 可用**。

## 编译步骤

```bash
# 1. 源码（上游回读核对）
curl -L -o /dev/null -w '%{http_code} %{size_download}\n' \
  https://kernel.org/pub/linux/libs/ell/ell-0.71.tar.xz   # => 200 574408
sha256sum ell-0.71.tar.xz
# => 850f79cc993791f00232fd31cbaf3e8212edcef25ca0515f98c6d48dfb5952d7

# 2. 初始化
python3 scripts/ohc-run.py init-build ell 0.71 \
  --url=https://kernel.org/pub/linux/libs/ell/ell-0.71.tar.xz --tar=tar.xz   # rc=0

# 3. configure（D8 记录）
sh ./configure --prefix=$HOME/usr/local --enable-maintainer-mode
#   耗时约 45s（00:58:0x 起）；产出 Makefile / ell/ell.pc / config.h
#   ★ --enable-maintainer-mode 不可省：configure.ac:125 把 openssl/xxd 检测
#     包在 if USE_MAINTAINER_MODE 内，缺它 have_openssl='' ⇒ CERT_TESTS 与
#     OPENSSL_PROVIDER 双双为假 ⇒ 46 个注册 TESTS 只编出 43 个、examples 不编。

# 4. make（多轮修复后）
make -j1          # rc=0，产出 ell/libell.la、ell/libell-private.la、5 个 tools

# 5. 上游测试
make -j1 check    # TOTAL=46  PASS=39  FAIL=7  SKIP=0

# 6. Conan 配方
python3 scripts/ohc-run.py conan-init ell 0.71         # rc=0
#    conandata.yml sha256 已填真实值；license=LGPL-2.1-or-later
python3 scripts/ohc-run.py refresh-patch --auto ell 0.71  # rc=0，31 个补丁
```

## 遇到的问题与解决方案

| # | 问题（第一条真实错误） | 根因 | 解决方案 | 知识库 |
|---|---|---|---|---|
| 1 | `configure:5167: error: cannot guess build type; you must specify one` ＋ `./build-aux/config.guess: unable to guess system type` | `uname -s` 返回 `HarmonyOS`，自带 config.guess(2022-01-09) 无该分支（`grep -c HarmonyOS = 0`）⇒ 落入 C 编译 fallback，而 fallback 在 `mkdir+cat > dummy.c` 处 `Permission denied` | `perl scripts/patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub` ⇒ 输出 `aarch64-unknown-linux-ohos` | **hit E007/E160** |
| 2 | `./config.sub: Invalid configuration 'aarch64-unknown-linux-ohos': Kernel 'linux' not known to work with OS 'ohos'` | **`patch-autotools-ohos.pl` 2.3 节守卫自污染**：2.1 节刚插入的 `basic_os=linux-ohos` 使 2.3 的 `unless ($sc =~ /linux-ohos/)` 必然匹配 ⇒ 走 `[skip]` ⇒ `case $kernel-$os` 校验列表永远加不上 `linux-ohos*` | 手工在 `linux-uclibc* )` 处追加 `\| linux-ohos*`（config.sub 1786-1790 行 case 段） | E007 处方**固有缺陷**，需回反馈 |
| 3 | `./config.status[996]: can't create ./confeCuyke/subs1.awk: Permission denied` ＋ `config.status: error: could not setup config files machinery` | autoconf `config.status` 内置 `umask 077 && mktemp -d "./confXXXXXX"`（configure 15179/15184 行）；HMDFS 上 `umask 077` 建出的目录实测 `drwx--S---` 且 **`chmod 700` 不生效**、目录内建文件恒 `Permission denied`（默认 `umask 002` 的 `drwxrws--x` 正常） | 按 E533 处方把 `configure` 内 `umask 077` → `umask 002`（2 处） | **hit E129/E136/E206/E223/E011/E533**（E129 签名三条正则全中） |
| 4 | `ell/netlink.c: .../linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'` | OHOS 内核头 `linux/socket.h` 定义 `sockaddr_storage`，与 musl `sys/socket.h` 冲突；凡含 `linux/{netlink,rtnetlink,genetlink,if_arp,if_addr,if,neighbour,if_link}.h` 且已含 `sys/socket.h` 的文件均触发 | 按 E091 `define-guard`：include 前 `#define sockaddr_storage __linux_sockaddr_storage`（`#ifdef __OHOS__`），include 后 `#undef`；批量脚本覆盖 ell/unit/examples 共 17 个文件 | **hit E091**（探针 1/2 复现、带守卫 rc=0） |
| 5 | `ld.lld: error: undefined symbol: sigisemptyset`（`ell/.libs/signal.o:(l_signal_remove)`） | `sigisemptyset()` 是 glibc 2.36+/POSIX.1-2024，OHOS musl 未提供 | 按 E534 `compat-patch-in-missing-syscalls`：`#ifndef HAVE_SIGISEMPTYSET` 下用 `static inline` 直接扫 `sigset_t` 位图判空（全零即空） | **hit E534** |
| 6 | `tools/gpio.c:28:3: error: use of undeclared identifier 'program_invocation_short_name'` | 该符号是 glibc 专有，musl 无 | 按 E493 处方 `#ifndef __GLIBC__ / extern char *__progname; / #define program_invocation_short_name __progname`（实测 musl 导出 `__progname`，输出 `pn`） | **hit E493** |
| 7 | `ell/key.c:199:31: error: field designator 'private' does not refer to any field in type 'struct keyctl_dh_params'` | OHOS `linux/keyctl.h` 把该结构体改成 `union { __linux_private; priv; } + prime + base`，**无 `private` 成员**；ell 走"系统头有 `KEYCTL_PKEY_QUERY` 即用系统 struct"分支，`.private` 设计符落空 | `#if defined(__OHOS__)` 下重新声明上游同形状的私有 `struct dh_params{int32 private;int32 prime;int32 base;}`（布局一致 ⇒ syscall ABI 不变） | **★ create**（四范围 0 命中）→ Issue **#3791** |
| 8 | `unit/test-key.c:59:22: error: comparison of integers of different signs ... [-Werror,-Wsign-compare]` | `KEY1_LEN` 是 `strlen()` 结果（`size_t`），`reported_len` 是 `ssize_t`；环境注入的 `CFLAGS`（Makefile:856）带 `-Werror -Wextra` | 最小语义等价改法 `assert(reported_len == (ssize_t) KEY1_LEN);` | 新增（未入 0 命中，仅 1 处） |
| 9 | conan-verify G2: `configure: error: cannot guess build type; you must specify one` | **`conandata.yml` 的 `patches: {}` 是空的**——`refresh-patch --auto` 生成了 .patch 文件，但没把条目注册进 `conandata.yml` ⇒ `apply_conandata_patches()` 一条都不应用、`export_conandata_patches()` 也不导出 ⇒ 干净构建等于没打补丁 | 把 31 个补丁按 `patch_file/patch_description/patch_type` 逐条注册（照已过 CI 的 `archives/a/a52dec/0.7.4` 格式） | 工具流程缺口（`refresh-patch` 不写 conandata），需回反馈 |
| 10 | G2: `ell/missing.h:60:1: error: unknown warning group '-Wstringop-overflow=', ignored [-Werror,-Wunknown-warning-option]` | `-Wstringop-overflow` 是 **GCC 专属**警告组，clang 不认识 ⇒ `-Wunknown-warning-option` 在 `-Werror` 下致命；上游用 `_Pragma("GCC diagnostic ...")` 包 `rawmemchr` | `#if defined(__GNUC__) && !defined(__clang__)` 包住 `_Pragma`（**不用平台宏**，PF5 友好）；正反对照实测：改前 `rc=141`、改后 `rc=0` | 知识库 **0 命中**（`stringop-overflow`/`unknown warning` 全无）⇒ 已入 `经验文档/B草稿库/` 通用池 |
| 11 | G2: `ell/netlink.c:282:13: error: comparison of integers of different signs ... [-Werror,-Wsign-compare]`，展开点指向 `sys/socket.h:360` | **musl 的 `CMSG_NXTHDR()` 宏内部** `__CMSG_LEN(...) >= __MHDR_END(mhdr) - (unsigned char *)(cmsg)` 拿 `size_t` 比 `ptrdiff_t` ⇒ 宏展开即触发，**不是 ell 代码问题** | 全源码 `-fsyntax-only -Wall -Wextra` 扫描定位 **7 文件 8 处**（`cipher/dbus/dhcp-transport/dhcp6-transport/genl/icmp6/netlink`），逐文件加 `#pragma GCC diagnostic ignored "-Wsign-compare"` + 扫描证据注释；改后全量复扫 **0 失败** | 知识库 **0 命中**（`CMSG_NXTHDR`/`sign-compare` 全无）⇒ 已入通用池 |
| 12 | G2 同族：`ell/cert-crypto.c:225` / `ell/dbus-filter.c:298,338` `unknown warning group '-Wmaybe-uninitialized'` | 同 #10，`-Wmaybe-uninitialized` 也是 GCC 专属；**靠全量扫描一次发现 3 处，避免再增量踩 2 轮** | 同 #10，`__GNUC__ && !__clang__` 条件化 | 同 #10（同一机制族） |

## 源码修改（31 个补丁，`refresh-patch --auto` 按 31 个 track-edit 文件生成）

> 三个文件之间**必须同步**：`patches/*.patch`（31）＝ `conandata.yml` 的 `patches:`（31）＝
> `manifest.yaml` 的 `patch_classification`（31）＝ `patch_generation.patches_count`（31）。
> 本轮踩过：`refresh-patch` **只写 patches/ 和 manifest.yaml、不写 conandata.yml**，
> 导致 `apply_conandata_patches()` 一条都不应用 ⇒ 干净构建退回原状（问题 #9）。

- `0001` `build-aux/config.guess`、`0002` `build-aux/config.sub` — OHOS 三元组识别（含手工补的内核校验列表）
- `0003` `configure` — `umask 077` → `umask 002`（2 处）
- `0004`–`0019` `ell/*.c`（16 个）— sockaddr_storage 守卫 / key.c 结构体 / `missing.h` 与 `cert-crypto.c`、`dbus-filter.c` 的 GCC-only pragma / `signal.c` 的 `sigisemptyset` / 7 个文件的 `CMSG_NXTHDR` sign-compare pragma
- `0020`–`0024` `examples/*.c`（5 个）— sockaddr_storage 守卫
- `0025` `tools/gpio.c` — `__progname`
- `0026`–`0031` `unit/*.c`（6 个）— 守卫 + `test-key.c` 符号比较

> **出处口径**：`manifest.yaml` 的 `patch_classification[].guard` 是 `refresh-patch --auto` 写入的 `pending` 占位（每轮 finish 都会重写），**不是实值**，故上述分布一律以 `patches/*.patch` 的 `+` 新增行复算为准，不去 manifest 核。

**guard 分布（按 `patches/*.patch` 的 `+` 新增行逐条复算得出）**：`__OHOS__` 18 · `__GNUC__ && !__clang__` 3 · `-Wsign-compare 文件级` 4 · `HAVE_SIGISEMPTYSET` 1 · `__GLIBC__` 1 · `none` 4（三元组校验表 2 = `config.guess`+`config.sub` / umask 1 = `configure` / 显式 cast 1 = `unit/test-key.c`）　⇒ 合计 `18+3+4+1+1+4 = 31`
> **归并规则（防两个口径打架）**：`grep -l '^+.*Wsign-compare' patches/*.patch` 原始命中 **7** 个（0005/0007/0008/0009/0011/0012/0017），其中 **0011/0012/0017 同时含 `__OHOS__`** 已按优先级计入 18 项，故此处只记**独占口径 4**（0005/0007/0008/0009）；上表各档互斥、不重复计数，闭合恒为 31。

⚠ **PF5 风险预警（留给下一轮/主理）**：31 个补丁中 **18 个**含 `__OHOS__` 新增行（R8/PF5 平台宏闸）。属 E091/E534/E493 等知识库既有处方的标准写法（glib/systemd/libusb/usbutils 先例），**建 PR 时必须在 `## 补充说明` 写明例外理由**，否则 PF5 会在建 PR 前拦截。

## 依赖版本

| 依赖 | 版本 | 说明 |
|---|---|---|
| conan 依赖 | 无（`requirements()` 为空） | ell 是叶子库 |
| clang | 15.0.4 | HarmonyOS SDK ohos-sdk_26.0.0.18 |
| automake / libtool / bzip2 | 由构建管线按需安装 | `preflight` 首轮即通过（无依赖需检查） |
| openssl（可选，仅 cert 测试） | 3.6.4 | 提供 `-provider legacy -provider default` 才能生成 DES 测试密钥 |

## 验证结果

### 上游测试数（§12.72 四类口径，2026-10-06 逐项实测）

| 类别 | 实测 | 说明 |
|---|---|---|
| ① `test*/` 框架源码 | **46** | `unit/test-*.c`（= automake 注册 `TESTS` 46：`unit_tests` 33 + `dbus_tests` 10 + `cert_tests` 3） |
| ② `*/res` 语料 | **0** | 源码树无 `res` 目录 |
| ③ `**/*RUNTEST*` 脚本 | **0** | 0 命中 |
| ④ `examples/*.c` 示例 | **10** | 上游 `noinst_PROGRAMS`，不注册为 TESTS |
| **四类严格合计** | **56** | |
| 附：`unit/` 数据文件 | 4 | `dbus.conf` / `gencerts.cnf` / `plaintext.txt` / `settings.test` |
| **申报（含数据文件，宁高勿低）** | **60** | 与 `manifest.yaml`、`test_package/MANIFEST.yml`、PR 正文两表一致 |
| 断言总数 | 2355 | `grep -c 'assert(' unit/test-*.c` |

### 五维测试账本（`适配检查清单.md:150` 要求，PR 正文/notes/报告同源）

| 维 | 字段 | 值 | 口径 |
|---|---|---|---|
| N_static | `n_static` | **60** | 上游测试资产总数（§12.72 四类 56 + unit 数据文件 4） |
| N_registered | `n_registered` | **46** | automake 注册 `TESTS`（unit 33 + dbus 10 + cert 3） |
| N_executed | `n_executed` | **46** | `make check` 实际执行（`# TOTAL: 46`） |
| 未执行分类 | `n_not_executed` | **0** | registered == executed ⇒ 0；另 7 项**执行了但失败**，逐项归因见下表 |
| N_consumer | `n_consumer` | **3** | `test_package/test.c` 1 个程序 / 3 条断言（encode、round-trip decode、formatted），negative control rc=1 |

⚠ **PR 正文不得拿 46 当 `N_static`** —— 46 是 `N_registered`/`N_executed`，`N_static` 是 **60**。
⚠ 39 个 PASS 中 `test-checksum`（AF_ALG bind 全拒 ⇒ 只跑 `unsupported` 一项）与 `test-tls`（`Needed checksum missing, skipping`）属**上游自身条件跳过后的 PASS**，不等于 100% 覆盖。
字段同源位置：`manifest.yaml` `tests:` 段 · 本节 · `test_package/MANIFEST.yml`（三处均 `60 / 46 / 39`）。

### 适配后实测（可执行断言口径）

```console
$ make -j1 check
# TOTAL: 46
# PASS:  39
# FAIL:  7
# SKIP:  0
```

**39/46 通过；7 个失败逐项归因（均为环境/平台限制，非本次适配引入）：**

| 测试 | 现象 | 归因 | 知识库 |
|---|---|---|---|
| `test-dir-watch` | `WCHAN=EVENTPOLL` 死等 9m57s 后按 SKILL「超时可 Ctrl+C 跳过并记录原因」终止，`exit 143` | `/tmp` 为只读 erofs（`mkdir /tmp/x` → `Read-only file system`），测试硬编码 `DIR_1="/tmp/ell-test-dir-1"` ⇒ inotify 事件永不触发 | E002 族（prescan `PSCAN-FS-001` 已预扫命中） |
| `test-path` | `Assertion failed: fd > 0 (test_path_find: 63)` → `exit 134` | 同上：`l_strdup("/tmp/foobarXXXXXX.tmp")` 在只读 `/tmp` 上 `mkstemp` 失败 | E002 族 |
| `test-dbus` | `TEST FAILED in test_dbus: dbus` / `bus_became_ready` → `exit 255` | **双重致因**：① 无 DBus 运行期（三处 socket 全 MISSING、`dbus-daemon` NOT FOUND，W0 已实测）；② **总线地址 `unix:path=/tmp/ell-test-bus` 落在只读 `/tmp`（E002 叠加，独立致因）** —— `test-dbus.c:55` 是 `fork+execvpe("dbus-daemon")`，exec 失败时子进程 `exit(EXIT_SUCCESS)`，故日志 `dbus-daemon process … created` 仅表示 fork 成功 | E002 族 + DBus 可选功能面 |
| `test-dbus-message-fds` | `Signal 6` → `exit 134` | 同上 | 同上 |
| `test-dbus-properties` | `Signal 6` → `exit 134` | 同上 | 同上 |
| `test-pem` | `TEST: pem/invalid header/test 1` → `Signal 31 (core dumped)` `exit 159` | seccomp 拦截系统调用（SIGSYS） | **hit E051**（`exit 159` 逐字）/ E246 |
| `test-key` | `Signal 31 (core dumped)` `exit 159` | `syscall(__NR_keyctl, KEYCTL_DH_COMPUTE, ...)` 被 seccomp 拦截 ⇒ SIGSYS；**与本轮编译期 cast 改动无关**（该改动只动符号比较，运行期未触及） | **hit E051/E246** |

> `test-tls` 为 `Needed checksum missing, skipping...` 后 **PASS**（上游自身跳过，计入 PASS）。

### Conan 验证

见 `reports/`（`conan-verify-report` / `test-report` / `w3-local-ci.log`）与 `.ci-result.json`（`exit_code` + `integrity_hash` 自校验）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `patches/0001`–`0031` | 31 个 | 见「源码修改」；与 conandata `patches:` / `manifest.yaml` `patches_applied` / `patch_classification` / `patch_generation.patches_count` 五方一致 |
| `conandata.yml` | 7629 B | `sha256=850f79cc…5952d7`（与上游 `Content-Length: 574408` 同源核对）；含 31 条 `patches:` 注册 |
| `knowledge/drafts/DRAFT-ell-0.71-ohos-keyctl-dh-params-union-no-private-member.{kv,md}` | 5825 / 6043 B | 成对草稿（B 判定 create 的交付件） |

## B 判定

- **结论：`create`**（机制 = OHOS `linux/keyctl.h` 把 `struct keyctl_dh_params` 的 `private` 改为 union，`.private` 设计符编译失败）
- **四范围查重（2026-10-06）**：
  - `经验文档/适配经验汇总.md` → 0 命中
  - `knowledge/graph/index.tsv`（542 条，`graph validate` 实测 `index rows: 542`）→ **`keyctl_dh` / `keyctl` / `field designator` 全部 0 命中**
  - `经验文档/经验库/` → 0 命中
  - `经验文档/B草稿库/`（14 条通用池）→ 0 命中
- **Issue：#3791**（`https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3791`）
- 本轮其余 7 类撞击全部 **hit**：`E007/E160`（config.guess）、`E129/E136/E206/E223/E011/E533`（config.status umask）、`E091`（sockaddr_storage）、`E534`（sigisemptyset）、`E493`（`__progname`）、`E051/E246`（SIGSYS exit 159）、`E002` 族（`/tmp` 只读）
- 轻量探针（30 行级、不含 ell 代码，留 `~/tmp/uc2/ell-0.71/`）：
  - `.private = 1` → `error: field designator 'private' does not refer to any field in type 'struct keyctl_dh_params'`（逐字复现）
  - `.priv = 1` → 编译通过并输出 `priv=1`（OHOS 实际成员名）

## 注意事项

> **conan-verify G2 实际连红 3 轮**（`verify1.log` 01:58:57 / `verify2.log` 02:02:47 / `verify3.log` 02:07:36 均 `G2: FAIL` rc=1，`verify4.log` 02:17:38 才 PASS）——三轮首错各为：① `conandata.yml` 的 `patches: {}` 未注册 ⇒ `apply_conandata_patches()` 一条不应用；② `ell/missing.h` GCC-only `-Wstringop-overflow` pragma；③ musl `CMSG_NXTHDR` 宏 sign-compare。⚠ 红轮首错**未单独留存**（`reports/conan-verify-report.md` 已被后续 PASS 覆盖），故该归因是「代码机理复核 + scratch 日志轮次」而非「日志逐字可复验」。
1. **`build` 一键工具的 Step3/Step4 在本包不可用**：`--resume-from=Step4` 未加载 `.build-context`，在 `archives/e/ell-0.71/src`（不存在）里跑 make；Step3 会清空 `Makefile`/`config.log`。本轮改走 SKILL 模式 B 手动编译（`init-build` → `configure` → `make` → `make check` → `conan-init` → `refresh-patch`）。已记 `反馈/pending`。
2. **`patch-autotools-ohos.pl` 2.3 节守卫自污染**（问题 #2）会让每个新 autotools 包都踩一次，需回反馈修。
3. `test-dir-watch` 每轮都会挂死（`/tmp` 只读），跑 `make check` 时需按 SKILL 超时口径处置，勿无限等。
4. `--enable-maintainer-mode` 不可省，否则测试数从 46 掉到 43、examples 不编。
5. 本包**纯库**（`noinst_PROGRAMS` 不安装，`bin/` 无产物）⇒ **不需要 `commands.json`**（R38/PF8 口径）。
---

**编译结束**: 2026-10-06 04:08
**最终状态**: built
