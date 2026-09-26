# 编译笔记 — quagga 1.2.4 for HarmonyOS PC (OHOS, aarch64)

任务号 9924 · 代号 主理-24 · 适配路径 A（stock 最小可用构建，可选特性一律用上游开关关掉）
构建主机：B 机（HarmonyOS aarch64，clang 15 / musl，autoconf 2.72，`/data/service/hnp/bin`）

## 0. 取源（先实测再定 URL）

| 候选 URL | 真机实测 |
|---|---|
| `https://github.com/Quagga/quagga/archive/refs/tags/quagga-1.2.4.tar.gz` | `http=000`，curl 退出码 **28（超时）** — 不通 |
| `https://codeload.github.com/Quagga/quagga/tar.gz/refs/tags/quagga-1.2.4` | **`http=200`，2234157 B** — 通 |

⇒ 采用 codeload 官方端点，**不塞镜像前缀**（PF7 镜像域名黑名单 + 仓内定案）。
`sha256 = ff4b45e6d586e02e93199952978b25236dc8721f1ab959d2f401ec2bf32dcbee`
由 B 机 `sha256sum` 实测得出（证据：`~/tmp/uc2/z24-quagga/probe1.sh` 第 [2] 步）。
URL 无 `.tar.gz` 后缀 ⇒ `conandata.yml` 必须显式 `filename: quagga-1.2.4.tar.gz`，
否则 conan 误判 zip、`strip_root` 失败。解压顶层目录 = `quagga-quagga-1.2.4/`。

## 1. 症状 → 根因 → 最小复现 → 方案

### 1.1 git-tag 包没有 configure（必须先 bootstrap）

- **症状**：`tar xzf` 之后根目录只有 `configure.ac`（53365 B），`configure`、
  `config.guess`、`config.sub` **全部不存在**。
- **根因**：GitHub tag 归档是 git 树快照，autotools 生成物不入库。
- **最小复现**：`ls -l $src/configure $src/config.guess` → `No such file`。
- **最终方案**：`self.run("autoreconf -fi", cwd=source_folder, env="conanbuild")`，
  `tool_requires("automake/1.18")` + `tool_requires("libtool/2.5.4")`
  （`configure.ac:25 AM_INIT_AUTOMAKE([1.6])`、`:87 LT_INIT`、`:14 AC_CONFIG_MACRO_DIR([m4])`）。
  宿主机只有 `autoconf/autoreconf/make`（`/data/service/hnp/bin`），
  `~/usr/local/bin/automake`、`libtoolize`、`aclocal` 直接执行报
  `No such file or directory`（解释器悬空）⇒ **不能依赖宿主 automake，必须 tool_requires**。

### 1.2 E007：config.guess 不认 HarmonyOS

- **症状**：configure `cannot guess build type; you must specify one of the
  options --build/--host`。
- **根因**：`uname -s` = `HarmonyOS`；`autoreconf -i` 从 automake 数据目录复制的
  GNU config.guess 没有该分支。
- **最终方案**：在 **autoreconf 之后**（顺序关键，否则被覆盖）写入自包含
  OHOS-aware `config.guess`，输出 `aarch64-unknown-linux-ohos`。
  `config.sub` 保留 automake 1.18 版本（GNU config.sub 自 2021 年起已认
  `*-linux-ohos`）。

### 1.3 E091：sockaddr_storage 重定义（netlink 面的真正拦路点）

- **症状**（真机原文，`~/tmp/uc2/z24-quagga/survey.log` / `probe1.sh` 第 [6] 步）：
  ```
  sysroot/usr/include/linux/socket.h:23:8: error: redefinition of 'sockaddr_storage'
  sysroot/usr/include/sys/socket.h:377:8: note: previous definition is here
  ```
- **最小复现**：一个只含 `#include <sys/socket.h>` + `#include <linux/netlink.h>`
  （→ `linux/socket.h`）+ `linux/rtnetlink.h` 的 12 行 C 文件，
  `clang --target=aarch64-linux-ohos --sysroot=$SYSROOT` 直接编。
- **实测**：无 flag ⇒ **1 error generated**；加 `-D__MUSL__` ⇒ **编过**。
- **最终方案**：`tc.extra_cflags.append("-D__MUSL__")`（仅 OHOS 分支）。
- **命中面**：`zebra/rt_netlink.c`、`zebra/kernel_*`、`nhrpd/{linux,netlink_arp,netlink_gre,znl}.c`、
  `lib/zebra.h`（全树 `#include <linux/*>` 去重共 14 个头，见 survey 第 [I] 步）。

### 1.4 HMDFS：umask 077

- **根因/方案**：与 bird2 同一族 ⇒ 改写生成的 `configure` 与 `config.status`
  中 `umask 077` → `umask 022`（`_fix_hmdfs_umask()`）。

### 1.5 运行身份：OHOS 上没有 quagga:quagga 账号

- **方案**：`--enable-user=root --enable-group=root --enable-vty_group=root`
  （上游开关名 `AC_ARG_ENABLE(user/group/vty_group)`，configure.ac:320/322/324），
  并 `--disable-exampledir` 关掉示例配置安装钩子里的 chown。

### 1.6 E386 / DRAFT-6487：HMDFS getcwd 风暴打死 configure（本轮首个真实失败）

- **症状**（W3 `conan create` 第 1 次判决，G2 FAIL，日志
  `archives/q/quagga/1.2.4/reports/conan-create.log`，已抄送
  `~/tmp/uc2/z24-quagga/w3-g2-fail-conan-create.log` + `first-error.txt`）：
  `autoreconf -fi` **成功**（`configure.ac:19: installing ./config.guess` /
  `./config.sub` / `test-driver`），随后
  ```
  quagga/1.2.4@ohpcd/stable: RUN: ".../b/configure" --prefix=/ ...
  shell-init: error retrieving current directory: getcwd: cannot access parent directories: Not a tty
  job-working-directory: error retrieving current directory: getcwd: ...  (×40+)
  configure: error: working directory cannot be determined
  ERROR: ... Error in build() method, line 178  autotools.configure()
  ```
- **根因**：profile `ohos-aarch64` 的 `[buildenv]` 注入
  `CONFIG_SHELL=/data/service/hnp/bin/bash`；该 bash 对 HMDFS 目录的 `getcwd()`
  返回 ENOTSUP/EINVAL，且 conan 缓存的 `p/b/<hash>/b/build-release` 比可正常
  `pwd` 的 `p/b/<hash>/b` **深一层**。autoconf 采用 CONFIG_SHELL 后
  config.guess/config.sub/config.status 全链路 getcwd 失败。**非负载问题**。
- **根因（第二、三轮补测出来的决定性一条）**：`conanbuild.sh` 的 source 顺序是
  **先** `conanautotoolstoolchain.sh`、**后** `conanbuildenv-release-armv8.sh`，
  后者由 profile `[buildenv]` 生成、末尾 `export CONFIG_SHELL="/data/service/hnp/bin/bash"`
  ⇒ **任何从 `generate()` 导出的 CONFIG_SHELL 都会被 profile 的值盖掉**
  （实测两份脚本都躺在 `p/b/<hash>/b/conan/` 下，`grep CONFIG_SHELL` 双命中）。
  autoconf 生成的 configure 会用 `$CONFIG_SHELL` **重新 exec 自身**，于是
  从第一行起就是 hnp bash 在 HMDFS 上 getcwd 失败。
