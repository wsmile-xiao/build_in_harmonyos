# ttysnoop 0.12d 适配笔记

## 编译环境

- 构建系统: makefile（上游裸 Makefile，无 configure）
- 编译日期: 2026-09-27
- 编译器: OHOS SDK clang 15.0.4（`/data/service/hnp/bin/clang` → `aarch64-unknown-linux-ohos-clang`），Conan 2.29.1，profile `ci/conan/profiles/ohos-aarch64`
- 构建机: x86_64 runner（交叉编译；运行验证见“验证结果”）
- 状态: built（本地 `conan-verify` / W3 `conan create` 通过；未上传制品仓）

## 源码与依赖

| 项 | 内容 |
|----|------|
| 上游 | Carl Declerck，0.12d（1998-04-08）；Debian copyright 记载上游 “extinct, originally from ftp.cc.gatech.edu” |
| 源码包 | `https://archive.ubuntu.com/ubuntu/pool/universe/t/ttysnoop/ttysnoop_0.12d.orig.tar.gz`（conandata 所用） |
| sha256 | `645f9c174f2d1785a2f333a585175212ba3e8911c69e62d555fc2ab92dd815d8`（8514 B）；与 Debian pool 的 `ttysnoop_0.12d.orig.tar.gz` 字节一致，并与 Debian 签名的 `ttysnoop_0.12d-6.2.dsc` 中 Checksums-Sha256 一致 |
| 源码性质 | 原始发布包：9 个文件，mtime 1994–1998、属主 carl，未含任何 Debian 改动；Debian 补丁一律未从该包引入，只作为参考并在补丁说明中署名 |
| 许可证 | GPL-2.0-or-later（Debian copyright 所载作者 1997 年邮件确认；tarball 内无许可证文件） |
| 依赖（W0） | 仅 libc。`crypt()` 由 OHOS `libc.so` 导出（`libcrypt.a` 为空档案，上游 `-lcrypt` 原样可链）；UNIX98 pty 四函数、`getutent/pututline/setutent/endutent` 均由 `libc.so` 导出；不需要 `-lutil`。无 Conan requires，无需 `conan download` 探测 |
| 历史归档（W0b） | 仓库无 ttysnoop 历史归档 |
| 语言预检（R47） | `lang-preflight` → detected=c，make，源文件 3 个（c:3），主体 100% |

源码 URL 选择（R39/PF7）：上游站点已消失，原始发布包只以发行版 orig tarball 形式存世（非 repack、
无 `+dfsg`）。任务给出的是 Debian pool 地址，但 PF7 把 `deb.debian.org` 一律判为“Debian 下游重打包源”；
Ubuntu 官方归档里的同名 orig 包逐字节相同（同 sha256、同 8514 B），且不在 PF7 的 Debian 域名单内，
故 conandata 与版本 manifest 使用 archive.ubuntu.com 地址（同仓先例：`coco-cpp/20120102`、`ifile/1.3.9`）。
Debian pool 地址与签名 `.dsc` 仅作真实性佐证。

## PR 前置硬闸（PF1–PF9）登记

- **PF9（分支/路径闸）与 R38/PF8 冲突**：本包是 CLI 工具，R38/PF8 与 CI L0k 要求在软件级放
  `archives/t/ttysnoop/commands.json`，软件级 `manifest.yaml` 为 ARCHIVE-SPEC 归档要求；PF9 以
  `len(path.split('/')) < 5` 把任何软件级文件判为“缺版本目录层”，两者对新增 CLI 包互斥，不能在配方内消除。
  处置同已合并先例（`csstidy/1.4`、`d-shlibs/0.109`、`cek/0.2.0`、`das-watchdog/0.9.0`、`hash-library/8`）：
  保留两份必需的软件级文件；不新增软件级 README.md（避免再添一处命中，同 `canfigger/0.3.2`）；
  建 PR 前实跑 preflight，确认唯一命中项为 PF9 后以 `--no-preflight` 创建，并在 PR 正文登记理由与先例。
  本包 W3 本地 CI 中 L0k（commands.json）与 L0m（目录结构）均通过。
- **L4 安全扫描提示（已声明，非阻断）**：补丁 0004 `open_unix98_master()` 中的 `strcpy(ptyname, name)`
  沿用 Debian `02_unix98_pty.diff` 原文；`name` 来自 `ptsname()`（`/dev/pts/N`，32 位编号最长 19 字节），
  目标为 32 字节的 `ptynam[]`，长度由构造保证。

## 编译步骤

配方 `build()` 直接驱动上游 Makefile，编译器与标志来自 Conan conf（R33），命令行赋值覆盖 Makefile 变量：

