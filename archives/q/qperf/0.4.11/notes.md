# qperf 0.4.11 adaptation notes

## 编译环境

- 构建系统: autotools（上游 tag tarball 无生成物，构建期 bootstrap）
- 编译日期: 2026-09-25（与两级 manifest 的 `build_date` 同值。取的是 finish 真实回写的文末 `**编译结束**: 2026-09-25 02:28` 与 `.ci-result.json` 的 `2026-09-25T02:29:17`；门禁在 2026-09-25 连跑两轮——门禁首轮 01:46:38 起跑（`~/tmp/uc2/z32b-qperf/go_finish.out:1`）、整改轮 02:28–02:29 收尾（`z32c-qperf/61_finish.log` 与 `reports/` 的回写时间）；测试层首轮自 2026-09-24 夜间起跑并跨零点，故本行只记 finish 回写日，不再写日期区间）
- 编译器: clang（OHOS SDK `/data/service/hnp/bin/clang`，profile `ohos-aarch64`，
  `os=OHOS os.version=6.0 arch=armv8 compiler.version=15`）
- 构建主机: B 机（HarmonyOS aarch64，8 核 / 31G），worktree
  `~/qzy/主理-32-qperf-0.4.11`（z26 窗由 `~/qzy/主理-26-qperf-0.4.11` 无损接管，
  z32 窗再无损移接为当前名，均为 `git worktree move`，非另建），
  `CONAN_HOME=~/tmp/ch/home-z23-qperf`
- 状态: built（conan-verify 全绿 + finish W3 本地 CI 通过）

## 源码取证

| 项 | 值 |
|---|---|
| 上游 | `https://github.com/linux-rdma/qperf` tag `v0.4.11` |
| 归档 | `https://github.com/linux-rdma/qperf/archive/refs/tags/v0.4.11.tar.gz` |
| 体积 | 60027 字节 |
| SHA256 | `b0ef2ffe050607566d06102b4ef6268aad08fdc52898620d429096e7b0767e75` |

SHA256 由两条独立网络路径（Windows 侧 codeload 直连、鸿蒙 A 机
`github.com/.../archive` 跟随重定向）分别下载并比对一致后取用；下载时逐次核对
HTTP 状态码与 `size_download`，未使用任何镜像代理，未改动校验和。
B 机构建主机本身不可达 github.com/codeload.github.com（`curl` connect 失败，
HTTP=000），源码经 base64 管道搬运后在 B 机复算 SHA256 一致。

**上游版本串自相矛盾（如实记录，不改哈希/不改版本）**：`src/qperf.c` 的
`VER_MAJ/VER_MIN/VER_INC = 0/4/11`（`qperf --version` 输出 `qperf 0.4.11`），
而 `configure.ac` 的 `AC_INIT(qperf, 0.4.10)` 写的是 0.4.10。本适配的任务版本、
Conan 版本、归档目录、分支名一律为 `0.4.11`（与 tag 与二进制自述一致）；
`AC_INIT` 只影响 automake 生成的 dist 目录名，本次不打 dist 包，未做补丁。

## 编译步骤

1. `get()` 解包（`strip_root=True`）。
2. bootstrap autotools（等价上游 README 的 `./autogen.sh`）：
   `aclocal --force` → `automake --foreign --add-missing --copy --force-missing`
   → `autoconf --force`，全部在源码根目录执行。
3. `configure`（conan `AutotoolsToolchain` 注入 `--prefix` 与 OHOS clang Flags，
   配方未额外传任何 configure 参数，遵守 R1 参数最少化）。
4. `make -j1`（HMDFS 上 GNU make jobserver FIFO 不可靠）。
5. `make install` + 拷贝 `COPYING` 到 `licenses/`。
6. OHOS 上对 `bin/qperf` 做 `binary-sign-tool -selfSign 1` 自签并用
   `llvm-readelf -SW` 核验 `.codesign` 段唯一（否则内核拒绝 exec）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag tarball 里没有 `configure`，直接 `Autotools.configure()` 无从执行 | 上游只发布 git tag 自动归档，不含 autotools 生成物（README 要求先跑 `./autogen.sh`） | `build_requirements()` 声明 `automake/1.18`，`build()` 内在 `configure` 缺失时按 aclocal→automake→autoconf 顺序 bootstrap |