- **最终方案（第三轮，两条一起做）**：
  1. `layout()` 把构建放回源码目录（`self.folders.build = ""`、
     `self.folders.generators = "conan"`）⇒ CWD 停在 `p/b/<hash>/b`；
     单独这一条**不够**（第二轮实测：build folder 已变浅，configure 仍同样的风暴）。
  2. **在 configure 命令行上内联** `CONFIG_SHELL=/bin/sh`（命令行赋值就近优先，
     压过任何 env 脚本），参数串仍从 `Autotools._configure_args`（= 生成的
     `conanbuild.conf`）取 ⇒ 不手写 `--prefix`/`--libdir` 等，与 conan 同源。
     `SHELL` 保持 profile 值不动 —— make 的 recipe 需要能 exec ELF 的 shell。
     这正是 DRAFT-6487 记录、classads/1.0.10 上验证过 G2 转绿的形态。
- **命中面**：本包全部走 autotools ⇒ 必然命中；与包大小无关。
- **知识归属**：E386 / `knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md`
  既有大族（`grep -rln getcwd archives/*/notes.md` 命中 12+ 个已合并配方），
  **本包判 hit 不判 create**。

### 1.7 第 7 轮真实拦路点：`CCLD pimd` 链接期 duplicate symbol（clang 15 默认 -fno-common）

**症状**（第 7 轮 `conan-verify` G2 FAIL，`VERIFY_RC=2`）：全部 `.c` 编译通过，死在链接
`pimd` 这一步。`ld.lld: error: duplicate symbol` 连报 **20** 条后撞 lld 自己的
`too many errors emitted, stopping now`。成对形态固定：一侧是 `pim_main.o:(符号名)`
（裸符号名 = lld 打印该 TU 首个强定义的方式），另一侧带 section 偏移——
`pimd.o:(.bss+0xA0)`、`pim_signals.o:(.rodata+0x0)`、`pim_version.o:(.data.rel.ro+0x0)`。
卷入的符号：`master`、`qpim_debugs`、`qpim_mroute_socket_fd/_creation/_reader`、
`qpim_all_pim_routers_addr`、`qpim_static_route_list`、`qpim_channel_oil_list`、
`qpim_mroute_oif_highest_vif_index`、`PIM_ALL_SYSTEMS/_ROUTERS/_PIM_ROUTERS/_IGMP_ROUTERS`、
`PIMD_VERSION`。**同一轮 zebra/bgpd/ripd/ripngd/ospfd/ospf6d/isisd 全部 `CCLD` 成功**
⇒ 只有 pimd 病。

**根因**（源码实测，非推断）：`pimd/pimd.h:71-103` 与 `pimd/pim_version.h:28` 把守护进程
共享全局量写成**暂定定义（tentative definition）**——有类型、有存储、
**既无 `extern` 也无初始化器**：

```c
const char *const PIM_ALL_SYSTEMS;      /* pimd.h:71  */
struct thread_master *master;           /* pimd.h:76  */
const char * const PIMD_VERSION;        /* pim_version.h:28 */
```

C 语义下**每个 include 该头文件的 TU 都输出一份这个符号**。GCC ≤ 9 默认 `-fcommon`
⇒ 符号落成 COMMON、链接期合并成一份 ⇒ 2018 年上游编得过。clang 15（OHOS 工具链）默认
`-fno-common` ⇒ 每份都变成强符号 ⇒ 重复。`const` 限定的落 `.rodata`/`.data.rel.ro`、
非 `const` 的落 `.bss`，与上面成对形态逐条吻合。全仓头文件暂定定义扫描
`pimd/ 14 处、其余目录 0 处` ⇒ 与"只有 pimd 病"自洽。
`configure.ac` grep `fno-common|fcommon|warningflags` **0 命中** ⇒ 这个默认值来自
clang 本身、不是 configure 注入，因此也没有 configure 开关可以关。

**最小复现**（真机，`~/tmp/uc2/z33-quagga/probe-fcommon.log`）：一个 4 行头文件
`int qglob; struct sX *qp; const char *const GROUP;` 被两个 TU include，
`clang-15 -O3` 直链 ⇒ `A_LINK_RC=1`，三条报错与第 7 轮**逐字同构**（含裸符号名渲染、
以及 const/非 const 分别落 `.rodata`/`.bss` 的分野）；加 `-fcommon` ⇒ `B_LINK_RC=0`，
符号类由 `B`/`R` 变 `C`(COMMON)。

**最终方案**：`generate()` 里一行 `tc.extra_cflags.append("-fcommon")`，恢复这段代码当初
写作所依赖的语言默认值。**纯配方层（路径 A），零上游源码改动，`patches/` 仍为空。**
注入位置经实测有效：工具链生成的 `conan/conanautotoolstoolchain.sh` 里是
`export CFLAGS="${CFLAGS:-}${CFLAGS:+ }-O3 -D__MUSL__"`，`-fcommon` 随 `extra_cflags`
落进 `CFLAGS`；automake 的 `COMPILE = $(AM_CPPFLAGS) $(CPPFLAGS) $(AM_CFLAGS) $(CFLAGS)`
把 `CFLAGS` 排在最后，而 `AM_CFLAGS` 只有 `$(WERROR)` ⇒ 没有任何 `-fno-common` 在其后覆盖。
同仓同型处置（照抄该仓约定，未自创写法）：`archives/c/chordii/4.5.3b/conanfile.py:55`
（同样是"头文件里定义全局量"）、`archives/a/aris/2.2/conanfile.py:61`、
`archives/a/arpalert/2.0.12/conanfile.py:41`、`archives/b/barcode/0.99/conanfile.py:59`。

**被否证的分支假设**（记下以免下一个人重挖）：怀疑"`PIMD_VERSION` 两侧都是带初始化器的
真定义、`-fcommon` 救不了、必须打上游补丁"——实测 `pim_version.h:28` 是**无初始化器**的
暂定定义，唯一的带初始化器真定义在 `pim_version.c`；`-fcommon` 下 COMMON 被强定义覆盖是
合法解析 ⇒ 不需要补丁。另一个曾被我误判的细节：`pim_main.o:(符号名)` 这种"裸符号名"
一度被当成 `-fdata-sections` 的证据，最小复现证明它只是 lld 对首个强定义的打印格式。

## 2. netlink / zebra 面在 OHOS 上到底能不能编、能不能跑（实测结论）

**结论：真能编、真能跑，不需要改上游源码。**

1. 头文件在位：`$SYSROOT/usr/include/linux/{netlink,rtnetlink}.h` 实测存在
   （sysroot = `/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot`）。
2. 类型在位且尺寸正确：`RTM_GETROUTE=26`、`NLM_F_ROOT=256`、
   `sizeof(struct rtmsg)=12`、`sizeof(struct nlmsghdr)=16`、`NLMSG_ALIGNTO=4`。
3. 建 socket：`socket(PF_NETLINK, SOCK_RAW, NETLINK_ROUTE)` ⇒ `fd=3, errno=0`
   （**普通用户 currentUser，非 root**）。
4. 真发路由 dump 请求：`bind()` + `send(RTM_GETROUTE | NLM_F_REQUEST|NLM_F_ROOT|NLM_F_MATCH)`
   + `recv()` ⇒ **同一包内收到 11 条 netlink 消息**，`errno=0`
   （证据程序 `~/tmp/uc2/z24-quagga/probe/nl_dump.c`，输出
   `OK netlink dump reply bytes=0 msgs_in_first_packet=11 errno=0`
   —— `bytes` 打的是 `NLMSG_NEXT` 迭代后的残留值，消息数才是结论）。

