# pktstat 1.8.5 适配笔记

## 编译环境

- 构建系统: autotools（**只有** `configure.ac` + `Makefile.am`，无 `configure`、无 autogen ⇒ 构建期必须 `autoreconf -fi`）
- 编译日期: 2026-10-01
- 编译器: clang 15（profile `tools.build:compiler_executables` → OHOS SDK clang，target `aarch64-linux-ohos`）
- profile: `ohos-aarch64-wsl`（本地，与 CI 的 `ci/conan/profiles/ohos-aarch64` 同构；`-pr:h` 与 `-pr:b` 同一 profile）
- 状态: built

## 软件与构建面（读源码所得，不是猜测）

pktstat 是「top 风格的网络连接流量查看器」：用 libpcap 抓取指定网卡的报文，按协议与端口聚合成 flow，
再用 ncurses 全屏界面每 `-w` 秒刷新一次。选项面很小（`main.c:170` 的
`getopt(argc, argv, "1A:a:BcEFi:k:lm:npPtTw:")`）。

- **BPF 过滤器不是自己写的**：`main.c:334-337` 走 `pcap_compile` / `pcap_setfilter`，
  `struct bpf_program` / `bpf_u_int32` 直接来自 `<pcap.h>`。
  `ether.c`/`ip.c`/`ip6.c`/`tcp.c`/`udp.c`/`sll.c`/`ppp.c`/`loop.c`/`frag.c`/`ipx.c`/`wol.c`
  是**按 DLT 分派的打标函数**（`ether_tag` / `ip_tag` / ...），不是 BPF 字节码。
- **libpcap 是硬依赖**：`configure.ac:85` `AC_CHECK_FUNC([pcap_open_live], , AC_MSG_ERROR(...))`。
- **ncurses 是硬依赖**：`configure.ac:87` `AC_CHECK_FUNCS([initscr], , AC_MSG_ERROR(...))`，
  `configure.ac:21-22` 分别用 `AC_SEARCH_LIBS(tgoto, [termlib termcap curses ncurses ocurses])`
  与 `AC_SEARCH_LIBS(initscr, [curses ncurses ocurses])` 探测。
  display.c 用 `initscr/cbreak/noecho`，resize.c 用 `resizeterm`（SIGWINCH 自适应）。
- 依赖全部走 **configure 的 AC_SEARCH_LIBS/AC_CHECK_FUNC 弱探测，没有 `--with-pcap` 这类强钉开关**，
  配方因此无需追加任何 feature 参数。
- `err.c` / `memcmp.c` / `strlcpy.c` **不在** `pktstat_SOURCES` 里，靠 `pktstat_LDADD = @LIBOBJS@`
  在 configure 判定需要时才拉进来（本次实测 `LIBOBJS =` 为空：musl 与 OHOS sysroot 都已具备
  `memcmp`/`strlcpy`，`err`/`errx`/`warn`/`warnx` 来自 libc）。
- `main.c`/多数 .c 用 K&R 风格函数定义与 K&R 参数表（`upcall_from_pcap(context, hdr, data) u_char *context;`），
  clang 15 默认 gnu17 下仍合法，只出 `-Wdeprecated-non-prototype` 警告，无需改源码。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tcp.c:121:19: error: use of undeclared identifier 'IPPORT_USERRESERVED'` | musl 的 `<netinet/in.h>`（OpenHarmony 的 libc）只保留 `IPPORT_RESERVED`，删掉了历史宏 `IPPORT_USERRESERVED`；BSD/glibc 一直定义为 1023（保留区之下的最高端口） | `patches/0001-tcp-port-reserved-constant.patch`：在 tcp.c 的 include 区加 `#ifndef IPPORT_USERRESERVED / #define ... 1023 / #endif`。守卫条件取自 libc 自身宏集而非任何平台宏（R8），libc 自带该宏的构建保持原值；语义不变，getservbyport 名称解析仍限定端口 ≤ 1023 |