| 2 | 直接调用 automake 包的 `bin/automake`/`bin/aclocal` 报 `Can't locate Automake/Config.pm in @INC (… //share/automake-1.18 …)` | 该包用 `#!/bin/sh` 包装脚本从 `$0` 推导 perl libdir；OHOS 包布局下推导结果为空前缀 | 经 perl 解释器直调包内真实入口 `bin/.aclocal-real` / `bin/.automake-real`，显式 `-I <pkg>/share/automake-1.18`、`--automake-acdir`、`--system-acdir`（libdir 版本由 glob 推导，不写死机器路径） |
| 3 | 主机 `~/usr/local/bin/automake` 无法执行（`No such file or directory`） | 脚本 shebang 为 `#!/usr/bin/perl`，OHOS 的 perl 只在 `/data/service/hnp/bin/perl` | 不依赖 PATH 上的 automake，统一显式传解释器（`shutil.which("perl")` 回退 SDK 绝对路径） |
| 4 | out-of-tree 构建下 `./mkhelp` / `./mkman` 找不到脚本与输入 | `src/Makefile.am` 的规则是 `help.c: help.txt` + 命令 `./mkhelp RDMA`，`qperf.1: help.txt` + `./mkman`，全部按 CWD 相对路径解析 | `layout()` 设 `folders.build = "."` 强制 in-tree 构建，不改动上游生成规则 |
| 5 | `automake` strict-GNU 要求 NEWS/ChangeLog 等文档 | `configure.ac` 只写 `AM_INIT_AUTOMAKE`（无 `foreign`），而配方直接跑 automake | 与 `autogen.sh` 一致：bootstrap 前 touch `NEWS`/`README`/`ChangeLog`，automake 传 `--foreign --add-missing --copy` |
| 6 | 链接期 `ld.lld: error: undefined symbol: sockatmark`（G2 FAIL） | OHOS 的 C 库对 POSIX 标准函数 `sockatmark(3)` **既不声明也不导出**（sysroot 头树命中 0 处、libc.so 导出 0 个；自带原型仍链接失败 ⇒ 缺的是符号不是声明） | 补丁 0001：按特性改发该函数规范自身定义的 `ioctl(fd, SIOCATMARK, &val)`。详见「源码修改」与 B 草稿 |
| 7 | 真机消费者测试 4 项 socket 传输全部 `fcntl F_SETOWN failed: Invalid argument`（rc=1，一个字节都没交换） | HongMeng 内核**完全不实现 signal-ownership 这一族 fcntl**（本机探针实测见下节），上游把 `F_SETOWN` 失败当致命错误 | 补丁 0002：仍请求 ownership，但只有当失败原因不是`EINVAL`/`ENOTSUP`（即不是"内核未实现"）时才中止；`F_SETOWN` 可用的平台行为逐字不变 |
| 8 | 测试脚本报 `RESULT pass=8 fail=6 total=14`，其中 3 项明明已产出数值仍判 FAIL | 断言层用的字段名与 qperf 真实输出不符（qperf 打的是 `latency`/`send_bw`/`recv_bw`，脚本 grep 的是 `lat`/裸 `bw`）；且 HarmonyOS **没有 `ldd`**，链路一致性断言被静默跳过，断言数与申报数不可比 | 字段名按实测输出对齐；`ldd` 改为 `readelf -d`（缺工具时判 FAIL 而非跳过）；`MANIFEST.yml` 断言数与 `test_package/conanfile.py` 的通过下限同步到实测值 25（z32 窗把本构建注册的其余 6 个传输也纳入实跑后，三处再同步为 **31**，见下一节第 10 行） |
| 9 | 把 `command -v timeout` 的结果当命令前缀用时，8 个用例全部 `rc=1` 且日志里是 `alias: … invalid alias name` | HarmonyOS 的 toybox `sh` 里 `timeout` 是个**别名**，`command -v timeout` 返回别名文本 `alias timeout=timeout` 而不是路径（`/usr/bin/timeout` 与 `~/usr/local/bin/timeout` 其实都在），拼进命令行后真正的 `timeout` 从未被执行 | `run_tests.sh` 新增 `run_cmd()`：按**可执行位**依次解析 `/usr/bin/timeout` → `$HOME/usr/local/bin/timeout` → 直接执行，不再用 `command -v` 的返回值当命令（z32 窗实跑复核发现并修掉） |
| 10 | 本节原先申报"上游登记 20 个传输测试、共 22 项、RDMA 族 10 个"，并把 `rds_/sctp_/sdp_` 记成"平台协议栈未验证" | 清点只查了 `help.txt` 的 socket 段与 `rc_*` 前缀，漏了 `src/qperf.c` 里 `TEST Tests[]` 的完整注册表（`uc_*`/`ud_*`/`ver_rc_*`/`xrc_*` 四族没数），也没对 sctp/sdp/rds 下任何探针 | z32 窗按注册表逐项重算为 **36 项**（RDMA 族 **24**），并对 sctp/sdp/rds 逐个下 `socket()`/`open()` 探针真跑到出 errno（见「传输路径实测矩阵」与 `reports/test-report.md`） |

## 源码修改

### 补丁 `0001-support-sockatmark-via-siocatmark.patch`（patch_type: portability）

`src/support.c` 的 `urgent()`（z32 窗按 `grep -rn urgent src/` 复核：定义在
`support.c:419`（z32c 窗在**补丁前原始树** `grep -n 'urgent(void)'
`src/support.c` 实测命中 419 行；原文 445 取自打过补丁的树，属行号错位），唯一调用点是
`qperf.c:719` 的 `sig_urg()`，即 SIGURG 处理器）
调用 POSIX 的 `sockatmark(3)`。
OHOS 工具链的 C 库**既不提供该函数的声明，也不导出该符号**，链接期表现为：

```
support.c:466:17: warning: call to undeclared function 'sockatmark';
    ISO C99 and later do not support implicit function declarations
ld.lld: error: undefined symbol: sockatmark
>>> referenced by support.c
ld.lld: error: linker command failed with exit code 1
```

缺失的不是 GNU/BSD 扩展，而是 **ISO POSIX 标准函数**（`sockatmark` 由
POSIX.1-2001 起标准化，glibc/macOS 的 `<sys/socket.h>` 都有声明）。

修法取 `sockatmark(3)` 规范自身定义的底层操作：`ioctl(fd, SIOCATMARK, &*atmark)`
——SDK 的 `<bits/ioctl.h>` 确实提供了 `SIOCATMARK`，`<sys/ioctl.h>` 提供 `ioctl`
原型。musl 自己的 `sockatmark()` 实现也是同一条 ioctl，因此本补丁与该函数的
参考实现同构，只是把它放到调用方。

补丁用 `#ifdef SIOCATMARK` 按**特性**而非平台分流：具备该 ioctl 的平台直接发
ioctl，不具备的平台保留原 POSIX 调用，故对 glibc/macOS 等平台零行为变化，
补丁文件中不含任何平台宏（`__OHOS__` 等）。

**运行时覆盖如实申报（z32 窗实跑复核，不记为通过）**：`urgent()` 只在
"对端调 `error()` 发 `send(RemoteFD, "?", 1, MSG_OOB)` → 本端收 SIGURG"这条
**远程失败上报链**上被触发。本轮把本构建登记的全部 12 个测试真跑了一遍，
客户端**从未取回对端的错误报文**（`sctp_*`/`sdp_*` 只打印了客户端自己的诊断，
服务端那句 `unable to make SCTP socket` 始终只在服务端日志里），
服务端侧则被 `urgent()` 自己的 `if (!Debug && !is_client()) die();` 提前退出
（上游 CLI 没有开 `Debug` 的选项）。
⇒ **本包不申报补丁 0001 的运行时覆盖**，其证据只有：链接期符号解析成功
（不打补丁即 `undefined symbol: sockatmark`、G2 FAIL）+ 与 musl `sockatmark()`
同一条 ioctl 的语义等价 + 非 OHOS 平台零改动。
"OOB/urgent 远程失败上报链在本平台不可用"与补丁 0002 同根
（signal-ownership / socket-signal 族未实现），按**能力缺失导致的行为退化**记录，
不影响 `tcp_*`/`udp_*` 的测量链路（那 4 项不依赖 SIGURG）。
证据：`~/tmp/uc2/z32-qperf/45_urgent_path.log`、`30_unsupported_run.log`。