⇒ **不构成路径 C 定性**：本包全部处置都落在配方层（cflag / autoreconf / config.guess /
umask / configure 开关），**没有一行上游 C 源码改动，patches/ 为空**。

## 3. 关掉的可选面（路径 A 收缩口径，逐条写上游开关名）

| 关掉的面 | 上游开关 | 真机原因（sysroot 实测） |
|---|---|---|
| SNMP agent | **不传** `--enable-snmp`（**绝不能**传 `--disable-snmp`） | 上游只定义 `--enable-snmp=smux\|agentx`（`configure.ac:307-308`），护栏是 `if test "${enable_snmp}" != ""`（`:1356`）⇒ 传 `--disable-snmp` 会把 `enable_snmp` 置成 `no`（非空）**进入** SNMP 分支。第 6 轮实测首错：`configure: error: --enable-snmp given but unable to find net-snmp-config`。已 grep 全仓：这种 `!= ""` 反护栏**只有这一处**，其余 `--disable-*` 都是 `= "yes"` / `!= "no"` 正常护栏 |
| PAM 登录 | `--without-libpam` | `security/pam_appl.h`、`security/pam_misc.h` **无** |
| libcap 降权 | `--disable-capabilities` | `sys/capability.h` **有**，但不链 libcap（避免运行期缺 `cap_set_proc`） |
| texinfo 文档 | `--disable-doc` | 工具链无 makeinfo/sphinx |
| OSPF API | `--disable-ospfapi` | 需 ossp-uuid + libss |
| ospfclient | `--disable-ospfclient` | 依赖 libospf（上一行） |
| FPM | `--disable-fpm` | 需 json-c |
| protobuf | `--disable-protobuf` | 需 libprotobuf |
| pcreposix | `--disable-pcreposix` | 无 libpcreposix |
| -Werror | `--disable-werror` | clang 15 对 2018 代码的诊断会变成硬错误 |
| ~~示例配置安装~~ | ~~`--disable-exampledir`~~（第 7 轮**删除**） | `exampledir` 在 `configure.ac` 中 **grep 0 命中** ⇒ 该开关不是上游开关，autoconf 只在末尾打一行 unrecognized option 警告、不产生任何效果；样例配置面由 `--disable-doc` 与关 vtysh 连带消掉 |
| 调试噪声 | `--disable-gcc_ultra_verbose`、`--disable-rusage` | 非必要 |
| **vtysh 交互 shell** | `--disable-vtysh` | vtysh 是 libreadline 的唯一消费者：`configure.ac:757-761` 在 `AC_CHECK_LIB(readline, main)` 失败时 `AC_MSG_ERROR`；四条 termcap 探测（termcap/tinfo/curses/ncurses 的 `tputs`）实测全 `no`。`archives/r/readline/` 的 8.2、8.3 配方**已在 `origin/main`**，但精确探测 `conan install --requires=readline/8.3@ohpcd/stable --build=never` → `Unable to find ... in remotes`（8.2 同）⇒ **发布缺口，不是适配缺口** |
| **nhrpd** | `--disable-nhrpd` | nhrpd 是 libcares 的唯一消费者：`configure.ac:1348` 只在 nhrpd 开启时 `PKG_CHECK_MODULES([CARES], [libcares])`，`nhrpd/Makefile.am:4,33` 用 `@CARES_CFLAGS@/@CARES_LIBS@`。第 5 轮实测首错 `configure: error: Package requirements (libcares) were not met: No package 'libcares' found`。`archives/c/c-ares/` 有 1.34.4/1.34.5/1.34.6 三个配方在 `origin/main`，精确探测 1.34.6 与 1.34.5 均 `Unable to find ... in remotes` ⇒ 与 readline 同一类发布缺口 |

保留（= 产品本体，路径 A 不砍）：`zebra bgpd ripd ripngd ospfd ospf6d isisd pimd watchquagga`
（9 个产物 = 8 个路由守护进程 + watchquagga）。**关掉的两个都不是路由协议面**：
vtysh 是把所有 daemon 缝在一起的交互式 CLI；nhrpd 是 RFC 2332 NBMA 覆盖网协议。
zebra 的 netlink/RIB 面与 BGP/OSPF/RIP/IS-IS/PIM 全部保留并实测。

坑（值得别家引用）：`configure.ac:1244-1247` 写着"nhrpd 只在 gnu-linux 上构建"，
看似会自动关掉它 —— 但 `$opsys` 由 `case "$host" in *-linux*` 判定，而本包的
host 是 `aarch64-unknown-linux-ohos`，**照样命中 `*-linux*`** ⇒ `opsys=gnu-linux`、
`enable_nhrpd` 不会被自动置 no ⇒ 必须**显式**传 `--disable-nhrpd`，否则 configure
直撞到 libcares 才失败。

`execinfo.h` 在 sysroot 中存在 ⇒ `--enable-backtrace` 面默认不关。

## 4. 上游测试台账（R51 / rule4）

`tests/Makefile.am`（真机原文）：
- `check_PROGRAMS` = testsig testsegv testbuffer testmemory heavy heavywq heavythread
  testprivs teststream testchecksum tabletest testnexthopiter testcommands
  test-timer-correctness test-timer-performance testcli + `$(TESTS_BGPD)`（5 个）
- `TESTS` = `$(TESTS_BGPD)` teststream tabletest testmemory testnexthopiter
  test-timer-correctness tabletest

配方在 `build()` 里真跑 `make -j1 check`（不 `--skip-check`）。

### 4.1 实测账本（第 8-11 轮，W3 = GREEN，2026-09-25；证据产出时 HEAD `3ff2cc5f5d`，判决数字未变）

数据源（全部在盘，判决行原文照抄，不转述）：

- W3 真跑本地 CI（**第 11 轮现行交付件**）：`reports/w3-local-ci.log`，113862 B，
  mtime 2026-09-25 01:57，md5 `b81af20be3c5bc4bafcffd46acc284c0`，**53 个判决标记**
  （本窗按作者口径 `[step]|L[0-9]+_RESULT=|Total:|VERDICT` 复算命中 53；另存件
  `~/tmp/uc2/z33-quagga/round11-w3-local-ci.log` md5 与交付件**全等**）
- W3 内层 `conan create`（第 11 轮）：`<仓根>/.ci_logs/conan_build_quagga_1.2.4.log`，107608 B，
  mtime 01:56，md5 `fc86bdff5886e9313f39e6966e16783d`
  （另存 `~/tmp/uc2/z33-quagga/round11-w3-conan-create.log`，md5 与交付件全等）
- `.ci-result.json`（第 11 轮）：`exit_code: 0`、`step: "W3_local_ci"`、
  `timestamp: 2026-09-25T01:57:40`、`integrity_hash: d825c1bda660f24f`、
  `log_sha256: 7ffe1f5943df7632c89e3542d437b260b19d6ca53c57a90506fc4e7b040f658d`
  （本窗 `sha256sum reports/w3-local-ci.log` 实测**等于**该值 ⇒ 结果文件与判决件绑定成立；
  另存 `~/tmp/uc2/z33-quagga/round11-ci-result.json` md5 `99d098ad17a39bc37ad730be7aa25caa` 与交付件全等）
