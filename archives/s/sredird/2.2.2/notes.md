# sredird 2.2.2 适配笔记

## 编译环境
- 构建系统: makefile（单文件 C + 两行裸 Makefile：`CC=gcc`、`CFLAGS=-O3 -pipe -fomit-frame-pointer`，
  一条 `$(CC) $(CFLAGS) $(WFLAGS) -o sredird sredird.c` 规则编译链接一步完成；无 configure、无 install 目标）
- 编译日期: 2026-09-29
- 编译器: OHOS SDK clang 15.0.4（`aarch64-unknown-linux-ohos`，经 `/data/service/hnp/bin/clang`），sysroot 为 OHOS musl
- 构建机: x86_64 runner 交叉编译；目标 aarch64-linux-ohos（profile `ci/conan/profiles/ohos-aarch64`，build_type=Release）
- 状态: built（conan-verify G0-G4 通过）

## 源码来源

- 任务给出的上游仓库 `salsa.debian.org/debian/sredird` 是 Debian 团队维护仓库：`upstream/2.2.2` 分支/标签存放纯上游源码，
  `debian/2.2.2-2` 标签在其上加了 `debian/` 目录（4 个补丁）。`debian/copyright` 的 `Source:` 与 `debian/watch` 指向 ibiblio
  Linux 归档 `pub/linux/system/serial/sredird-2.2.2.tar.gz`（作者 InfoTecna 旧主页已失效，任何路径都回 200 的“页面不存在”HTML）。
  实测 salsa `upstream/2.2.2` 归档的 6 个文件与 ibiblio 发布包**逐文件 sha256 完全相同**；因此构建取上游发布包
  （不用 salsa 按需生成的 git 归档，也不用 deb.debian.org 的 Debian 重打包，避开 PF7）。
- ibiblio 服务器对 `.tar.gz` 回 `Content-Encoding: x-gzip`：Conan 的 requests 透明解码后得到裸 tar，
  sha256 变成 `ad02fdc0…`（W3 首次失败于 `sha256 hash failed`）；curl 拿到的发布字节是 `640c47dc…`。
  仓库已有同类先例（lbrate 1.1，草稿 `E562-draft-BF48` 等），本次不另立条目；
  改用 GWDG 学术镜像（`ftp.gwdg.de/pub/linux/metalab/...`，ibiblio/metalab 的镜像）取同一文件：
  无 Content-Encoding，字节与 ibiblio 发布文件相同（两处独立下载 sha256 一致）。
- 归档 sha256 `640c47dcd84b3b90640165a38eb336a675fdab06c14c09cae2f4a604cae560d3`（25495 字节），
  内含 6 个文件：`COPYING` / `Makefile` / `README` / `sredird-2.2.2.lsm` / `sredird.8` / `sredird.c`。
- 语言预检：源码 1 个 C 文件（2232 行）+ Makefile，纯 C 项目，无需 `--lang` 声明（默认口径 cpp 族放行）。

## 编译步骤

1. 手工打通：`init-build` 后先断开 `.work`/`.orig` 硬链接（E543：`cp --remove-destination`），
   `aarch64-unknown-linux-ohos-clang -O2 sredird.c` 首次失败于 `#include <termio.h>`（问题 1）。
2. 删除该 include 后编译通过；对照实测协议往返时发现应答帧畸形（问题 2），改 `uint32_t`。
   `refresh-patch --auto` 生成 `patches/0001-sredird.c.patch`（+3/-3，`patch --dry-run -p1` 干净，无平台宏）。
3. 配方 `build()`：`apply_conandata_patches` 后由 `AutotoolsToolchain(self).vars()` 取 `CC`/`CPPFLAGS`/`CFLAGS`/`LDFLAGS`（R33），
   以 make 命令行变量传入：`CC` 覆盖写死的 gcc；`CFLAGS` = 上游默认 `-O3 -pipe -fomit-frame-pointer` + 工具链
   CPPFLAGS/CFLAGS/LDFLAGS（Makefile 规则没有独立的链接行，链接标志只能走 CFLAGS）；只构建 `sredird` 目标。