### 补丁 `0002-qperf-treat-unimplemented-f_setown-as-non-fatal.patch`（patch_type: portability）

`src/qperf.c` 的 `remotefd_setup()`（客户端 connect 路径 line 1542、服务端 accept 路径 line 1359 均调用）
把 `fcntl(RemoteFD, F_SETOWN, getpid())` 失败当致命错误。本机用独立探针实测（**不含任何 qperf 代码**，
脚本 `~/tmp/uc2/z26-qperf/probe_fcntl.c`，日志 `step_probe.log`）：

| 调用 | AF_INET/SOCK_STREAM | AF_INET/SOCK_DGRAM | 普通文件 |
|---|---|---|---|
| `fcntl(F_SETOWN, getpid())` | **-1 / EINVAL(22)** | **-1 / EINVAL(22)** | -1 / ENOTSUP(95) |
| `fcntl(F_GETOWN)` | 返回 -22（errno 未置位，f_op->getown 未实现、错误码直接漏出） | 同左 | -1 / ENOTSUP |
| `fcntl(F_SETOWN_EX, F_OWNER_PID/TID)` | **-1 / EINVAL** | **-1 / EINVAL** | -1 / ENOTSUP |
| `fcntl(F_SETSIG, SIGIO)` | **-1 / EINVAL** | **-1 / EINVAL** | -1 / ENOTSUP |
| `fcntl(F_SETFL, O_ASYNC)` | 0 / OK | 0 / OK | 0 / OK |
| `ioctl(FIONBIO)`（同函数上一句） | **0 / OK** | **0 / OK** | 0 / OK |

SDK `<fcntl.h>` 的命令号是齐的（`F_SETOWN=8`、`F_GETOWN=9`、`F_SETOWN_EX=15`、`F_SETSIG=10`、
`O_ASYNC=020000`、`SIGIO=29`），所以**不是头文件缺宏，而是内核不实现这一族**；
另注：`struct f_owner_ex` 与 `F_OWNER_*` 在 SDK 头里**没有声明**（探针首次编译即报
`variable has incomplete type 'struct f_owner_ex'`），故 `F_SETOWN_EX` 这条路在本平台连编译都过不去。

**为什么降级是安全的（关键论据，非猜测）**：`F_SETOWN` 只决定"将来 SIGIO 投递给谁"，
而 qperf 从不武装那个通知。**取证前提：下面这组读数一律取"补丁前的原始树"**
（`~/tmp/ch/home-z23-qperf/p/qperff9e257013fb3a/s/src/`，未应用本包任何补丁），
对 `src/` 整树按符号逐个 `grep -o | wc -l` 计数：
`SIGIO=0`、`O_ASYNC=0`、`F_SETFL=0`、`F_SETSIG=0`、`F_GETOWN=0`、`F_SETOWN_EX=0`，
`F_SETOWN` 只 2 次命中且同属**唯一调用点** `src/qperf.c:1559`（1560 行是该调用自己
的错误报文文本）；全树也没有安装任何 SIGIO 处理器。
即该 ownership 建立后**无人消费**，去掉致命失败不可能改变任何测量值。

⚠ **取证口径更正（z32c 窗）**：上一轮那条 `44_sigio_consumer_check.log` 扫的是
**已打补丁**的树（日志内 `SIGIO=2 / O_ASYNC=1 / F_SETSIG=1 / F_SETOWN=6`，命中全部
来自补丁 0002 自己的注释与错误文本），**不能**支撑"无消费者"这一论证——拿去复算
即成假证据。本节改按原始树重算，读数见上（复算命令与输出
`~/tmp/uc2/z32c-qperf/50_pristine_tree_grep.log`）。
修法刻意保留"仍去请求 ownership"，只在 errno 为 `EINVAL`/`ENOTSUP` 时不中止，
因此真正误用句柄（其它 errno）仍会报错，`F_SETOWN` 可用的平台行为逐字不变。

补丁按 `git apply --check` 与 `git apply --reverse --check` 双向 `rc=0` 验证，
且**新增行不含任何平台宏**（`__OHOS__` 计数 0，过 R8/PF5 口径）。

## 依赖版本

- `tool_requires`: `automake/1.18`（构建期工具，非运行依赖）。
  二进已在 ohpcd 制品仓核实可下载：
  `conan install --requires=automake/1.18 --build=never -pr:h=ohos-aarch64` →
  `automake/1.18#65a7ba60030d238eb8bb32266391cfc5:01d92cf349a0dd98ff915f4bd99a04430171517f - Download (ohpcd)` → `Package installed`。
- `requires`: 无。RDMA 传输未纳入（依据见下节实测）。

## 传输路径实测矩阵（RDMA vs socket）

`configure.ac` 的探测方式是 `AC_CHECK_LIB(ibverbs, ibv_open_device, RDMA=1)` +
`AC_CHECK_LIB(ibverbs, ibv_open_xrc_domain, HAS_XRC=1)` +
`AC_CHECK_LIB(rdmacm, rdma_create_id)`，结果只驱动
`AM_CONDITIONAL(RDMA/HAS_XRC, …)`。**缺库时是自动降级、不是硬报错**，
与上游 README「If the library ibverbs is not found, a version of qperf is built
that does not support the RDMA tests」一致。

**真机实测（HarmonyOS PC B 机，loopback 自环）。本构建注册的 12 个测试 z32 窗全部真跑过：**
前 6 项为 z26 窗两轮 + z32 窗两轮（`-t 1` 与 `-t 3`）；后 6 项（`sctp_/sdp_/rds_`）
是 z32 窗**首次真跑**——此前只写过"平台协议栈未验证"，属未经复核的申报。

服务端：`qperf -lp <port> &`（脚本自己起、按自己的 PID 回收），客户端逐条：