- **第 11 轮是真重跑、不是复制第 10 轮**：`~/tmp/uc2/z33-quagga/finish11.meta` 记
  `start=2026-09-25 01:50:17 head=3ff2cc5f5d` 与 `w3_before=19d2dfd2… → w3_after=b81af20b…`；
  第 10 轮另存件 `round10-w3-local-ci.log`（114295 B，mtime 01:42，md5
  `19d2dfd2e991b7ddd1fd34266cf56292`）与现行交付件 md5 **不同**，而两轮判决行数字逐条相同
  （TOTAL/PASS/SKIP/XFAIL/FAIL/XPASS/ERROR = 11/11/0/0/0/0/0、各 53 个标记）⇒ 结论可复现。
  本节此前的第 10 轮三值（`19d2dfd2…` / `54b0f4af…` / 114295 B）自此**被取代**，不得再被引用。

> ⚠ **本节旧文本已被作废**：第 4 轮这里写的是"本轮可执行数 0 / 跳过数 11 / W3 = RED"，
> 那是 configure 阶段就硬失败时的实况。第 8 轮 G2 转绿后全部由下表取代，
> **旧数字不得再被任何地方引用**。

| 维度 | 数 | 依据 |
|---|---|---|
| 上游注册 `TESTS` 总数（静态） | **11**（名字去重 10） | `tests/Makefile.am`：`TESTS = $(TESTS_BGPD) teststream tabletest testmemory testnexthopiter test-timer-correctness tabletest` ⇒ BGPD 组 5 + 6 条，`tabletest` 被上游重复列了两次 |
| 本轮可执行数 | **11** | 判决 `# TOTAL: 11` |
| 实测通过数 | **11** | 判决 `# PASS:  11`。日志内 `^PASS:` 行实测 **10 条**（第 10、11 轮两份件都是 10），构建树 `tests/*.trs` 同为 **10** 个且全部 `:test-result: PASS`，`tests/*.log` **11** 个 ⇒ 差的 1 来自上游 `tests/Makefile.am:23-24` 把 `tabletest` **重列两次**（`TESTS` 共 11 个 token，`# TOTAL: 11` 与此同源，即上表"名字去重 10"那一行）；判决数字不改 |
| 跳过数 | **0** | 判决 `# SKIP:  0` |
| 失败数 | **0** | 判决 `# FAIL:  0` / `# ERROR: 0` / `# XFAIL: 0` / `# XPASS: 0` |
| 上游 `check_PROGRAMS` 构建数 | **21**（静态 16 + BGPD 组 5） | **真 create 日志** `<仓根>/.ci_logs/conan_build_quagga_1.2.4.log`（= 另存 `round11-w3-conan-create.log`）第 937-1389 行 `Making all in tests` 段 `CCLD` 去重实测 **21 个唯一名**，与静态声明完全一致。⚠ 复核者**别**打开归档里的 `reports/conan-create.log` 数 CCLD：那份 17917 B 的件实为 **test_package 单跑日志**（`Launching test_package` → 9 条 `--version` → ✅ test.sh finished），含 **0 条 CCLD** |

`make check` 判决区块原文（现行第 11 轮件 `<仓根>/.ci_logs/conan_build_quagga_1.2.4.log` = 另存 `round11-w3-conan-create.log` 的第 1393-1412 行；第 10 轮件 `round10-w3-conan-create.log` 的同一段落在第 1396-1415 行）：

```
PASS: aspathtest
PASS: testbgpcap
PASS: ecommtest
PASS: testbgpmpattr
PASS: testbgpmpath
PASS: teststream
PASS: tabletest
PASS: testmemory
PASS: testnexthopiter
PASS: test-timer-correctness
Testsuite summary for Quagga 1.2.4
# TOTAL: 11
# PASS:  11
# SKIP:  0
# XFAIL: 0
# FAIL:  0
# XPASS: 0
# ERROR: 0
```

本地 CI 判决行原文：

```
[ok] L1a: test_package was executed by conan create
[ok] L1b: Test execution evidence found in log
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[ok] L1e: Negative test confirmed — test genuinely depends on quagga
[ok] L5: bin/ has content
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: ... bgpd/isisd/ospf6d/ospfd/pimd/ripd/ripngd/watchquagga/zebra --version OK
L4_RESULT=pass: patches clean
[step] All packages built and tested successfully ✅
```

**"跳过 0"的技术原因（不是"没环境"）**：上一棒担心关掉 vtysh 会打断
`tests/BUILT_SOURCES = test-commands-defun.c` ← `$(MAKE) -C ../vtysh vtysh_cmd.c`
这条依赖链。实测该链**在 `--disable-vtysh` 下依然成立**——`vtysh/Makefile` 与
`vtysh/extract.pl` 是 `configure.ac:1652-1667` 的无条件 `AC_CONFIG_FILES`，且
`vtysh_cmd.c` 的生成规则不在 `if VTYSH` 之内 ⇒ `testcommands` 正常 `CCLD`。
**既没有预设任何 skip，实际也没有产生任何 skip。**

**三条不得越界的口径**：

1. `testsig` `testsegv` `testbuffer` `heavy` `heavywq` `heavythread` `testprivs`
   `testchecksum` `testcommands` `testcli` `test-timer-performance` 这 11 个
   `check_PROGRAMS` **被构建、但上游本来就没把它们注册进 `TESTS`**（上游事实，不是本包
   取舍）⇒ 一律不得计入"实测通过"。
2. `L2` 里 `bgp_btoa --version/--help failed` 与 `test_igmpv3_join --version/--help failed`
   两条被框架标为 **`(non-blocking)`**：它们是上游 `bin_PROGRAMS` 顺带装进 `bin/` 的附属程序
   （`bgpd/bgp_btoa` 转换工具、`pimd/test_igmpv3_join` 组播加入请求构造器），
   天生不解析 `--version/--help`。⇒ **包内实装可执行文件共 11 个 = 本包声明的 9 个命令
   + 这 2 个上游附属程序**；`commands.json` 只声明 9 个（`L0k` PASS）。本包**不**把这两个
   补成"能跑的命令"，也**不**宣称它们可用。
3. `conan-verify` 报告的 `L2/L4/L5` 三行虽记 `✅ PASS`，正文却是「跳过（无 cache 路径）」，
   `G4` 还附「无法找到程序包 ID」⇒ 那三项在 conan-verify 这一层**并未真跑**。
   功能矩阵 / checksec / 基线对比一律**以 finish 的 W3 为准**，不得拿 conan-verify
   那三行当证据。


## 4.3 当前状态与下一个唯一动作（第 5-6 轮，主代理裁决已执行）

> ⚠ 取证更正：第 4 轮那份 `reports/w3-local-ci.log` 与 `reports/conan-create.log`
> **md5 完全相同**（`d325b944f4ab439dab09d2046e5f7186`，20595 B），里面
> `[step]` / `L0_RESULT=` / `Total:` 标记数为 **0** ⇒ 它只是 create 日志的副本，
> **W3 当时并没有真跑**。同名文件的 `verify.status` 也写着 `0`，而同一时刻
> `verify.out` 末行是 `VERIFY_RC=2` —— 驱动脚本把管道尾命令的 rc 当成了
> `conan-verify` 的 rc。两条都已作废，本轮起 `reports/w3-local-ci.log` 一律由框架
> 的 `run_local_ci()`（`ci/conan/setup.sh` + `ci/conan/build_and_test.sh`）自己写。
> `ohc-run.py conan-verify` 也不是 W3，它是 `finish` 的 **Step 4/10** 质量验证
> （G0-G4/L2/L4/L5）；W3 是 **Step 5/10**。