| 2 | profile `[buildenv]` 导出 `CONFIG_SHELL=/data/service/hnp/bin/bash`，configure 启动即报 working directory cannot be determined | 该 bash 在 HMDFS 上 `getcwd()` 失败，autoconf 生成的 configure 会用 `$CONFIG_SHELL` 重新 exec 自身（E386） | 同一条 shell 命令内 `unset CONFIG_SHELL;` 后再跑 configure；`generate()` 期的 `env.unset()` 会被运行期重注入击败，故不放在那里。configure 参数仍取 `Autotools._configure_args`，配方不拼任何编译开关（R1/R33/R49） |
| 3 | `AC_SEARCH_LIBS(tgoto/initscr, [... curses ncurses ...])` 理论上找不到库 | 仓内 ncurses/6.6 只产出 `libncursesw.a`（无 `libncurses.a`、无 `libcurses.a`），短名 `-lncurses`/`-lcurses` 都链不到 | 无需干预：`AutotoolsDeps` 把依赖闭包的 `-l` 塞进 `$LIBS`，ncurses 的 `cpp_info.libs = ["ncursesw", "panelw", "menuw", "formw"]` 使 `-lncursesw` 在 `AC_SEARCH_LIBS` 跑链接测试时已在场 ⇒ 两个探测都命中（实测 `checking for initscr... yes`） |
| 4 | `autoreconf -fi` 在 CI 上失败：`Can't exec "aclocal": No such file or directory at /data/service/hnp/autoconf.org/autoconf_2.72/share/autoconf/Autom4te/FileUtils.pm line 299` → `autoreconf: error: aclocal failed with exit status: 2`（CI 构建 **#66008**） | 上游只带 `configure.ac`/`Makefile.am`，必须 `autoreconf -fi`，而 autoreconf 强制要求 `aclocal`（来自 automake）。**CI worker 镜像有 autoconf_2.72、没有 automake**。首版配方假定「worker 自带完整 autotools」——该假定只在本地 WSL 成立（系统 automake 1.16.5），在 CI clean 环境不成立，正是 W0b「历史/本地命令在 CI 环境里逐字可执行吗」被违反。判据：报错栈在 autoconf 的 `Autom4te/FileUtils.pm`（perl 代码）内 ⇒ perl 本身在 CI 正常，缺的只是 `aclocal` 可执行文件；且 6 个前置步骤全绿、失败发生在 `conan create` 第一步 | `requirements()` 增加 `self.tool_requires("automake/1.18")`，把 `bin/`（含 `aclocal`、`automake` 及其所需的 perl）注入 PATH。选 **1.18** 因已合入的 `archives/a/abiword-plugin-*/3.0.8` 用同一版本（CI 已验证绿）；1.18 与 1.19 的 `share/aclocal-1.x/obsolete.m4` 都仍定义本项目用到的 `AM_CONFIG_HEADER`，故过时警告仍是 warning 而非 error。此前「tool_requires 会被解析成 armv8 二进制、在 x86 worker 上跑不了」的顾虑**不成立**——CI worker 本身就是 aarch64 HarmonyOS |
| 5 | `AM_CONFIG_HEADER` / `AC_HEADER_STDC` / `AC_HEADER_TIME` / `AC_TYPE_SIGNAL` 均已过时 | configure.ac 写于 2012 年，autoconf 2.71 对这些宏只 warn（不跑 autoupdate），不阻断 | 无需补丁：实测 `autoreconf -fi` rc=0，`configure` 正常生成 |
| 6 | CI 构建 **#66033** 在 `worker-prep`/`git-clone`/`cleanup` 三个步骤全部失败，报 `/usr/bin/zsh: Out of memory`，耗时 0.01–0.05s | **平台/worker 侧故障（与本包内容无关）**：失败发生在 `conan create` 之前，构建内容根本没被执行；`zsh` 自身 fork 失败属机器资源问题 | 不改任何构建代码（layer A 处置原则）。待 worker 恢复后对新 SHA 重新触发即可 |
| 7 | （审计派生）`tool_requires` 注入的 automake 到底是 registry 那份还是本机那份？需要可证伪的判据，否则「本地绿」无法证明 CI 也会绿 | 两边都有 aclocal，光看构建成功无法区分 | 查生成的 `aclocal.m4` 版本戳：本机 automake 为 1.16.5，而生成物里 `am__api_version='1.18'` ⇒ 证明走的是 `tool_requires` 注入的 registry 那份 |
| 8 | CI 构建 **#66039** 在 `config.status` 阶段失败：`./config.status[742]: can't create ./confEjEJDa/subs1.awk: Permission denied` | **E011/E129（HMDFS 权限）**：autoconf 生成的 configure 用 `(umask 077 && mktemp -d "./confXXXXXX")` 建暂存目录；HMDFS 上 0700 目录回读为 0660（检索位丢失），于是往里写文件即 EACCES | `build()` 里 `_fix_configure_umask()` 就地把**生成**的 configure 内 `umask 077` 改写为 `umask 022`（实测命中 2 处 → 目录 0755，恢复检索位）。两处都在 configure 内，其中第二处是 autoconf 2.72 用 here-doc 产出 config.status 的那份副本，所以改 configure 即同时修好 configure 与 config.status（实测改后 configure/config.status 均为 `umask077=0, umask022=2`）。Makefile.in 里那 1 处属 automake 的 `distuninstallcheck` 目标，本包不运行该目标，刻意不动。configure 是我们 `autoreconf -fi` 自己生成的构建产物，故按 R6 就地改写而不进 patches/（与 lft/3.98 同形）；若字面量消失则打 warning 不静默 |
| 9 | CI 构建 **#66055** 只剩 1 条交付面断言红：`PKTSTAT_ARTIFACT_FAIL interp-is-ohos-loader (PT_INTERP=/lib/ld-musl-aarch64.so.1)` | **断言本身写错了，不是产物错了**：我把 `OHOS_INTERP` 硬编码成 `/lib/ld-linux-aarch64.so.1`（本地 WSL sysroot 的拼法），而 CI worker 上真实 OHOS SDK clang 产物的 PT_INTERP 是 `/lib/ld-musl-aarch64.so.1`。这与 #4 同类：**拿本地环境当平台事实**。CI 的值才是 ground truth | 改为接受 OHOS 64 位用户态加载器的两种拼法 `OHOS_INTERP_LOADERS = ("/lib/ld-musl-aarch64.so.1", "/lib/ld-linux-aarch64.so.1")`（前者是 CI 实测，后者是部分 OHOS sysroot / 本地 shim 的命名），断言名改为 `interp-is-ohos-64bit-loader`，并保留实测值打印。语义仍是"由 OHOS 64 位用户态加载器驱动"，只是不再锁死某一个 sysroot 的文件名。32 位 `ld-linux-armhf.so.1`、glibc `ld-linux.so.3`、空值与非加载器路径仍然一律拒绝 |