| # | 测试 | 命令 | rc | 关键输出（真实数值） | 判定 |
|---|---|---|---|---|---|
| 1 | `conf` | `qperf 127.0.0.1 -lp 19821 conf -t 1` | 0 | 打印会话配置（z32 复跑见 `-lp 19831`，输出 `loc_os = HarmonyOS HongMeng Kernel 1.12.0`） | 用作就绪探测，判通过 |
| 2 | `tcp_bw` | `qperf 127.0.0.1 -lp 19821 -t 1 tcp_bw` | 0 | z26 轮 `4.51 / 4.32 GB/sec`；z32 轮 `-t 1 = 4.23`、`-t 3 = 3.86 GB/sec` | PASS |
| 3 | `tcp_lat` | `qperf 127.0.0.1 -lp 19821 -t 1 tcp_lat` | 0 | z26 轮 `19.6 / 18.4 us`；z32 轮 `-t 1 = 31.6`、`-t 3 = 29.4 us` | PASS |
| 4 | `udp_lat` | `qperf 127.0.0.1 -lp 19821 -t 1 udp_lat` | 0 | z26 轮 `20.9 / 19 us`；z32 轮 `-t 1 = 28.9`、`-t 3 = 35.3 us` | PASS |
| 5 | `udp_bw` | `qperf 127.0.0.1 -lp 19821 -t 1 udp_bw` | 0 | z26 轮 `send 4.66 / 4.5 GB/sec`、`recv 531 MB / 739 MB/sec`；z32 轮 `-t 1 = 3.54 / 1.69`、`-t 3 = 3.74 / 1.67 GB/sec` | PASS |
| 6 | `quit` | `qperf 127.0.0.1 -lp 19821 quit` | 0 | 服务端进程随即自行退出（z32 轮 `server_reaped_by_quit=yes`，无需 kill） | PASS |
| 7 | `sctp_bw` | `qperf 127.0.0.1 -lp 19832 -t 1 sctp_bw` | **1** | 无任何测量字段；客户端 `getaddrinfo failed: Unrecognized service`，服务端 `unable to make SCTP socket` | **已执行，被内核能力拒绝（不计通过）** |
| 8 | `sctp_lat` | 同上，测试名 `sctp_lat` | **1** | 同 7 | 已执行，被内核能力拒绝 |
| 9 | `sdp_bw` | 同上，测试名 `sdp_bw` | **1** | 客户端 `getaddrinfo failed: Unrecognized service`，服务端 `unable to make SDP socket` | 已执行，被内核能力拒绝 |
| 10 | `sdp_lat` | 同上，测试名 `sdp_lat` | **1** | 同 9 | 已执行，被内核能力拒绝 |
| 11 | `rds_bw` | 同上，测试名 `rds_bw` | **1** | `socket failed: Address family not supported by protocol`（= `strerror(97)`，qperf 与探针两侧一致） | 已执行，被内核能力拒绝 |
| 12 | `rds_lat` | 同上，测试名 `rds_lat` | **1** | 同 11 | 已执行，被内核能力拒绝 |

数值为多轮真机运行的区间（`-t 1` 单次采样，且同机他窗在跑构建：z32 轮
`gate.sh` 实测 load 20.4），两窗两列都写以免被当成稳定基线；
申报口径只取"字段存在 + 数值严格为正 + 退出码 0"，**不申报绝对吞吐值**。
输出格式（决定断言字段名）：`tcp_bw -> bw`、`tcp_lat/udp_lat -> latency`、
`udp_bw -> send_bw + recv_bw`（注意 `udp_bw` 没有裸 `bw` 字段，早期断言即栽在此）。
日志：`~/tmp/uc2/z32-qperf/20_supported_run.log`、`30_unsupported_run.log`
及各 `<test>_t{1,3}.client.log` / `<test>.client.log`。

**`sctp_` / `sdp_` / `rds_` 被拒的可复算根因（z32 窗独立探针，不含任何 qperf 代码）**
探针 `~/tmp/uc2/z32-qperf/probe_transport.c` + `probe_qperf_path.c`（SDK clang `-O0`
编译 + `binary-sign-tool -selfSign 1` 自签后原生执行），每组带阳性对照
（`AF_INET/SOCK_STREAM`、`AF_INET/SOCK_DGRAM`、`AF_INET6/SOCK_STREAM` 全部 `OK fd=3`）：

| 传输 | qperf 实际发的调用（源码依据） | 实测结果 |
|---|---|---|
| SCTP | `src/socket.c:717-721` 把 `ai_protocol` 从 6 改写成 `IPPROTO_SCTP` ⇒ `socket(AF_INET=2, SOCK_STREAM=1, 132)` | **errno=93 `EPROTONOSUPPORT`（Protocol not supported）**；`SOCK_SEQPACKET` 版本 errno=94 |
| SDP | `src/socket.c:47` `#define AF_INET_SDP 27`，`711-716` 改写 `ai_family` ⇒ `socket(27, SOCK_STREAM, 6)` | **errno=97 `EAFNOSUPPORT`（Address family not supported by protocol）**；另试 `43` 亦 97；`/dev/xpmem`、`/sys/module/xpmem`、`/sys/module/sdp` 全 `open()` errno=2 |
| RDS | `src/rds.c:52-90`：`AF_RDS` 未定义时读 `/proc/sys/net/rds/pf_rds`，读不到退回 `DEFAULT_AF_RDS 21`；`rds_socket()` 用 `SOCK_SEQPACKET` | `/proc/sys/net/rds/pf_rds`、`/proc/net/rds`、`/sys/module/rds_tcp` 全 `open()` errno=2 ⇒ 走 21 分支；`socket(21, SOCK_SEQPACKET, 0)` **errno=97**；试主线号 27 亦 97 |

客户端那句 `getaddrinfo failed: Unrecognized service` 已实测证明是**下游假象**：
服务端子进程 `error()` 后先退出、没回传数据端口，客户端把 `0xFFFFFFFF` 当端口用，
`getaddrinfo(..., service="4294967295")` 才返回 `EAI_SERVICE(-8)`
（`probe_qperf_path` 原文：`TCP, service=4294967295 -> eai=-8`；
同一 service 换成 `19832`/`0` 时 `eai=0`，随后 `socket(2,1,132)` 仍 errno=93）。
⇒ 根因是 `socket()` 的能力缺失，不是配方/端口/DNS 配置问题。

**产物链接面（`readelf -d` 实测，非 `ldd`——OHOS 无 ldd）**：`DT_NEEDED` 仅
`[libc.so]`，**无 `libibverbs` / `librdmacm`**；与 `qperf --help tests` 中 `rc_*` 命中 0 条
**互相印证**（该交叉核查是消费者测试的链路一致性断言，两侧不一致即判 FAIL）。