- 岔路已裁决并落地：**`--disable-vtysh`**（主代理 2026-09-24 裁决，理由照 §3 那一行）。
  第 5 轮按该裁决改完立刻撞到一个**同构**的新拦路点 —— `configure.ac:1348` 的
  libcares（nhrpd 唯一消费者），c-ares 三个版本同样是"配方在 main、制品未发布"
  ⇒ 按**同一条裁决原则**（发布缺口 ⇒ 用上游自带 `--disable-*` 收缩，不 block 干等）
  加了 `--disable-nhrpd`。**这是本窗自决的一次范围收缩，主代理若要保 nhrpd，
  需要的是把 c-ares 发布出去，而不是回滚本包。**
- 连带代价（如实，逐条）：
  1. vtysh 关掉的是**交互式 CLI 拼接层**，路由协议 daemon 与 zebra 的 netlink 面**都没关**；
     `configure.ac:741-742` 的 `case "${enable_vtysh}" in "no") VTYSH="";;` 干净跳过
     整段 readline/termcap 探测（第 6 轮实测：configure 一路跑到 `config.lt` 之后，
     readline 报错归零、getcwd 报错归零）。
  2. **`tests/Makefile.am` 的 `test-commands-defun.c`（`BUILT_SOURCES`）依赖
     `$(MAKE) -C ../vtysh vtysh_cmd.c`** ⇒ 关 vtysh 后该测试项是否还能构建，
     取决于 `vtysh/Makefile` 在不在。盘上事实：`configure.ac:1652-1667` 把
     `vtysh/Makefile` 与 `vtysh/extract.pl` 列为**无条件** `AC_CONFIG_FILES`，
     且 `vtysh/Makefile.am` 里 `vtysh_cmd.c` 规则**不在任何 `if VTYSH` 之内**
     ⇒ 规则仍可执行；本轮**不预设结论**，以 §4.1 的 `make check` 实测判决为准，
     若确实断掉就按 skipped 记并把这一条技术原因写进五维账本。
  3. 交付命令集从 11 个收缩到 **9 个**（8 个 daemon + watchquagga）。
     `commands.json` / 两级 `manifest.yaml` / `README.md` / `test_package` 已同步；
     并且 `test_package` 反向**断言 vtysh 与 nhrpd 不在包内**，
     把"收缩"从声明变成可被 CI 抓到的契约。
- ⚠（第 10 轮已完成，见 §4.3.1）下一个唯一动作：`conan-verify` 过 G2 拿齐 G0-G4/L2/L4/L5 ⇒
  再跑 `run_local_ci()` 出**真** W3（判决行 `[step]` / `L0/L1/L1d/L1e/JC/KC/G0/G1/G2/L4/L5`
  + `Total/Success/Failed`）。**已知 `.ci-result.json` 只由 `finish` 的
  `_write_ci_result()` 生成（带 integrity_hash，禁止手写）**，本窗按授权不跑 finish
  ⇒ 该文件留给主代理跑 finish 时产出。
- 已经拿下的（不要再重复排查）：取源、`autoreconf -fi` bootstrap、E007 config.guess、
  **E386/HMDFS getcwd（已证真修好：本轮 configure 一路跑到 `config.lt` 与
  TeX/MD 的 PDF 警告，没有任何 getcwd 行）**、路径 A 的可选面收缩清单。
- 未拿下的：readline（vtysh 的硬依赖）+ 它连带需要的 termcap 族
  （`AC_CHECK_LIB(termcap/tinfo/curses/ncurses, tputs)` 四条实测全 `no`）。
- ⚠（第 10 轮已定案，见 §4.3.1）**两条岔路（都要主代理定，子代理不自决）**：
  1. **补依赖**：`self.requires("readline/<ver>")` + `AutotoolsDeps` 注 `-lreadline`
     与 `-ltinfo`，再 `--enable-vtysh`。注意 `conan download readline/8.1
     -r=ohpcd --only-recipe` 这次**不是** "not found"，而是
     `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`
     ——制品仓侧的加速策略报错，需先复核（W0 判定未清）。
  2. **收缩**：`--disable-vtysh`（`configure.ac:742 "no") VTYSH="";;`，干净跳过
     readline 探测）。**但有连带代价**：`tests/Makefile.am` 的
     `test-commands-defun.c` 规则要 `$(MAKE) -C ../vtysh vtysh_cmd.c`
     ⇒ vtysh 不进 SUBDIRS 后 `make check` 的 `BUILT_SOURCES` 可能断，
     届时要连带排除 `testcommands`/`testcli`，rule4 账本要按实情改。
- ⚠（第 10 轮更正）**本条原文已失效**：`commands.json` 早已按 **9 命令**定案
  （不再是"含 vtysh 的完整套件"），W3 也已转绿 ⇒ 详见下方 §4.3.1 状态刷新表第 3 行。
  本窗到达的状态是"本地门禁齐 + 证据齐"，**建 PR 与提审仍归主代理**。

### 4.3.1 状态刷新（第 8-10 轮，2026-09-25）—— 上方第 5-6 轮快照的失效项

上方 §4.3 是第 5-6 轮的现场快照，**原文保留作推理痕迹**，但下面三条已被盘上事实否证，
就地更正（旧文字不删，免得下一个人照抄旧结论）：

| 第 5-6 轮原文 | 现在的盘上事实 | 证据 |
|---|---|---|
| "下一个唯一动作：`conan-verify` 过 G2 …… 再跑 `run_local_ci()` 出**真** W3" | **两条都已完成**：第 8 轮 G0/G1/G2/G3/G4 全 PASS；第 10 轮 `finish` 由框架 `run_local_ci()` 写出真 W3 —— 53 个判决标记、mtime 01:40 晚于本轮起算点、与 create 日志 md5 不同 | `~/tmp/uc2/z33-quagga/round8-conan-verify-report.md`、`round10-w3-local-ci.log`、`round10-w3-conan-create.log` |
| "**两条岔路（都要主代理定，子代理不自决）**：1 补 readline、2 `--disable-vtysh`" | **岔路 2 已采纳并落地**（vtysh + nhrpd 都关）。连带代价里担心的 `test-commands-defun.c` 断链**实测没有发生** ⇒ 不需要排除 `testcommands`/`testcli`，五维账本 `skip = 0` | §5 第 5-6 行、§4.1"跳过 0 的技术原因" |
| "`commands.json` 现按'含 vtysh 的完整套件'声明，待定案后校正" + "在 W3 转绿前**不要**让 PR 走到提审" | **两条都已过期**：`commands.json` 已是 **9 命令**，与 `test_package/conanfile.py::_BINARIES`、`test.sh` 的 `COMMANDS`、两级 `manifest.yaml`、`README.md` 四处一致（`L0k` PASS）；W3 已转绿。提审时机由主代理定，**本窗不提审、不建 PR** | `archives/q/quagga/commands.json`、W3 `L0_RESULT=pass` |

仍然没拿下、但**不属于本包范围**的：readline / c-ares 的**制品发布缺口**（配方已在
`origin/main`，`--build=never` 精确探测 `Unable to find ... in remotes`）。
本包的处置是"用上游自带开关收缩"，不是"等发布"（理由见 §4.4 倒数第二行）。

## 4.4 B 判定候选（本包撞到的、别家也会撞的机制）