## 源码修改

- `patches/0001-tcp-port-reserved-constant.patch` — tcp.c 补回 `IPPORT_USERRESERVED`（见上表 #1）。
  0 处平台宏（`__OHOS__` / `__MUSL__` 等一律未用）。

## 依赖版本

| 依赖 | 版本 | 制品仓状态 | 备注 |
|------|------|-----------|------|
| libpcap | 1.10.6 | 已发布（ohpcd，recipe rev e4d43bf9） | 硬依赖，`pcap_open_live` 缺失即 configure 失败 |
| ncurses | 6.6 | 已发布（ohpcd，recipe rev 3dcfd3b6） | 硬依赖，`initscr` 缺失即 configure 失败 |

两者在仓内均为**纯静态包**（`libpcap.a` / `libncursesw.a`，无 .so），因此产出的 pktstat ELF 的
`DT_NEEDED` 只有 `libc.so` 一项——这既是 test_package 的一条断言，也意味着运行期不需要 loader 路径。

## 验证结果

```bash
# W0 依赖发布检查（R35：禁止用 conan list 判断）
conan download "libpcap/*" -r=ohpcd --only-recipe   # → libpcap/1.10.1, 1.10.6
conan download "ncurses/*"  -r=ohpcd --only-recipe   # → ncurses/6.4, 6.5, 6.6
conan download "pktstat/*"  -r=ohpcd --only-recipe   # → 0（新包，符合预期）

# R47 语言预检
python3 scripts/ohc-run.py lang-preflight pktstat 1.8.5 --src <src>
# → detected=c, task=cpp, c↔cpp 同族 → 继续适配

# W3 本地编译验证
conan create . --name=pktstat --version=1.8.5 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
# → rc=0；payload verified: bin/pktstat + share/man/man1/pktstat.1

# 同源门禁
CI_PACKAGES="archives/p/pktstat/1.8.5" zsh ci/conan/build_and_test.sh
# → 见 reports/w3-local-ci.log
```