**RDMA / IB / RoCE 段：未执行（本构建产物根本不含该传输），按"三层能力缺失"申报。**
证据取证窗 = 主窗 2026-09-24 + z32 窗 2026-09-25 独立复跑，
**探针口径 = `open()` 系而非 `stat()`**
（`stat()` 对这类路径全假阴性，判设备节点/能力时必须用 `open()`）。三层实测：

1. 设备节点 / sysfs：`/dev/infiniband/uverbs0`、`/sys/class/infiniband`、
   `/sys/module/ib_core` 以 `open()` 探测全部 `errno=2 (ENOENT)`（z32 复跑同结果）；
2. 用户态库：`readelf -d bin/qperf` 全程序头无 `ibverbs`/`rdmacm` 引用（`grep` rc=1）。
   ⚠ 原申报写的"`ldconfig -p` 无 ibverbs/rdma 条目"这条**证据口径不成立**——
   z32 实测本机 `command -v ldconfig` 为空（ldconfig 根本不在 PATH），
   该结论改由 ELF 面承担；
3. 内核协议族：`/proc/net/protocols` 可读，23 条注册行 `HTP MTP L2TP/IPv6 L2TP/IP
   PPPOL2TP KEY PACKET MPTCPv6 PINGv6 RAWv6 UDPLITEv6 UDPv6 TCPv6 PPTP PPPOE ALG
   UDP-Lite MPTCP PING RAW UDP TCP NETLINK`——**其中 IPv4 的 `TCP`（size 列 2400）、
   `UDP`（size 列 1152）、`PING`、`RAW`、`NETLINK` 全都在列**，与本包实测可用的 4 项
   socket 传输相符；缺席的是 `SCTP`/`RDS` 与 RDMA 族条目，与 `socket()` 侧的
   `errno=93`（SCTP）/`errno=97`（SDP、RDS）**互印**。
   ⚠ 该表**只作辅证**：早先那句"清单连 IPv4 TCP/UDP 都没列"是**大小写敏感的 grep**
   读出来的（表内协议名是大写），属误读，已在 z32c 窗更正。
   判能力一律以 `socket()`/`open()` 的 errno 为准。

⇒ 上游 configure 的 `AC_CHECK_LIB(ibverbs, ibv_open_device)` 因此在 OHOS 上探测失败，
`AM_CONDITIONAL(RDMA)` 取假，编出**无 RDMA 版本**——上游 README 明示
「If the library ibverbs is not found, a version of qperf is built that does not support
the RDMA tests」，属受支持配置，**不是适配缺陷**。

**分母不缩（z32 窗按 `src/qperf.c` 的 `TEST Tests[]` 注册表重算，更正原申报）**：
上游注册的测试总数是 **36 项**，不是 22 项——

```
grep -c "^    test(" src/qperf.c                       -> 36
12 无条件 + 21 在 #ifdef RDMA 内 + 3 在 #ifdef HAS_XRC 内 -> 36
RDMA 族 24 = rc_* 10 + uc_* 6 + ud_* 3 + ver_rc_* 2 + xrc_* 3
socket 族 10 = tcp_/udp_/sctp_/sdp_/rds_ 各 bw+lat
杂项   2 = conf + quit
```

原申报把 RDMA 族只数成 `rc_*` 10 个，漏了 `uc_*`/`ud_*`/`ver_rc_*`/`xrc_*` 四族 14 个。
`src/help.txt` 的 `Tests +RDMA` 段与上表逐条一致，`Tests -RDMA` 段恰为本二进制的 12 项。

⇒ 账本：**36 = 实测通过 6 + 已执行被内核能力拒绝 6 + 未执行（未编进产物）24**。
后 30 项一律**不计入通过**；本构建注册的 12 项已 100% 真跑过。

## R51 上游测试清点（静态证据）


对解包后的 `qperf-0.4.11` 全树执行清点：

```
grep -rnE "enable_testing|add_test|AM_TESTS_ENVIRONMENT|TESTS *=|check_PROGRAMS|CTEST" . → 0 命中
find . -type d \( -name test -o -name tests \)                                         → 0 命中
grep -rnE "^(check|installcheck)" --include=Makefile.am .                                → 0 命中
find . -iname "*test*"                                                                   → 0 命中
ls -a | grep -iE "travis|gitlab|github|circle"                                           → 0 命中
```
> **清点命令勘误（W4 r2 P3）**：上列五条的**首轮原文按字面不可复算**——第 1、3 条的 `A|B` 缺 `-E`（BRE 下竖线是字面量、恒 0 命中，属「空洞 0」），第 2 条 `find` 的括号未转义（被 shell 吃掉）。本节已改写成可原样复算的形态；W4 审计方在**未打补丁的原始树**上用上述正确写法重跑，五项命中数逐条仍为 **0** ⇒ **清点结论不变**。


`Makefile.am` / `src/Makefile.am` 只定义 `SUBDIRS`、`bin_PROGRAMS`、`man_MANS`、
`clean-local`，无 `TESTS`、无 `check_PROGRAMS`、无 `installcheck`。
z32 窗在同机同源码树独立重跑上述五条判据，命中数逐条仍为 **0**
（日志 `~/tmp/uc2/z32-qperf/43_static_inventory_recheck.log`）。
**结论：上游 0.4.11 无任何自动化测试（静态 0），此结论成立。**

但"没有测试框架"不等于"没有可跑的东西"：qperf 的功能单元就是它注册的**基准测试**，
清点口径必须以注册表为准。z32 窗补做这一步（原申报漏了，见下）：

```
grep -c "^    test(" src/qperf.c                          -> 36
12 无条件 + 21 在 #ifdef RDMA 内 + 3 在 #ifdef HAS_XRC 内   -> 36
分族：rc_ 10  uc_ 6  ud_ 3  ver_rc_ 2  xrc_ 3   = 24（RDMA 族）
      tcp_ 2  udp_ 2  sctp_ 2  sdp_ 2  rds_ 2   = 10（socket 族）
      conf + quit                                =  2（杂项）
```

`src/help.txt` 的 `Tests +RDMA` 段与这 36 条逐字对应；`Tests -RDMA` 段只有 12 条，
与本二进制 `qperf --help tests` 的实际输出完全一致。