```bash
make -j1 CC=/data/service/hnp/bin/clang CCOPTS=-O2 LIBS=-lcrypt ttysnoops ttysnoop
```

`package()` 手工安装：`bin/ttysnoops`、`bin/ttysnoop`（0755；OHOS 设备上用 `binary-sign-tool -selfSign 1`
自签，x86 构建机无签名工具时告警跳过）、`share/man/man8/ttysnoop.8`、`res/snooptab.dist`（示例配置）。
上游 `install` 目标写 `/sbin` 与 `/usr/man/man8`，不使用。

## 遇到的问题与解决方案

| # | 问题（原文关键行） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ttysnoops.c:373:9: error: indirection requires pointer operand ('int' invalid)`（同行 `call to undeclared function 'getutline'`） | OHOS `<utmp.h>` 只声明 `setutent/getutent/pututline/endutent/utmpname`；`getutline()` 无声明且 `libc.so` 不导出（仅 `libc.a` 有）。补 prototype 后动态链接 `ld.lld: error: undefined symbol: getutline`；改 `-static` 则 musl utmp 桩返回 NULL，退出时 SIGSEGV | 补丁 0004：`cleanup_utmp()` 改用 `getutent()` 扫描（只匹配 LOGIN/USER_PROCESS，与 `getutline()` 语义一致）并判空。新知识草稿 E639 |
| 2 | 原版 `find_ptyxx()` 只找 `/dev/ptyp0…/dev/ptysf`（BSD pty），OHOS 无此设备 → `can't open pty` | 现代内核只有 UNIX98 pty（`/dev/ptmx` + `/dev/pts/N`） | 补丁 0004：移植 Debian `02_unix98_pty.diff`（Peter Samuelson）：`posix_openpt/grantpt/unlockpt/ptsname`，BSD 路径保留为回退；pty 名缩写 `pts/N` / `N` 用于 utmp 与 socket 名 |
| 3 | `/etc/snooptab`、`/var/spool/ttysnoop` 在 OHOS 上只读或不存在（`/etc` 为只读分区） | 路径编译期写死在 `config.h` | 补丁 0001/0003/0004：`conf_path()` 允许 `TTYSNOOP_SNOOPTAB` / `TTYSNOOP_SPOOLDIR` 覆盖；**特权或 set-id 运行时忽略覆盖**（telnetd/getty 以 root 拉起的登录包装器保持上游固定路径，环境变量无法把 snooptab 指向攻击者文件从而以 root 执行任意程序）；默认值保持上游 |
| 4 | clang 15 对 `wait/time/exit/write` 报隐式声明（告警；clang 16 起为错误），`time()` 在 LP64 上按 `int` 返回会截断 | 上游缺头文件 | 补丁 0001/0004：补 `<stdlib.h> <unistd.h> <sys/wait.h> <time.h>` |
| 5 | `accept(servfd, …, &len)` 的 `len` 未初始化 | 上游缺陷，socket 模式随机 `can't accept on server socket` | 补丁 0004：`socklen_t len`，每次 `accept` 前赋 `sizeof(cli_addr)`（同 Debian `03_address_length.diff`） |
| 6 | 认证子进程 `getpwnam(SNOOPUSER)==NULL` 时 `exit(1)`，而父进程把退出码 1 解释为“口令正确” → **fail-open**，任何连上 socket 的人直接获得监视与键入权限 | 上游缺陷；OHOS 上 passwd 查询失败的概率高于常规 Linux | 补丁 0004：查不到用户时 `exit(0)`（拒绝）；`SHADOW_PWD` 分支同改。对照实测见“验证结果” |
| 7 | 客户端 `sprintf(sockname, "%s/%s", SPOOLDIR, argv[1])` 写 128 字节栈缓冲，无界 | 上游缺陷；引入环境变量覆盖后输入面变大 | 补丁 0003/0004：`snprintf` 并拒绝超过 `sun_path` 的路径（`socket path too long`） |
| 8 | x86 构建机没有 `binary-sign-tool`；动态链接的 OHOS ELF 在 x86 上无法启动（缺 `/lib/ld-musl-aarch64.so.1`） | 构建机与目标机不同 | 配方：非 aarch64 构建机告警跳过签名；test_package 在非 aarch64 机器上只编译链接、明确打印未执行；本地运行验证用同源 `.o` 静态重链 + qemu（E544 口径） |
| 9 | socket 模式需要在 spool 目录 `bind()` AF_UNIX 套接字，CI 设备构建目录位于 HMDFS（`/storage/Users/currentUser/...`） | E461：HMDFS 拒绝 AF_UNIX bind（EPERM） | test_package 的 S3 先探测 bind 能力，不可用时打印 `skip - S3 … errno` 且不计入通过数；S1（tty 模式）不依赖 socket |