4. `package()`：上游无 install 目标，`sredird` → `bin/`，`sredird.8` → `share/man/man8/`，`COPYING` → `licenses/`，
   `README` → `share/doc/sredird/`；`commands.json`（软件级）声明 CLI（R38）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sredird.c:113:10: fatal error: 'termio.h' file not found` | `<termio.h>` 是 glibc 遗留头，musl/OHOS sysroot 不提供；源码只用 `<termios.h>` 的 `struct termios` / `tcgetattr` / `tcsetattr` / `cfmakeraw`，从未用到 `struct termio` 或 `TCGETA`/`TCSETA`（`grep` 实测仅 include 行一处） | 补丁删除该未用 include；无平台宏。与 Debian 补丁 `debian/patches/0004-rm-termio-h.patch`（2025-12，Closes #1115213，`Forwarded: not-needed`）改动完全相同。同类知识已有草稿 `DRAFT-E567-termio-ioctl-macro-capability-guard`（musl 无 termio.h / TCGETA），不另立条目 |
| 2 | 编译零告警，但 RFC 2217 `SET-BAUDRATE` 应答帧畸形：请求 `IAC SB 44 1 00 01 C2 00 IAC SE`，应答 `IAC SB 44 101 00 01 C2 00 00 00 00 00 IAC SE`（值后多 4 个 `00`） | 32 位线缆字段被声明为 `unsigned long`：`SendBaudRate` 里 `unsigned long NBR = htonl(BR)` 后按 `sizeof(NBR)` 逐字节序列化，LP64 下循环 8 次；`ntohl(*(unsigned long *)&Command[4])` 多读 4 字节。ILP32 时代恰为 4 字节。x86_64 同样复现，`-Wall -W -Wshadow -pedantic` 全部静默 | 补丁新增 `#include <stdint.h>`，`NBR` 与解析处改 `uint32_t`；test_package T5 逐字节比对应答帧并回读 pty 的 `cfgetospeed()`，补丁前失败、补丁后通过（qemu 实测，见下）。新增知识草稿 `E6511-draft-6CBB`（draft-review verdict=create，最相近 E419 分数 0.21） |
| 3 | conan-verify G2：`sha256 hash failed for 'sredird-2.2.2.tar.gz'`（Provided 640c47dc…, Computed ad02fdc0…） | ibiblio 对 `.tar.gz` 回 `Content-Encoding: x-gzip`，requests 透明解码落裸 tar（见“源码来源”） | 改用 GWDG 镜像，字节相同、无内容编码，sha256 不变 |
| 4 | x86 runner 无法运行交付的动态产物 | 构建机没有 OHOS 的 `/lib/ld-musl-aarch64.so.1`（E544） | 功能验证改用同源、同标志的 `.c` **静态重链**副本经 qemu-aarch64 实跑；test_package 在此类主机上如实 SKIPPED，由 aarch64 CI worker 执行 |
| 5 | `init-build` 把构建系统判成 `autotools`，`conan-init` 生成 autotools 配方与 CMake 空壳 test_package；manifest 里 `{BUILD_SYSTEM}` 占位符未渲染 | 工具侧判定问题（已写入 SKILL_FEEDBACK） | 按实际的裸 Makefile 手写配方与 manifest，test_package 改为 C 消费者用例 |

## 源码修改

`patches/0001-sredird.c.patch`（`refresh-patch --auto` 生成，+3/-3，`patch --dry-run -p1` 干净；无任何平台宏，可上游化）：

1. 删除 `#include <termio.h>`，新增 `#include <stdint.h>`；
2. `SendBaudRate()`：`unsigned long int NBR` → `uint32_t NBR`；
3. `HandleCPCCommand()` 的 `TNCAS_SET_BAUDRATE`：`ntohl(*((unsigned long int *) &Command[4]))` → `ntohl(*((uint32_t *) &Command[4]))`。

## 依赖版本

- 无 Conan 依赖（仅 libc：termios / socket / syslog）；W0 核验：配方 `requirements()` 为空，无需探测制品仓。
- 工具链：OHOS SDK clang 15.0.4、ld.lld、musl sysroot。

## 上游测试清点（R51）

- 清点：源码归档共 6 个文件、无子目录；无 `tests/` 目录（0 个）、无测试脚本、无 ctest/pytest 注册（0 个）；
  Makefile 目标只有 `sredird` / `clean`，`make -n check`、`make -n test`、`make -n tests` 均报 `No rule to make target`；
  Debian 打包（`debian/2.2.2-2`）无 `debian/tests`。
  **上游测试用例数 N = 0**，可运行数 N′ = 0，通过率不适用。