> **更正（z32 窗实跑复核）**：本节原申报"全量登记 **20** 个传输测试、RDMA 族 **10** 个、
> 共 **22** 项"，把 RDMA 族只数成 `rc_*`，漏了 `uc_*`/`ud_*`/`ver_rc_*`/`xrc_*` 四族
> 共 14 项 ⇒ 正确值是 **34 个传输测试 + 2 个杂项 = 36 项**，RDMA 族 **24** 项。
> 分母相应从 16 项未执行更正为 **24** 项未执行（另 6 项 `rds_/sctp_/sdp_`
> 已由"未验证"变成"真跑过、被内核能力拒绝"）。

申报口径：静态上游自动化测试 **0** 项 + 上游注册基准测试 **36** 项（本产物内 **12** 项）
+ 本次消费者实测 **31** 条断言（N 取真机 `run_tests.sh` 打印的 `RESULT total=` 实测值，
逐条见「测试数字五维账本」与 `reports/test-report.md`）。

## 验证结果

### 门禁判决（鸿蒙 PC B 机真机，2026-09-25 00:0x–01:4x 首轮 + 02:2x z32c 整改窗重跑；逐条原文按三层取证目录：测试层首轮 `~/tmp/uc2/z26-qperf/`、门禁首轮重跑 `~/tmp/uc2/z32b-qperf/`、整改轮 `~/tmp/uc2/z32c-qperf/`；下表「日志」列的目录名一律相对 `~/tmp/uc2/`，并逐行标明该件属于哪一轮的哪个目录）

| 门禁 | 命令 | 判决 | 日志 |
|---|---|---|---|
| W0 依赖预检 | `bash ci/scripts/preflight_check.sh qperf/0.4.11` | `[OK] 所有依赖均已发布…`，`[OK] 已发布: automake/1.18`、`[OK] 版本号未被占用`，**rc=0** | `z26-qperf/step1_preflight.log`（测试层首轮）＋ `z32b-qperf/preflight.out`（门禁首轮重跑） |
| 配方检索 | `python3 scripts/ohc-run.py recipe-search qperf` | `⚠️ 无相似配方（语料 6173 条）——首稿走 conan-init 模板`，**rc=0**（咨询步骤） | `z26-qperf/step2_recipesearch.log`（测试层首轮；咨询步骤，未随门禁重跑） |
| G0–G4 / L2/L4/L5 | `python3 scripts/ohc-run.py conan-verify qperf 0.4.11` | **`Verdict: PASS`**、**VERIFY_RC=0**。分项照录 `reports/conan-verify-report.md` 原文：G0 ✅ PASS（并附 E490 `⚠️ 已知风险…未在配方中处理` 告警）、G1 ✅ PASS、G2 ✅ PASS（`conan create 成功`）、G3 ✅ PASS；**G4 标题为 ✅ PASS 但正文只有 `⚠️ 无法找到程序包 ID` 一条告警**；**L2 / L4 / L5 标题为 ✅ PASS 而正文是 `⏭️ 跳过（无 cache 路径）`**⇒ G4 与 L2·L4·L5 **均不构成可执行性证据**，本不在 verify 行挂 ✅；产物真跑通只由 W3 的 31 条消费者断言（驱动安装后的 `bin/qperf`）承担 | 本行 `VERIFY_RC=0` 取整改轮 `z32c-qperf/60_verify.log`；分项原文取本归档目录下`reports/conan-verify-report.md`、`reports/conan-create.log`（两份均为 02:28 整改轮回写）；另两轮同项日志：测试层首轮 `z26-qperf/step3_verify.log`、门禁首轮 `z32b-qperf/verify.out` |
| W2+R36+**W3** | `python3 scripts/ohc-run.py finish qperf 0.4.11 built` | `✅ W3 本地 CI 模拟通过`（内部真跑 `ci/conan/setup.sh` + `ci/conan/build_and_test.sh`）、`✅ 仅含配方变更 (14 文件)，无框架文件`、`✅ graph validate 通过`；`EXIT_REASON: finish_success` / `EXIT_CODE: 0` / `STEP_FAILED: Step6` —— 同块三条读数一并照录（`z32c-qperf/61_finish.log:119-121`）；驱动记录的外层 `FINISH_RC=1`（同件 `:133`，由 `z32c-qperf/run_stage.sh:23` 显式打印落盘）—— **与 r1 基线同形**（`z32b-qperf/go_finish.out:7` 亦 `FINISH_RC=1` 且该轮 W3 判通过）⇒ 本包不拿外层 rc 当门禁通过判据 | 本行判决取整改轮 `z32c-qperf/61_finish.log`（其 `:98` 即上面那条 14 文件）＋本归档目录下 `reports/w3-local-ci.log`（02:29 整改轮回写）；门禁首轮同判在 `z32b-qperf/finish.out`（`:98` 同为 14 文件）；测试层首轮 `z26-qperf/step4_finish.log:105` 记的是 12 文件（旧基线计数，勿引） |
| W5 知识图谱 | `python3 scripts/ohc-run.py graph validate` | `✅ All checks passed (169 warnings)`，`.kv/.md/index` 三者 540 对齐；加本包草稿后告警数不变（169→169），即新草稿零新增问题 | `z32c-qperf/62_graph.log`（整改轮）＋ `z26-qperf/step5_graph.log`（测试层首轮）——两处实测均含 `All checks passed (169 warnings)` |
| B 草稿预审 | `python3 scripts/ohc-run.py draft-review DRAFT-qperf-0.4.11-posix-sockatmark-absent-use-siocatmark-ioctl` | `质量预检: signature=✅ root_cause=✅ rec=✅`；TOP3 相似度 `E093 0.43 / E245 0.29 / E085 0.23`（均 < 0.5）；`📌 预审建议: review-similar → E093`（灰区，纳入与否归人工审核） | `z26-qperf/step6_draftreview.log`（测试层首轮；知识草稿预审项，未随门禁重跑） |

`**编译结束** / **最终状态** 两行由 `finish` 真实回写在文末，未手工凑写。

**W3 结果文件**（`archives/q/qperf/0.4.11/.ci-result.json`，工具生成、含日志哈希，禁止手改）：
`exit_code: 0`、`step: W3_local_ci`、`software: qperf`、`version: 0.4.11`、
`timestamp: 2026-09-25T02:29:17.158383`、`integrity_hash: c7076306bfe7517a`、
`log_sha256: ff4a8e6388fbc083a90501cde12b45f29430ce674c8883138550ccc373fbb937`。

### z32 窗复核（2026-09-25 01:14–01:32，同机同制品）

上游测试面实跑与探针取证见「传输路径实测矩阵」与「测试数字五维账本」，
逐条日志在 `~/tmp/uc2/z32-qperf/`（清单见 `reports/test-report.md` 第九节）。
本窗另用真 conan 流程复验了改动后的 `test_package`：

```
conan test archives/q/qperf/0.4.11/test_package qperf/0.4.11 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
  -> CONAN_TEST_RC=0
  -> RESULT pass=31 fail=0 total=31
  -> qperf/0.4.11 (test package): qperf consumer test: 31/31 assertions pass
