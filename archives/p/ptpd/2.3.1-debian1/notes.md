# ptpd 2.3.1-debian1 适配笔记

## 版本来源

平台任务版本 `2.3.1-debian1` 就是 Debian 源包的发布标识：上游 orig tarball 名为
`ptpd_2.3.1-debian1.orig.tar.xz`，其 `configure.ac` 的 `AC_INIT` 版本为 `2.3.1`。
sourceforge 上是另一棵更旧的树，只有 Debian 池同时提供这个确切版本，故 `conandata.yml`
用 HTTPS 的 Debian pool URL，sha256 `c37e6f52…` 与 `ptpd_2.3.1-debian1-6.dsc` 逐字符一致。

## 构建

上游自带**已生成**的 autotools 树（`configure` + `Makefile.in` + `build-aux/`），因此
配方直接运行随包 `configure`，不做 autoreconf。

真机 `conan create` 过程中的四处关键点（均已实测）：

1. **host/build 三元组**：`conan create` 时 host 与 build 都是 OHOS，
   `conan.tools.build.cross_building()` 为假，Conan 的 AutotoolsToolchain **不会**下发
   `--build/--host`；于是 configure 会调用随包 `config.guess`，而它不认识 bionic。
   配方显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`，
   `config.guess` 不再被调用，`$host` 仍命中 configure.ac 的 `*linux*` 分支
   （用于探测 `linux/net_tstamp.h`）。
2. **HMDFS 与 umask 077**：`configure` 生成的 `config.status` 会 `umask 077` 建临时目录，
   但可写的 HomeArea（hmdfs）不按该模式生效，`config.status` 报
   `can't create ./confXXXX/subs1.awk: Permission denied`。`build()` 里把 `configure` 的
   `umask 077` 改成 `umask 022`（与 numactl 同法）。
3. **sockaddr_storage 重定义**：`dep/net.c` 里 `#include <linux/net_tstamp.h>` 会传递包含
   `<linux/socket.h>`，它重新定义 `<sys/socket.h>` 已有的 `struct sockaddr_storage`
   （E091/E119）。补丁预定义 UAPI 头防重复宏 `_UAPI_LINUX_SOCKET_H`。
4. **utmp/utmpx**：bionic 有 `<utmpx.h>` 但**没有** `setutxent()/pututxline()/endutxent()`
   （E121），链接期 `undefined symbol`。用 configure 缓存变量
   `ac_cv_header_utmpx_h=no ac_cv_header_utmp_h=no` 关掉登录记账代码。

另有一个补丁：`dep/sys.c` 无条件调用 `ether_ntohost()`；bionic 实现了
`ether_aton()/ether_ntoa()` 却**没有** `ether_ntohost()`，链接期未定义。按 R8
「不得引入平台条件编译宏」的要求，补丁**不改用 `__OHOS__`**，而是：
`patches/0002-sys-c-ether-ntohost.patch` 在随包 `configure`（及 `config.h.in`）的
`AC_CHECK_FUNCS` 列表里加入 `ether_ntohost`（`configure.ac` 因不参与构建、改动它会触发
缺失的 aclocal/automake 重生成，故不动），检测产生的 `HAVE_ETHER_NTOHOST` 在 `sys.c`
里用 `#ifdef` 保护调用；真机 `checking for ether_ntohost... no` → `/* #undef ... */`，
走 `unknown` 分支。这样是 configure 期特性探测，与同 PR 的 utmpx 处理方式一致。（P3 加固：
测试脚本改 `set -eu`、退出码改用 `[ "$rc" -eq N ]` 断言；补丁内注释不再误称「数字 MAC」。）

`--disable-snmp`（制品仓无 net-snmp）。`libpcap` 为可选（上游 `--disable-pcap`），
默认开启以贴合 Debian 打包；`-o ptpd/*:pcap=False` 可关。

## 测试

上游**无自动化测试**：`test/` 只有 3 个示例 PTP 配置与 `testing.org`（人工互操作指南），
无 `make check`、无测试程序 → 上游 N=0。适配后提供消费者 `test_package/test_ptpd.sh`
**12/12**：版本横幅、短/长帮助、默认配置导出、逐项设置帮助、未知选项报错路径。

## 平台能力实测（决定路径 A）

真机 aarch64、非 root：

| 能力 | 结果 |
| --- | --- |
| `setsockopt(SO_TIMESTAMPING, {0,RX_SOFTWARE,RX_HARDWARE})` | rc=0（内核接受） |
| `ioctl(SIOCETHTOOL, ETHTOOL_GET_TS_INFO)` | 无可用的 eth 接口 |
| `open("/dev/ptp0")` | ENOENT（无 PTP 硬件时钟） |
| `adjtimex()` | **SIGSYS（signal 31）被 seccomp 杀** |

即 OHOS 上 ptpd 可以构建、可以运行（观察/监控模式），但**无法用 adjtimex 校准系统时钟**，
也无 PHC；`adjtimex/SIGSYS` 与 `sockaddr_storage`、`utmpx` 均已被既有知识库条目
（E051/E164/E246、E091/E119、E121）覆盖，故按**路径 A**提交，不申报 B。