- 补全（鸿蒙特有测试，**1 个用例、含 7 项检查**）：`test_package/rfc2217_client.c` 是完整消费者流程——
  Conan 以 OHOS profile 经 CMake 用 OHOS 工具链编译该 C 客户端，`test()` 把包内 `bin/sredird` 复制到构建目录（OHOS 上先自签名），
  用 socketpair 作“网络连接”、`posix_openpt` 伪终端作“串口”启动它，逐项检查：
  T1 初始 Telnet 协商 18 字节逐字节一致；T2 HDB 锁文件内容 = sredird 的 pid；T3 网络→串口数据送达、`IAC IAC`→`0xFF`；
  T4 串口→网络数据送达、`0xFF`→`IAC IAC`；T5 `SET-BAUDRATE 115200` 应答逐字节一致且 pty 从端 `cfgetospeed()` 为 `B115200`；
  T6 `SET-DATASIZE`/`SET-STOPSIZE`/`SET-CONTROL` 应答并经 termios 生效（CS8、`CSTOPB` 置位再清除、`IXON|IXOFF` 置位再清除）；
  T7 关闭连接后 sredird 退出码 0 且删除锁文件。（pty 恒为 8 位无校验，故数据位 7 / 校验请求无法在 pty 上观测，未纳入。）
  它异步过滤 sredird 主动发出的 `NOTIFY-MODEMSTATE` 报告，`IAC IAC` 数据整体透传。整个客户端不依赖 PATH，二进制路径只来自被测包。

## 验证结果

```bash
# conan-verify（G0-G4 PASS）/ conan create，x86_64 runner：
#   Testing the package: ... WARN: SKIPPED: rfc2217_client was cross-built for aarch64 OHOS but this host cannot
#   execute it (needs aarch64 and /lib/ld-musl-aarch64.so.1); the functional check runs on the aarch64 CI worker

# 交付产物属性（llvm-readelf）：ELF64 aarch64 PIE，PT_INTERP=/lib/ld-musl-aarch64.so.1，NEEDED libc.so，
#   GNU_STACK RW（NX）、GNU_RELRO + BIND_NOW（full RELRO）

# 功能验证（本地实跑）：conan 构建目录中已打补丁的 sredird.c（同源）按 conan create 相同标志
#   clang -O3 -pipe -fomit-frame-pointer -O3 -DNDEBUG -Wall -W -Wshadow -Wpointer-arith -Wwrite-strings -pedantic -static
# 静态重链；消费者 rfc2217_client.c 同工具链 -static 编译；qemu-aarch64 实跑：
$ qemu-aarch64 ./client.static ./sredird.static
PASS T1: initial Telnet negotiation (18 bytes) byte-exact
PASS T2: HDB lock file holds the sredird pid
PASS T3: network -> serial data delivered, IAC IAC unescaped to 0xFF
PASS T4: serial -> network data delivered, 0xFF escaped to IAC IAC
PASS T5: SET-BAUDRATE 115200 acknowledged and applied via termios
PASS T6: SET-DATASIZE/STOPSIZE/CONTROL acknowledged and applied via termios
PASS T7: sredird exited with status 0 and removed the lock file
ALL PASSED (7 checks)
exit=0

# 消融对照（同法静态重链，qemu-aarch64 实跑）：
#   仅删 termio.h、未改 unsigned long -> T1-T4 通过，T5 失败（应答帧多 4 个 00），exit=1
#   完整补丁                          -> T1-T7 全部通过
```

**说明**：x86 runner 上交付的动态产物本身未实跑（缺 OHOS loader），上面的功能结果来自同源同标志的静态重链副本，
**不等于交付产物已实跑**；交付产物的功能层（用例 rfc2217_client）由 aarch64 CI worker 上 `conan create` 的 test_package 执行，
本地未实跑、由 CI 执行——CI 出结果后须在日志确认该用例确实运行并通过（而非 SKIPPED）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/sredird` | ELF64 aarch64 PIE，动态链接 OHOS musl（`libc.so`） |
| `share/man/man8/sredird.8` | 上游 man 页（未压缩） |
| `share/doc/sredird/README` | 上游 README |
| `licenses/COPYING` | GPL-2.0 全文 |

## 注意事项

- sredird 设计为由 inetd 类超级服务器启动（连接即 stdin/stdout）；无参数（少于 4 个参数）打印版本与用法并退出 1，没有 `--version`。
- 上游 `main()` 的选项循环写作 `argv[argi][0] == '-' && argi < argc`（先解引用后判边界）、可选轮询间隔读 `argv[4]`
  （与 `-i` 同用时位置不对）——均为上游既有行为，与平台无关，未改动。Debian 的 `0002`（参数不足时段错误）/`0003`（hardening）
  同样不在本次适配范围；Debian 的 4 个补丁均未涉及 `unsigned long` 线缆字段（问题 2）。
- 真实串口设备（`/dev/ttyS*`、USB 串口）与 `/var/lock` 在 OHOS 设备上的可用性取决于设备与权限，未在真机验证；
  test_package 使用 pty 与当前目录下的锁文件，不依赖真实串口。
---

**编译结束**: 2026-09-29 13:11
**最终状态**: built