```

被测制品 `bin/qperf` 的 `sha256 = 70d7a7d4e0ebba431ae3004c1a6914d7abd809e2faa006d5b958f30e371b3fa2`
（即 `finish(built)` 于 00:14 产出的那一个），日志 `46_conan_test.log`。
⇒ 新的 31 断言层在 `VirtualRunEnv` 下同样全绿，不是只在手写 shell 里跑通。

### 测试数字五维账本

z32 窗实跑复核后重列（改前→改后见每行括注；账平校验
`通过 6 + 跳过 30 = 静态总数 36`，`可执行 12 = 通过 6 + 已执行被拒 6`）：

| 维度 | 数 | 口径与证据 |
|---|---|---|
| 上游自动化测试（静态总数） | **0** | `TESTS`/`check_PROGRAMS`/`ctest`/`tests/` 全树 0 命中；z32 窗独立重跑逐条仍 0。清点命令见上节 R51，日志 `43_static_inventory_recheck.log` |
| 上游注册基准测试（分母，不缩） | **36**（改前 22） | `src/qperf.c` 的 `TEST Tests[]` 注册表：12 无条件 + 21 在 `#ifdef RDMA` + 3 在 `#ifdef HAS_XRC`；RDMA 族 **24**（改前误记 10）= `rc_*` 10 + `uc_*` 6 + `ud_*` 3 + `ver_rc_*` 2 + `xrc_*` 3 |
| 本构建产物可执行 | **12**（不变，已复核） | `qperf --help tests` 实测 10 socket + 2 misc，与源码 `#ifdef RDMA` 之外的 12 条逐字对应；24 项 RDMA/XRC **未编进产物**（`readelf -d` 仅 `libc.so`，`rc_*` 命中 0） |
| 本适配新增消费者测试 | **12 场景 / 31 断言**（改前 9 / 25） | `test_package/MANIFEST.yml` `test_scenario_count: 12`、`assertion_count: 31`，分项 7+1+3+14+**6**=31，与 `RESULT` 行、`conanfile.py` 下限三处同源；新增的 6 条是本构建注册的 `sctp_/sdp_/rds_` 断言，z32c 窗已把它们**收紧为可证伪**：每条为**该传输独占一个服务端**（自己的监听端口、自己的日志、按自己的 PID 回收），只在命中**内核 socket 层的真实拒绝语句**（服务端日志里的 `unable to make SCTP socket` / `unable to make SDP socket`，或任一端的 `socket failed: Address family not supported`）、或真的出数时才记 ok；下游假象 `getaddrinfo failed: Unrecognized service` **不再作为判据** |
| **实测通过数** | **31 / 31 断言；上游测试实跑通过 6 / 12 已执行** | 真机 `RESULT pass=31 fail=0 total=31`（`HARNESS_RC=0`，`[PASS]` 计数 31、`[FAIL]` 计数 0）；通过的 6 项 = `conf`、`quit`、`tcp_bw`、`tcp_lat`、`udp_bw`、`udp_lat`，数值与命令逐条见「传输路径实测矩阵」及 `~/tmp/uc2/z32-qperf/20_supported_run.log`、`42_run_tests_installed.log` |
| 跳过数 | **30**（改前 0 + 未执行 16，口径合并重列） | 分两类逐条给原因：① **24** 项 RDMA/XRC 族未编进产物（三层缺失：`open()` 探针 errno=2 / ELF 无 libibverbs / `/proc/net/protocols` 的 23 条注册行**含** IPv4 的 `TCP`/`UDP`/`PING`/`RAW`/`NETLINK` 而无 `SCTP`/`RDS`/RDMA 族条目，后者与 `socket()` 的 errno=93/97 互印、**只作辅证**，判据以 errno 为准，见「传输路径实测矩阵」与 `10_transport_probe.log`、`15_env_facts.log`）；② **6** 项 `rds_bw rds_lat sctp_bw sctp_lat sdp_bw sdp_lat` **已真跑执行**、被内核协议能力拒绝（`socket()` errno=93 / 97，探针与 qperf 两侧同判，见 `30_unsupported_run.log`、`32_qperf_path_probe.log`）。断言层本身**零静默跳过**：原 `ldd` 分支已改 `readelf -d`，探测不到工具即判 FAIL |
| 失败数 | **0**（不变） | 没有任何"本可运行的用例"跑出错误结果或崩溃；`test_package/conanfile.py` 要求 `failed == 0` 且 `passed >= 31 && total == 31`，断言层被削弱即不过 |
| **未执行（不计入通过）** | **24**（改前 16） | 仅 RDMA/IB/RoCE 族 24 项（产物不含）。`rds_/sctp_/sdp_` 6 项已从"未验证"升格为"已执行、被内核能力拒绝"，改记在跳过类的第 ② 档，**仍不计通过** |

申报口径：`rule4` 要求正文数字 ≤ 实测——本包申报"**消费者断言 31/31 通过；
本构建注册的 12 个上游测试 100% 真跑（6 项出数通过 + 6 项被内核能力拒绝并给出 errno）；
24 个 RDMA/XRC 测试因产物未编入未执行**"，
**不**把 30 个未通过项计入通过；合计 36 不小于上游静态合计 36。

**本轮改动对既有门禁判决的连带影响（z32c 整改窗已闭环）**：`test_package/` 是配方的一部分，
改它 ⇒ `conan create` 的 recipe revision 变化 ⇒ 旧判决不再绑定当前 HEAD 的配方，
故本轮按 `conan-verify` → `finish qperf 0.4.11 built` 顺序**真重跑**了门禁：
`conan-verify` 仍 `Verdict: PASS`，`finish` 内部实跑 W3 本地 CI 与 `test_package`，
`.ci-result.json` 当前判决 = `exit_code: 0`、`timestamp: 2026-09-25T02:29:17.158383`、`integrity_hash: c7076306bfe7517a`、
`log_sha256: ff4a8e6388fbc083a90501cde12b45f29430ce674c8883138550ccc373fbb937`（W3 日志 `reports/w3-local-ci.log` 内 `RESULT pass=31 fail=0 total=31`，`[PASS]` 计数 31、`[FAIL]` 计数 0）。
⇒ **本地证据已齐，剩下的只有远端 CI**：`submit`/`/rebuild` 与让渡归主代理，本窗不碰流水线命令。