| 机制 | 判定 | 证据 |
|---|---|---|
| profile `[buildenv]` 的 `CONFIG_SHELL` 覆盖工具链 env ⇒ autotools configure 必须命令行内联 | **hit**（E386 / DRAFT-6487 既有大族；`grep -rln getcwd archives/*/notes.md` ≥12 个已合并配方） | `p/b/<hash>/b/conan/conanbuild.sh` 两行 source 顺序 + 两份 env 脚本双命中 `CONFIG_SHELL` |
| GitHub tag 归档无 `configure`/`config.guess`，必须 `autoreconf -fi` + `tool_requires(automake,libtool)` | **hit**（abiword-plugin-* 等既有用法，`tool_requires("automake/1.18")` 234 处） | `archives/a/abiword-plugin-clarisworks/3.0.8/conanfile.py:105-114,149` |
| E091 `-D__MUSL__` 解 netlink 头冲突 | **hit**（bird2 2.17.4 / babeld 1.13.1 两例已合并） | `archives/b/bird2/2.17.4/notes.md`、本包 `survey.log` 第 [6] 步 |
| "路由守护进程在 OHOS 上 netlink 真能建 socket 并收到 RTM_GETROUTE dump"（供后续 frr/bird 类包引用） | 倾向 **hit**（bird2 notes 已声明守护进程需 root/netns，但**没有**给出 dump 成功的实测数）——升不升 B 由主代理按宽口径 grep 复核 | 本包 `probe/nl_dump.c` 输出 `msgs_in_first_packet=11 errno=0` |
| `conan download --only-recipe` 报 `system acceleration policy not enabled` 时**不能**判"依赖未发布" | 未见先例，值得入库（W0 判定的假阴性面）——请主代理复核宽口径 | 本轮 readline 探测原文 |
| **"配方已在 `origin/main`、但制品未发布"这类上游依赖缺口，正解是用上游自带的 `--disable-*` 收缩，而不是 `$P block` 等发布** | 本包连撞两例（readline→vtysh、c-ares→nhrpd），两次都是"配方在 main + 精确 `conan install --build=never` 报 `Unable to find ... in remotes`"；block 路线在这种形态下**永远不会解锁**（sweep 只认"上游合入"，而上游本来就在 main） | `verify2.out` 第 5 轮 readline 探测 + 本轮 c-ares 两条 `not resolved` 原文 |
| OHOS 的 host 三元组 `*-linux-ohos` 仍命中 autotools 的 `*-linux*` 分支 ⇒ "只在 Linux 上构建"式护栏不生效 | 未见先例（本包实测），后续 frr/keepalived 一类带 `opsys` 判断的包会再撞 | `configure.ac:1244-1247` + 本轮 `enable_nhrpd` 未被自动关闭 |
| 2018 年代 C 包把共享全局量写成**头文件里的暂定定义** ⇒ clang ≥ 11 / GCC ≥ 10 默认 `-fno-common` 必炸 `ld.lld: duplicate symbol`；正解是配方层 `tc.extra_cflags.append("-fcommon")`，不动上游 | **hit**（同一处置在已合并归档里早已成族：`archives/c/chordii/4.5.3b/conanfile.py:55`、`archives/a/aris/2.2:61`、`archives/a/arpalert/2.0.12:41`、`archives/b/barcode/0.99:59`；`grep -rl fcommon archives/ \| wc -l` 先例计数 **135**（口径：W4 独立审计在本包 HEAD **工作树**的复算值）；本窗按四种口径复核、均可复算：git 跟踪面 **133**（= 130 + 本包 conanfile.py/manifest.yaml/notes.md）、当前工作树 **136**（再多的 3 件是本包不入 PR 的产物：`reports/w3-local-ci.log`、`reports/audit-result.json`（W4 判决件，被 .gitignore 覆盖）、`__pycache__/*.pyc`；W4 那次计到 135 只因它的判决件当时尚未落盘）、`origin/main` 已合并归档面 **130** ⇒ 原申报 130 用的是"上游先例面"口径、并非虚报，只是未标口径；数量级远超"新机制"门槛 ⇒ 属既有机制，**不建【知识库扩展】Issue**） | 第 7 轮 20 条成对报错 + 真机最小复现 `~/tmp/uc2/z33-quagga/probe-fcommon.log`（默认 `A_LINK_RC=1` / 加 `-fcommon` `B_LINK_RC=0`，符号 `B`/`R`→`C`）+ 全仓头文件扫描 `pimd/ 14 处、其余 0 处` |


## 5. 已试过的失败方案（W3 六轮判决，日志留档）