断言统计：**11 条交付面静态断言 + 8 条消费者用例（7 通过 / 1 按技术原因 skip）= 19**。

上游测试清点：v1.8.5 **0 条**自动化测试，四条独立实测证据见
`test_package/MANIFEST.yml`（源码树无 `test*` 目录/文件、无测试驱动配置；
`configure.ac`(100 行) 与 `Makefile.am`(37 行) 中
`TESTS|check_PROGRAMS|check_SCRIPTS|add_test|AC_*_TEST` 命中数为 0；
automake 生成的 `Makefile.in`(969 行) 无 `TESTS`/`TEST_LOGS`/`check_PROGRAMS`；
打好本包补丁使树可编译后真跑 `make check` → rc=0、输出 0 行、无 `test-suite.log`）。
这是清点结论，不是"没环境"。

> **订正（2026-10-02）**：本文件与 `MANIFEST.yml` 此前把上游入口写成
> `make -n check` 报 "No rule to make target 'check'"。**该说法经实测证伪**：
> automake 无条件生成 `check` 目标，只是它是空壳（`check-am: all-am` 且配方为空），
> 真跑 `make check` 返回 rc=0 并执行 0 个用例。结论（N=0）不变，但证据表述已按实测改写。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/pktstat` | 主程序，aarch64 PIE，NX + RELRO，`DT_NEEDED` 仅 `libc.so` |
| `share/man/man1/pktstat.1` | 由 `pktstat.1.in` 经 sed 生成 |
| `licenses/COPYING` | 上游许可（public domain，David Leonard） |

## 注意事项

- **实时抓包类用例受容器能力限制**：`pktstat -1 -i lo -P -w 1` 在构建容器里被内核拒绝，
  实测 stderr 为 `lo: can't get TPACKET_V3 header len on packet socket: Not supported`
  （容器缺 AF_PACKET/TPACKET_V3），故按"具体技术原因"记 **skip** 而不是 pass。
  同环境下 `pcap_lookupdev()` 也会失败（`eth0: SIOCETHTOOL(ETHTOOL_GLINK) ioctl failed: Function not implemented`）。
  这是网络诊断类工具在 CI 环境的固有边界：能稳定断言的是**选项解析/校验/错误路径**，
  以及"libpcap 确实被链入并被调用"（坏网卡时回显 libpcap 自己的错误串）。
- 无权限判据时不要把 skip 记成通过：test.sh 的 marker 同时输出 `passed` / `passedCount` /
  `skipped` / `failed` 四个字段，test_package 的 conanfile 对三组期望值做硬断言，数量对不上即失败。
- 原站 `www.adaptive-enterprises.com.au/~d/software/pktstat/` 已下线（http 301 到 https 后连接失败），
  配方取 Gentoo 包数据库登记的 Upstream `https://github.com/dleonard0/pktstat` 的 `v1.8.5` 标签
  （R39：GitHub 为官方源形态，非个人 fork/网盘/CDN）。
- `VERSION` 宏（`main.c:244` 的版本横幅）在 `configure.ac` 里对应的 `AC_SUBST` 是注释掉的
  （第 10 行，为修 automake-1.4 的 brokenness），但实测横幅仍正确输出 `1.8.5`，无需补丁。
- **`make check` 是空壳，不要据其存在与否推断"上游有测试"**：automake 无条件生成 `check`
  目标，本包实测 `check-am: all-am` 配方为空、`TESTS`/`TEST_LOGS` 均为空、真跑 `make check`
  rc=0 且不产出 `test-suite.log`。判断上游测试数要看 `TESTS`/`check_PROGRAMS`/`check-local`
  是否有内容，而不是 `check` 目标是否存在。