## B 判定

**`B判定=create`**，新增草稿（同 stem 成对，已落本 PR）：
`knowledge/drafts/DRAFT-qperf-0.4.11-posix-sockatmark-absent-use-siocatmark-ioctl.{kv,md}`

一句话机制：**OHOS 的 C 库连 ISO POSIX 标准函数 `sockatmark(3)` 都不声明、也不导出符号，需按特性（`#ifdef SIOCATMARK`）改发该函数规范自身定义的底层 `ioctl(fd, SIOCATMARK, &val)`**。

四范围查重：`sockatmark|SIOCATMARK|out-of-band|urgent` 在 `knowledge/graph/*.kv` + `index.tsv` **0 命中**、在 `knowledge/drafts/*.kv`（1469 条，实测 `ls knowledge/drafts/*.kv | wc -l`）**0 命中**、`grep -ln "ioctl\|SIOC" knowledge/graph/*.kv` **0 命中**、`recipe-search qperf` **无相似配方**（语料 6173 条）。

判 `create` 的四条件落点（逐条比对，详见草稿 `.md` 的「知识库查重与新增价值」）：

- **E534**（任务预设的对照条目，口径为"musl 缺 **GNU/BSD** 扩展函数需 weak 兼容层"）：
  ①**症状不一致**——其 `error_signature`/`match_keywords`/`affected_scope` 只列举
    `gethostid`/`strverscmp`/`sigisemptyset`/`getusershell`，`root_cause` 写死"musl 有意不实现
    **非 POSIX** 扩展"；`sockatmark` 是 **POSIX 标准函数**，属条目解释覆盖不到的新偏差
    （四条件第 1 条自身口径：出现已知条目外的新偏差即升 B）。②**解法未被覆盖**——E534 是
    集中式 `__attribute__((weak))` 兼容层，本包是调用点特性门控 ioctl，按第 2 条原文
    "既有条目没写的另一条解法 ⇒ 不算 hit，按 create 报"。
- **E245**（`draft-review` 检出的真正最近邻：OHOS libc 未导出 `vhangup`，声明缺失+符号缺失
  但内核 syscall 存在，方案 `ohos-syscall-shim`）：必须正面区分——E245 下沉到**裸 syscall**
  （查 `__NR_xxx` 用 `syscall()` 直调）且要求**平台宏**（"非 OHOS 平台不启用 shim"）；
  本条走**同层已导出的 `ioctl()`**、零平台宏（过 R8/PF5），等价性由 POSIX 正文与 musl 实现背书。
  两者同族、却走**两条不同解法路线**，并沉淀选路判据：先看有没有已导出的同层接口，没有才下沉 syscall。
- `draft-review` 相似度 TOP3 `E093 0.43 / E245 0.29 / E085 0.23` 全部 < 0.5；
  `E093` 的高分由类目重合（cat=0.75）与"undeclared function"表象（sig=0.57）推高，
  关键词重合仅 `kw=0.05`，且 `getpass` 是 POSIX 已废弃的 GNU 扩展，与本条不同根因不同解法。

**本包另有一条同量级新机制未随本 PR 提交**（`一 PR 一知识` 口径，多出的不塞本 PR）：
**HongMeng 内核完全不实现 signal-ownership 这一族 fcntl**（`F_SETOWN`/`F_GETOWN`/`F_SETOWN_EX`/
`F_SETSIG` 在 TCP/UDP 套接字上一律 EINVAL、普通文件 ENOTSUP，而 `F_SETFL(O_ASYNC)` 与 `FIONBIO`
正常），修法是"对可证无消费者的能力，只在 errno 表示未实现时不中止"。证据：补丁 0002 +
本节探针实测表 + grep 出的"全树无 SIGIO/O_ASYNC/F_SETFL/F_SETSIG 用法"。
该机制对所有用 SIGIO 异步套接字的包都成立，建议进通用草稿池由后续撞上的包配发。

- **适配路径**：路径 A（直接适配）+ 2 条 portability 源码补丁（无框架改动）；路径 B 判定 = create
- **使用知识库**：E490（autotools 生成物与 helper 执行位在 configure 前需恢复，bootstrap 时命中）；知识图谱对 sockatmark、SIOCATMARK、out-of-band、urgent 四关键词检索 0 命中；recipe-search qperf 无相似配方（语料 6173 条）
- **知识库扩展**：新建草稿 knowledge/drafts/DRAFT-qperf-0.4.11-posix-sockatmark-absent-use-siocatmark-ioctl.kv 与同名 .md——OHOS 的 C 库连 ISO POSIX 标准函数 sockatmark(3) 都不声明也不导出，需按特性改发该函数规范自身定义的底层 ioctl(fd, SIOCATMARK, &val)
- **关联 Issue**：#3352 已创建 —— https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3352


## 注意事项

- 本包是命令行工具，故软件级目录必须声明 `commands.json`（R38 / CI L0k）。
- `qperf` 默认无参数即进入 server 模式且长驻；任何脚本化调用必须显式带
  `-t <秒>` 并在结束时用 `quit` 测试或服务端进程回收，否则挂住。
- OHOS 上首次 exec 新生成 ELF 需要自签，`package()` 已内建（见编译步骤 6）。
---

**编译结束**: 2026-09-25 02:28
**最终状态**: built
**CIW-B2 整改记录（2026-09-27）**: Septest rule1 判「复选框解析不到（body 格式特殊）」，病根=复选框在 ### 小节内、解析器只认 ## 节直属复选框（CIW-F2 ①类正文格式细则口径）；已把「上游测试用例修改说明」「补全测试用例说明」两节改为「- **问题** + 复选框」格式并 PATCH 正文。本提交仅刷 HEAD 绑新判决（同 HEAD 重提复用旧 FAIL 教训 12580/12558/12541），零功能性改动。