| 轮 | 处置 | 判决 | 第一条真实错误 / 关键证据 | 日志 |
|---|---|---|---|---|
| 1 | 首稿：`basic_layout` 默认 out-of-source + profile 的 CONFIG_SHELL | G2 FAIL | `configure: error: working directory cannot be determined`（前置 `shell-init: ... getcwd` ×40+），cwd=`.../b/build-release` | `~/tmp/uc2/z24-quagga/w3-g2-fail-conan-create.log` |
| 2 | 加 `tc.generate(env=Environment().define("CONFIG_SHELL","/bin/sh"))` | G2 FAIL（**同类**） | 同一条错误——但**本轮实际跑的是旧配方**：自制 `recipe-backup` 守卫把修复盖回去了（`Error in build() method, line 178` 行号未随新增行变化暴露了这点） | `w3-run2-conan-create.log` |
| 3 | 以 HEAD 为准重放同一 env 方案（守卫已修） | G2 FAIL（**同类**，但配方确认是新的：`line 199`） | build folder 已变浅为 `.../b` ⇒ **in-source 单独不够**；`grep CONFIG_SHELL p/b/<hash>/b/conan/*` 双命中，证明 profile buildenv 后置覆盖 | `w3-run3-conan-create.log` |
| 4 | configure 命令行**内联** `CONFIG_SHELL=/bin/sh`（args 取自 `Autotools._configure_args`） | G2 FAIL于**新**位置 | **getcwd 风暴归零**：`RUN: CONFIG_SHELL=/bin/sh ".../b/configure" ...` 之后正常产出 `config.lt`，首错变成 `configure: error: vtysh needs libreadline...`（`configure.ac:757-761`） | `~/tmp/uc2/z24-quagga/w3-run4*`（`reports/w3-local-ci.log` 一名当时是副本，见下注） |
| 5 | 执行主代理裁决：加 `--disable-vtysh`（同步 9 命令面 + test_package 反向断言） | G2 FAIL于**新**位置 | **readline 报错消失、getcwd 仍 0 条**；新首错 `configure: error: Package requirements (libcares) were not met:` + `No package 'libcares' found`（`configure.ac:1348`，仅 `enable_nhrpd != no` 时执行） | `~/tmp/uc2/z24-quagga/round5-g2-fail-libcares.log`（md5 `9a13bd7b5631cd9a76180020b137e735`，469 行，build folder `quagg3151326b2916f`） |
| 6 | 同口径再加 `--disable-nhrpd` | 见 §4.1 实测判决 | — | `~/tmp/uc2/z24-quagga/verify2.out` + `reports/conan-create.log`（本轮覆盖写入） |
| 7 | 承第 6 轮（SNMP 改"不传即关"）后首次推进到链接阶段 | **G2 FAIL 于新位置** | 编译 0 错，`CCLD pimd` 报 `ld.lld: error: duplicate symbol` 共 20 条后 `too many errors emitted, stopping now`：`PIMD_VERSION`/`master`/`PIM_ALL_*`/`qpim_*` 对侧 `.bss`/`.rodata`/`.data.rel.ro` | ⚠ 原始日志已被后续覆盖，见取证声明 `~/tmp/uc2/z33-quagga/round7-transcript.md`（**转录件、非原始字节**）；同型错误由 `~/tmp/uc2/z33-quagga/probe-fcommon.log` 在真机可复现 |
| 8 | `generate()` 加一行 `tc.extra_cflags.append("-fcommon")`（路径 A，不动上游，`patches/` 仍空） | **G2 PASS ⇒ `Verdict: PASS`** | G0/G1/G2/G3/G4 全绿；上游 `make check` 真跑 `# TOTAL: 11 / # PASS: 11 / # SKIP: 0 / # FAIL: 0 / # ERROR: 0`；test_package 9 个产物逐个执行 + `✅ quagga test.sh finished`；`VERIFY_RC=0` | `~/tmp/uc2/z33-quagga/round8-conan-verify-report.md`、`verify8.out`、`verify8.status=0`（三者一致） |
| 9 | 按门禁序列补跑第 4 道闸 `ohc-run.py build quagga 1.2.4` | **`BUILD_RC=2`，Step1 失败（框架码路错配，非本包缺陷）** | `EXIT_REASON: init_build_failed` / `❌ 无法定位源码目录: orig=None, work=None`——驱动的 URL 自探给出 savannah/waterlan 候选（该 `.gz` 重定向后 404，见本节末"其它过程性发现"），拿不到本包已定案的 codeload 源。**配方目录 26 个文件 md5 快照 before/after 比对：仅框架自有 `.handoff.json` 变化 ⇒ 零覆盖** | `~/tmp/uc2/z33-quagga/round9-build-gate-init-build-failed.log`、`build9.md5.diff` |
| 10 | `ohc-run.py finish quagga 1.2.4 built`（真 W3 由框架 `run_local_ci()` 自己写） | **W3 全绿**；`FINISH_RC=2` 只来自 step5b / step8 两个非门禁项 | W3 判决 `L0/L1/L2/L4/L5_RESULT=pass` + `[step] All packages built and tested successfully ✅` + `Total: 1`；`.ci-result.json` `exit_code: 0` 带 `integrity_hash`。step5b = `clean-verify` 需要 `init-build` 留下的 `.orig/.work` 目录（与第 9 轮同一码路错配）；step8 = `packaging/`、`reports/test-report.md`、`.staging-verified` 三项 submit 建议项 ⇒ 见下方处置说明 | `~/tmp/uc2/z33-quagga/round10-w3-local-ci.log`（md5 `19d2dfd2…`，53 个判决标记）、`round10-w3-conan-create.log`（md5 `54b0f4af…`）、`round10-ci-result.json`、`finish10.out` |
| 11 | 同一条 `ohc-run.py finish quagga 1.2.4 built` **重跑复现**（起算 01:50:17，当时 HEAD `3ff2cc5f5d`） | **W3 再次全绿，判决数字与第 10 轮逐条相同**；`finish11.status` 仍为 2 ⇒ 依旧只来自 step5b / step8 两个非门禁项 | 现行交付件 `reports/w3-local-ci.log`：113862 B、mtime 01:57、md5 `b81af20b…`、53 个判决标记；`.ci-result.json`：`integrity_hash d825c1bda660f24f`、`log_sha256 7ffe1f59…`（实测 == sha256(该日志)）；真 create 日志 `.ci_logs/conan_build_quagga_1.2.4.log`：107608 B、md5 `fc86bdff…` | `~/tmp/uc2/z33-quagga/round11-w3-local-ci.log`、`round11-w3-conan-create.log`、`round11-ci-result.json`（三者 md5 与交付件全等）、before/after 对照 `finish11.meta`：`w3_before=19d2dfd2… → w3_after=b81af20b…` ⇒ **真重跑而非复制** |

> **第 9/10/11 轮的两个非绿项怎么处理（不隐瞒、也不越界去“修框架”）**
>
> - `build` 的 Step1 与 `finish` 的 step5b 是**同一个根**：**框架码路错配**，不是网络断供，
>   更不是本包缺陷。`scripts/ohc/init_build.py:432-438` 的 `--no-download` 分支要求
>   `init-build` 探索期留下的 `<包>-<版本>.orig` / `<包>-<版本>.work` **探索目录**，
>   而交付归档布局是 `archives/q/quagga/1.2.4` ⇒ 该分支起手即报 `源码目录不存在` 并 return 2。
>   驱动给出的 8 个"可用 URL"（savannah / quagga.org / waterlan 各 `.gz` 与 `.xz`）里
>   **没有本包 `conandata.yml` 定案的 codeload 源**，再探一次也接不上。
>   （2026-09-25 本窗真机复测，见 `~/tmp/uc2/z33-quagga/round12-url-probe.txt`：
>   `download.savannah.nongnu.org/releases/quagga/quagga-1.2.4.tar.gz` 重定向后 **HTTP 404**
>   （返回 236 B 错误页）；W4 审计窗同一 URL 探测为 `rc=28 / http=000` 超时 ⇒ 两种形态都取不到源码。
>   `waterlan.home.xs4all.nl/quagga/quagga-1.2.4.tar.gz` 带 Range 实测 **HTTP 206 可达**
>   ⇒ 上一版那句"探到的 savannah/waterlan URL 真机 404"**不准确**（404 只对 savannah 成立），已更正。）
>   要"修绿"只能伪造 `.orig/.work` 目录或用 `--force` 重跑 `init-build`——**前者是造假日志
>   （R34/R9 命中），后者会让框架覆盖已提交的手写配方**（本仓已因此踩过第 2 轮的反噬，见上表第 2 行），
>   两者都不做。`conan create` 这一道真门禁已由 G2 与 W3 各跑一遍并全绿，**定性结论不变**：
>   工具链码路错配，不属欺骗类。
> - step8 的三项建议物里 **`packaging/` 故意不建**：同类 4 个已合并配方
>   （`aris/2.2`、`chordii/4.5.3b`、`arpalert/2.0.12`、`barcode/0.99`）目录内均无
>   `packaging/`、`reports/test-report.md`、`.staging-verified`，且往归档目录放打包产物会
>   直接撞本轮已 `PASS` 的 `JC3: 源码 tarball / 打包产物检测`。`reports/` 与
>   `.ci-result.json` 本身在 `.gitignore`（第 96 / 238 行）⇒ 属本地证据，不进 PR。
>   这三项留给主代理决定，不在本包内自行造文件充数。

> 第 4 轮那一行的"日志"列写的是 `reports/w3-local-ci.log`，**该文件当时是
> `conan-create.log` 的同 md5 副本、并非真 W3**（取证更正见 §4.3 顶部）；
> 其真实内容仍另存于 `~/tmp/uc2/z24-quagga/w3-run3-conan-create.log` 的同族日志。

> R43 自查：第 2 轮与第 1 轮**同类**，若不查 source 顺序直接第 3 次盲调就会踩到
> "同错误类别 5 次"停火线 ⇒ 因此第 2 轮失败后先读 `conanbuild.sh`/两份 env 脚本
> 与 `Autotools.configure` 源码定位机制，再动第 3 次。

### 其它过程性发现（不是失败，但会误导）