## Debian 补丁取舍（ttysnoop_0.12d-6.2）

| Debian 补丁 | 取舍 | 理由 |
|---|---|---|
| 02_unix98_pty | 采纳（移植进 0004） | OHOS 只有 UNIX98 pty；未照搬其 `#define _XOPEN_SOURCE 600`：musl 在只定义它时会隐藏 `<sys/select.h>` 等 BSD 声明，而不定义任何特性宏时默认全部可见 |
| 03_address_length | 采纳（0004） | socket 模式正确性 |
| 10_compiler_warnings | 部分（仅补缺失头文件） | 其余为风格性告警 |
| 01（logwtmp.c）/ 17（-lutil、SunOS 分支） | 不采纳 | OHOS libc 无 `logwtmp`，`libutil.a` 为空档案；wtmp 在 musl 上为桩（`/dev/null/wtmp`） |
| 12_tailor_makefile / 18_hardening | 不采纳 | 配方以 make 变量赋值传入编译器与标志，不改 Makefile |
| 13/14/15/16 | 不采纳 | 客户端/服务端行为调整、root 权限检查、utmp id 调整，超出本次适配所需；其中 14 的“非 root 拒绝运行”与 OHOS 非特权使用冲突 |

## 源码修改（`refresh-patch --auto` 生成，逐文件）

| 补丁 | 内容 |
|------|------|
| `patches/0001-common.c.patch` | `conf_path()`（环境变量覆盖 + 特权/set-id 忽略）；补 `<stdlib.h>` `<unistd.h>` |
| `patches/0002-common.h.patch` | 声明 `conf_path()` |
| `patches/0003-ttysnoop.c.patch` | 客户端 socket 路径：`TTYSNOOP_SPOOLDIR` + 有界 `snprintf` |
| `patches/0004-ttysnoops.c.patch` | UNIX98 pty；`getutent()` 替代 `getutline()` 并判空；snooptab/spool 走 `conf_path()`；有界 socket 路径；`accept` 地址长度；认证 fail-closed；补 `<sys/wait.h>` `<time.h>` |

补丁均不含 `__OHOS__` 平台宏（`#ifdef TIOCSCTTY` 为 ioctl 能力宏，沿用 Debian 写法）。

## 上游测试清点（R51）

- 解包后 9 个文件：`Makefile README common.c common.h config.h snooptab.dist ttysnoop.8 ttysnoop.c ttysnoops.c`；
  `find . -iname '*test*'` 为空，无 `tests/`、`t/`。
- Makefile 目标：`all ttysnoops ttysnoop ttysnoops.o ttysnoop.o common.o clean install`；
  `make -n check` → `make: *** No rule to make target 'check'.  Stop.`
- 源码无 `assert(` 与测试框架代码。
- 结论：上游 0 用例（N=0、N′=0），适配后由 `test_package` 补全。

## 测试设计（test_package/test_ttysnoop.c）

`test_package` 用 OHOS 工具链编译 `test_ttysnoop.c`，由它驱动**包内**的 `bin/ttysnoops` 与 `bin/ttysnoop`；
同一可执行文件还被 ttysnoops 当作“登录程序”（`./test_ttysnoop --child`）在其分配的 pty 上执行，
回报 `ttyname()` 与是否拥有控制终端，并逐行回显输入。

| 场景 | 断言数 | 内容 |
|------|--------|------|
| S1【鸿蒙特有】tty 监视 | 9 | ttysnoops 以会话首进程身份跑在 pty A 上（getty/telnetd 的拉起方式），`TTYSNOOP_SNOOPTAB` 指向测试 snooptab，把会话镜像到 pty B：①② 登录程序输出到达 A 与 B；③ 登录程序运行在 ttysnoops 新分配的 pty 上（`posix_openpt/ptsname`，与 A/B 不同）；④ 该 pty 是其控制终端；⑤⑥ A 端键入到达登录程序、回显镜像到 B；⑦⑧ B 端（监视端）键入注入会话、A/B 都看到回应；⑨ 登录程序结束后 ttysnoops 退出码 0（utmp 清理路径） |
| S2 客户端 | 3 | 无参数 → usage + 退出 1；服务端不存在 → `can't connect to server` + 退出 1；超长 pty 名 → `socket path too long` + 退出 1（非信号终止） |
| S3 socket 模式 | 4 | 仅当工作目录允许 AF_UNIX `bind()`：会话 socket 出现在 `TTYSNOOP_SPOOLDIR`；客户端连接并收到口令提示；错误口令被拒、服务端挂断、无 `Verified OK`；登录程序结束后 ttysnoops 退出 0。不可 bind 时打印 `skip - S3 …` |
| root 运行时 | 1 | S1/S3 不执行（覆盖对特权进程按设计失效），改为断言特权 ttysnoops 忽略 `TTYSNOOP_SNOOPTAB`（仍报 `can't open /etc/snooptab`） |