- `ohc-run.py build quagga 1.2.4` 在 **Step1 init-build** 就 HANDOFF
  （`BUILD_RC=2`，`EXIT_REASON: init_build_failed`）：它的 URL 搜索给出
  `download.savannah.nongnu.org/releases/quagga/quagga-1.2.4.tar.gz` 等候选，
  真机实测该 `.gz` 重定向后 **HTTP 404**（返回 236 B 的 ASCII 错误页，
  `sha256 9448f8a1…` 是那个错误页的哈希，**不是源码**），`.xz` 只有 302。
  ⇒ 驱动的一键路径接不上本包定案的源，改用 `conan-verify`（同一 W3 `conan create` 门禁）推进。
  2026-09-25 本窗复测补正（`~/tmp/uc2/z33-quagga/round12-url-probe.txt`）：**404 只对 savannah 成立**，
  `waterlan.home.xs4all.nl/quagga/quagga-1.2.4.tar.gz` 带 Range 实测 **HTTP 206 可达**
  （W4 审计窗那次 savannah 探测为 `rc=28 / http=000` 超时）⇒ "旧 URL 全部 404"的说法作废，
  真正的卡点是 `init_build.py:432-438` 要求 `.orig/.work` 探索目录（见上方"两个非绿项"处置说明）。
- 本仓库 `recipe-backup` 自制的"驱动可能改写配方"守卫**反噬过一次**：它拿首稿
  备份把已提交的修复盖回工作区，导致第 2 轮实际跑的是旧配方（`line 178` 行号
  未随新增行变化暴露了这点）。已改为"以 HEAD 为准 + 刷新备份"。

## 6. 适用边界

- 仅 `os in ("Linux","OHOS")`（R32），arch armv8。
- 结论 2 的 netlink 可用性建立在 **OHOS SDK 26.0.0.18 sysroot + musl guard** 上；
  换 SDK 版本需重跑 `probe/nl_dump.c`。
- 守护进程**运行时**要读写内核路由表/绑定 vty 端口，非 root 下会部分失败；
  本包交付口径是「编译通过 + 上游测试真跑 + 二进制可加载并自报版本」，
  不宣称"能当路由器用"。
- `-fcommon` 的适用边界：只有当重复符号来自**暂定定义**（有类型无 `extern` 无初始化器，
  常见于 2018 年前后把全局量直接写在头文件里的 C 代码）时才有效。若某个包的同名符号
  **两侧都带初始化器**（即都是真定义），`-fcommon` 救不了，必须走 `archives/…/patches/`
  把其中一处改 `extern` 或收进单个 TU，并在 notes 写清症状/根因/最小复现/适用边界。
  本包实测不属此类（`PIMD_VERSION` 唯一的带初始化器定义在 `pim_version.c`）⇒ `patches/` 为空。
- 判定顺序建议（给下一个撞同一堵墙的人）：先 `grep` 符号在头文件里有没有 `extern`、
  再看对侧 section 是 `.bss`/`.rodata`/`.data.rel.ro`（暂定定义）还是 `.data`（真定义）；
  前者一行 `-fcommon` 收工，后者必须补丁。别一上来就改上游。
- 本包只声明并验收 **9** 个命令。`bin/` 内另有上游自带的 `bgp_btoa`、`test_igmpv3_join`
  两个附属程序（L2 标 non-blocking），不进 `commands.json`、不承诺可执行语义。
---

**编译结束**: 2026-09-25 01:50
**最终状态**: built

## 路径与知识库声明（3+2 最小声明，与 PR 正文同源）

- 适配路径：路径 A（基础适配；patches/ 为空，零上游源码改动，可选特性一律用上游自带开关关闭）
- 使用知识库：openharmony-compile-agent skill 与 knowledge/graph 知识图谱；命中并复用 E386（HMDFS getcwd 风暴，唯一有效解法是 configure 命令行内联 CONFIG_SHELL=/bin/sh）、E091（musl 需 -D__MUSL__）、E017（GitHub URL 镜像注入会污染活文件 conandata）、E011/E114（config.status 的 umask 077）与 -fno-common 重复符号族（本仓先例 archives/c/chordii/4.5.3b、archives/a/aris/2.2、archives/a/arpalert/2.0.12、archives/b/barcode/0.99 的 tc.extra_cflags 写法）
- 知识库扩展：无新增条目。理由：本轮唯一新面孔是 pimd 的暂定定义重复符号问题，而它在仓内已有 -fcommon 先例（口径已注明：W4 审计在 HEAD 工作树复算 **135**；本窗复核 工作树 136 / git 跟踪面 133 / `origin/main` 已合并归档面 **130** = 原申报值）⇒ 属既有条目覆盖面内，B 判定 = hit，不产草稿
- 关联 Issue：无需新建（B 判定 = hit；【知识库扩展】类 Issue 仅随 create 建）
- 交付面与测试口径：交付命令集 11 收为 9（8 daemon 加 watchquagga），关掉的是 vtysh（readline 制品未发布的发布缺口）与 nhrpd（c-ares 同理），BGP/OSPF/RIP/IS-IS/PIM 与 zebra netlink 面全保留；W3 第 11 轮 automake 判决 TOTAL 11 / PASS 11 / SKIP 0 / XFAIL 0 / FAIL 0，五维账本＝静态 11、可执行 11、通过 11、跳过 0、失败 0，check_PROGRAMS 按**真 create 日志** <仓根>/.ci_logs/conan_build_quagga_1.2.4.log 的 Making all in tests 段 CCLD 去重实测 21（静态 16 加 BGPD 5；归档里的 reports/conan-create.log 是 test_package 单跑日志、含 0 条 CCLD，别拿它数），未预设任何 skip 也未产生 skip；日志内 ^PASS: 行 10 条（# TOTAL: 11 源于上游 tabletest 重列两次，见 §4.1）；第 11 轮证据指纹：reports/w3-local-ci.log md5 b81af20be3c5bc4bafcffd46acc284c0 / 113862 B / mtime 01:57 / 53 个判决标记，.ci-result.json integrity_hash d825c1bda660f24f 且 log_sha256 7ffe1f5943df7632… 实测等于 sha256(该日志)，真 create 日志 md5 fc86bdff5886e9313f39e6966e16783d，而第 10 轮件 md5 19d2dfd2… 与之不同 ⇒ 第 11 轮是真重跑
- 本地门禁两条非绿项的定性（不属本包缺陷，已按框架存量矛盾披露）：ohc-run build 的 Step1 与 finish 的 step5b 同根＝scripts/ohc/init_build.py:432-438 的 --no-download 分支要求 init-build 探索期留下的 quagga-1.2.4.orig / .work 目录，而交付归档布局是 archives/q/quagga/1.2.4 ⇒ 属**工具链码路错配**；驱动那 8 个可用 URL 池里也没有本包 conandata.yml 定案的 codeload 源（2026-09-25 本窗真机复测：savannah 的 .gz 重定向后 HTTP 404、W4 审计窗探测为 rc=28 / http=000 超时，两种形态都取不到源码；waterlan 的 .gz 带 Range 实测 HTTP 206 可达 ⇒ 上一版"旧 URL 真机 404"措辞不准确，已按实测更正）；要变绿只能伪造 .orig/.work 或重跑 init-build 覆盖手写配方，两条都拒（前者触 R34/R9 造假证据、后者毁已提交的手写配方）⇒ 定性结论不变：工具链码路错配，不属欺骗类；step8 的 packaging/ 与 reports/ 与 .staging-verified 属留盘不提交的生成物（.gitignore 第 96 与 238 行），且往归档目录放 packaging/ 会直接撞本轮已 PASS 的 JC3 打包产物检测