合计 16 项断言（非特权运行）。鸿蒙特有测试按 S1 计 **9**。

## 验证结果

### 1. conan-verify / W3（x86_64 runner）

`conan create`（profile ohos-aarch64）通过：4 个补丁全部应用，`make` 以 `/data/service/hnp/bin/clang`
交叉编译，链接产物 `NEEDED: libc.so`；全部强未定义符号均由 `libc.so` 导出，`libc.so` 未导出的
`__at_fini`、`__register_frame_info`、`__deregister_frame_info` 三个均为弱引用。
test_package 在本机编译链接成功，**执行阶段按设计跳过**（`WARN: test_ttysnoop built for armv8 but NOT executed
on this x86_64 build machine`）；x86 上无签名工具，包内二进制未签名（告警）。

### 2. 本地实跑：同源 `.o` 静态重链 + qemu-aarch64（非交付产物）

取 Conan 缓存中本次包构建目录的 `ttysnoops.o / ttysnoop.o / common.o`（sha256 前缀 4bb8fe8b / de08ea6f /
bc8654bd）静态重链，并静态编译 `test_package/test_ttysnoop.c`，经 binfmt 调 qemu-aarch64 运行：

```bash
setpriv --reuid=65534 --regid=65534 --clear-groups -- ./test_ttysnoop ./ttysnoops ./ttysnoop
# ok 1 … ok 16，“# ttysnoop consumer test: 16 checks, 0 failed”，EXIT CODE: 0
./test_ttysnoop ./ttysnoops ./ttysnoop          # root：skip S1/S3，4 checks, 0 failed，EXIT CODE: 0
```

⚠ 这不等于交付产物已实跑：交付的是动态链接 `libc.so` 的 ELF，x86 runner 上无法启动（E544）。
交付产物的执行由 CI 设备（aarch64，非 root，`HOME=/storage/Users/currentUser`）在 test_package 中完成：
**本地未以交付产物实跑、由 CI 执行**。CI 构建目录位于 HMDFS，预计 S1+S2 共 12 项执行、S3 打印 skip（E461）。

### 3. 回归敏感性对照（同一测试程序驱动对照变体，qemu 静态）

| 变体 | 结果 |
|------|------|
| `cleanup_utmp()` 恢复旧写法 + 手工 `getutline` prototype，动态链接 `libc.so` | `ld.lld: error: undefined symbol: getutline` |
| 同上，`-static` | `not ok 9` / `not ok 16`：`ttysnoops … killed by signal 11` |
| SNOOPUSER 设为不存在的用户 + 上游 `exit(1)` | `not ok 15`：客户端未经口令即被授权（`exit(1)` 被当作验证通过），连接不关闭，超时后被测试程序杀掉（signal 9） |
| SNOOPUSER 不存在 + 本补丁 `exit(0)` | 16/16 通过（客户端在口令提示前被拒并断开） |

## 已知限制

1. 只有 tty 监视模式（S1）在 OHOS 上可完整使用；需以非特权用户运行并通过 `TTYSNOOP_SNOOPTAB` 指定可写位置的 snooptab。
2. socket 模式需要能 `bind()` AF_UNIX 套接字的 spool 目录（HMDFS 拒绝，E461）；认证以 `SNOOPUSER`（root）的
   `/etc/passwd` 口令哈希为准，若平台 passwd 中无可用哈希，则任何口令都会被拒（fail-closed）。
3. utmp/wtmp 在 OHOS libc 上为桩，ttysnoops 的 utmp 记账不产生效果（不影响转发）。
4. root 身份运行时忽略 `TTYSNOOP_*`，行为与上游一致（读 `/etc/snooptab`）。

## 知识沉淀

- 新增草稿 `knowledge/drafts/E639-draft-788E.kv/.md`：OHOS `<utmp.h>` 只有 utmp API 子集，`getutline()/getutid()`
  无声明、`libc.so` 不导出，旧写法三层失败（编译/链接/运行）与 `getutent()` 判空修法。
  查重：`engine` 对原始报错命中 E063（-Werror 泛化条目，不相关）；`draft-review` 最相似 E245（vhangup 未导出）/
  E081（secure_getenv），得分 0.4，均为不同 API；E121 只覆盖 utmpx 族。
- 引用既有：E461（HMDFS 拒绝 AF_UNIX bind）、E544（x86 上动态 OHOS ELF 无法运行 → 静态重链验证）。
---

**编译结束**: 2026-09-27 03:46
**最终状态**: built
