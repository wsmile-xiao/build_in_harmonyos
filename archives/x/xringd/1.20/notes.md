# xringd 1.20 适配笔记

## 编译环境
- 构建系统: makefile（上游是 1996 年裸 Makefile，无 configure / 无 automake / 无 cmakelists）
- 编译日期: 2026-09-27
- 编译器: clang 15（profile `ci/conan/profiles/ohos-aarch64`，os=OHOS arch=armv8）
- 状态: built（本地 W3 通过）
- 目标性质: **调制解调器铃流守护进程**，不是 X11 程序（实测 `grep -cE "XOpenDisplay|XNextEvent|CursorShape"` 在 xringd.c/ringsm.c/uartcount.c 均为 0）

## 定源（一手）

- 线索链：tar 包内自带 `xringd-1.20.lsm` →
  `Primary-site: sunsite.unc.edu /pub/Linux/system/Network/daemons  23k xringd-1.20.tgz`；
  `Alternate-site: dolphin.doc.ic.ac.uk /pub/Linux/xringd`。作者 Angelo Haritsis <ah@doc.ic.ac.uk>，GPL。
- 端点实测读数：
  | 端点 | 读数 |
  |---|---|
  | `http(s)://dolphin.doc.ic.ac.uk/...` | curl (6) Could not resolve host（DNS 死） |
  | `https://www.doc.ic.ac.uk/~ah/`（作者主页） | HTTP 404 size=271（vm-wwwhomes 上个人目录已清） |
  | `https://www.ibiblio.org/pub/Linux/system/Network/daemons/xringd-1.20.tgz` | HTTP 404（大写 Linux 树无此件） |
  | `https://www.ibiblio.org/pub/linux/system/network/daemons/xringd-1.20.tgz` | **HTTP 200 size=31787，last-modified: Mon, 21 Jul 1997 22:27:32 GMT** |
  | 同目录 listing | HTTP 200；xringd 相关只有 `xringd-1.10.{lsm,tgz}`、`xringd-1.20.{lsm,tgz}`，无免 gzip 的 `.tar` 变体 |
  | `ftp://ftp.ibiblio.org/pub/linux/system/network/daemons/xringd-1.20.tgz` | 200、31787 B、哈希同下（**未采用**：CI 侧 21 端口出网未验证） |
- 采样与同值性：ibiblio 官方址连续 **3 次**下载，`bytes=31787`、
  `sha256=3ecfa6fa8b871b6d92168370fdfab1bf48a90ddbf10a738f384def3b07a1b77f` 三次一致；
  gzip magic `1f8b`（200 不是 HTML）；Debian 池 `xringd_1.20.orig.tar.gz` 实算**同值**
  ⇒ 证明是同一文件（仅用于交叉核验，池址不进配方）。
- tar 顶层是**不带版本号**的 `xringd/`（由 Makefile `dist` 目标 `tar ... xringd` 打成）
  ⇒ `strip_root=True`，不靠 `filename=` 凑版本目录。

## 编译步骤

配方不跑裸 `make`，也不碰 `dist:`（它会 mv/perl/tar 回写发布物）。上游默认目标实测就是 `xringd`
（裸 `make -n` 打出 `gcc -Wall -O2 -m486 -DVERSION=\"1.20\" ... -c -o ringsm.o/xringd.c` 再链接），
无 `what:`/猜平台类坑目标。构建命令（R6：安装目录与编译旋钮一律走 make 命令行变量覆盖，不改 Makefile）：

```sh
make -j1 CC=<profile 注入的 clang> CFLAGS='-Wall -O2 $(DEFS)' LDFLAGS= xringd
make -j1 CC=<同上>                  CFLAGS 同上  LDFLAGS= uartcount
```

- `-m486` 与链接期 `-s` 被覆盖掉；`$(DEFS)` 由 make 自身展开（实测展开正确），
  使 `VERSION/MODEM_FILE/CONF_FILE/INIT_TIMEOUT` 仍由上游单点定义，配方不重复字面量。
- 构建前在 `build()` 里显式删除上游随包带的两枚预编译件（见「源码修改」下一节）。
- 交叉产物实测：`ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped`；
  `xringd -h` 回显 `xringd version 1.20` ⇒ DEFS 真的传进去了。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 同一官方 URL，curl 下到的哈希与 conan 下到的哈希不同（3ecfa6fa vs d72967ed），`source()` 报 sha256 failed | 站点给**已经 gzip 过**的 `.tgz` 又声明 `content-encoding: x-gzip`（Apache AddEncoding 误配，`www.ibiblio.org`/`ibiblio.org`/`http` 三种写法实测都带）；conan 下载通道按声明透明解压，落地变 102400 B 纯 tar | `source()` 里 try `get()` / except 回退 `urllib.request`（urllib 不做 Content-Encoding 解码），回退后 `check_sha256` 校验官方原件哈希 + `unzip(strip_root=True)`。不换镜像、不改哈希凑数 |
| 2 | `clang-15: error: unknown argument: '-m486'`（交叉与本机两种调用均退出码 1） | 上游 CFLAGS 里 x86 专属架构旋钮 | make 命令行覆盖 `CFLAGS`，保留 `-Wall -O2 $(DEFS)`，不改 Makefile |
| 3 | 链接期 `-s` 产出 stripped 二进制 | OHOS 内核 MAC 会拒 exec 已 strip 产物（先例 abduco/0.6 用 STRIP=true 绕同一坑） | 命令行覆盖 `LDFLAGS=`（置空），产物保持 not stripped |
| 4 | `make install` 不可用 | 两行都是 `-install -o root -g bin ...`：行首 `-` 吞掉非 root 失败 ⇒ 静默空交付；且本设备实测没有 `install` 工具（`which install` 退出码 1） | `package()` 不跑 `make install`，按上游 BINDIR/MANDIR 语义显式装配并 chmod |
| 5 | `uartcount.c` 编译失败 `use of undeclared identifier 'O_RDONLY'/'O_NONBLOCK'/'O_NOCTTY'` | 1996 年 glibc 会经 `termios.h` 传递引入 `fcntl.h`，现代 libc 不再传递引入 | 打 1 行可移植性补丁 `patches/0001-uartcount-include-fcntl-h.patch`（`patch_type: portability`，已登记进 conandata.yml 的 `patches:`） |
| 6 | 上游包内含与 make 目标同名的预编译件 | `xringd-1.20.tgz` 里 `xringd`、`uartcount` 两枚文件实测是 `ELF executable, 32-bit LSB 386, dynamic (/lib/ld-linux.so.1), stripped`（LSM 自述 "Source and an aout bin are included"）；make 是否跳过真实编译取决于双方 1997 年 mtime 先后 | `build()` 内先 `os.remove` 这两枚陈旧目标件，保证产物必然是本次交叉编译的结果 |

## 源码修改

只有一个补丁，不改 Makefile、不改任何字面量：

- `patches/0001-uartcount-include-fcntl-h.patch`（`patch_type: portability`）
  在 `uartcount.c` 的 `#include <termios.h>` 后加一行 `#include <fcntl.h>`。
- 补丁新增行不含 `__OHOS__`（PF5）。
- round-trip 实测：干净副本 `patch -p1` 前后 `#include <fcntl.h>` 计数 `0 -> 1`；
  未打补丁编译退出码 1（首错 `use of undeclared identifier 'O_RDONLY'`），打上后退出码 0。
- 注：上一版补丁生成时误把 `--- / +++ ` 头整行删掉，导致 `patch` 空转（rc=0 却零改动），
  是 round-trip 的计数校验把它抓出来的；已改为只截时间戳、保留 `a/ b/` 标签。

## 依赖版本

**零第三方依赖（R36 一手证明）**：两枚产物 `readelf -d` 的 `NEEDED` 只有

```
xringd    NEEDED: [libc.so]
uartcount NEEDED: [libc.so]
```

源码侧只 include libc 与 Linux uapi 头（`termios.h`/`sys/ioctl.h`/`syslog.h`/`getopt.h` +
`linux/serial.h`/`linux/version.h`）。实测 OHOS sysroot 里 `linux/serial.h`、`linux/version.h`
**均存在**：`LINUX_VERSION_CODE=330240`（≥ 上游 `#error` 门限 1.3.48=66352）、
`sizeof(struct serial_icounter_struct)=80`、`TIOCGICOUNT=0x545d`、`TIOCMIWAIT=0x545c`
⇒ 编译面无需 stub，也没有触发语言例外。

## 测试口径

- **上游测试：0 条**。一手清点依据：`Makefile` 目标只有
  `xringd / install / dist / uartcount / clean`（`grep -nE "^(check|test.*):"` 空），
  包内也无任何 test/check 文件 ⇒ 不写"上游测试全通过"。
- **消费者测试：33 条断言，全部真执行 `bin/xringd` / `bin/uartcount`**，
  守护/可能阻塞的调用一律套 `timeout=20s`，**超时按 FAIL 记账**（不跳过当通过）。
  汇总行：`SUMMARY xringd consumer: total=33 passed=33 failed=0`。
- 断言构成：交付物落位 6（含可执行位）、产物架构校验 4（ELF magic + `e_machine=183`）、
  `-h`/未知选项 5、配置解析真跑 9（自建合法件、上游样例件、多选项组合、非法件报 `line 2`、
  缺件报 `cannot open config file`）、运行面真实失败形态 9。
- 配置校验为什么能真跑通：`-n` 置 `syntax_only`，`main()` 在 `modem_open()` **之前** 就
  `exit(0)` ⇒ 这是真正执行了 `ringsm_parse()` 状态机的功能通过，不是空转。

## 运行面能力缺失的申报口径

xringd 的本职是守串口 Ring Indicator 线。本机 `/dev` 面实测：
`/dev/modem` **不存在**、`/dev/ttyS0`、`/dev/ttyS1`、`/dev/ttyUSB0` 均**不存在**
（`/dev/tty`、`/dev/null` 存在）。实跑读数：

```
xringd -c <合法配置>            → "xringd: error opening modem device" + "No such file or directory"  rc=1
xringd -c <合法配置> -m /dev/ttyS0 → 同上 rc=1
uartcount                        → "cannot open modem device: No such file or directory" rc=1
uartcount /dev/null              → rc=1 且无 "Count:" 输出（非串口节点上 TIOCGICOUNT 被拒）
```

⇒ 结论口径：**编译面与静态面完整通过；守护/铃流检测的运行面因本平台 `/dev` 无串口节点而不可达，
属平台能力缺失，不是适配缺陷。** 本报告不宣称"铃流检测功能可用"，只申报
"编译 + 静态 + 真实失败形态"三项证据齐；`-c ... -n` 的配置解析路径是真实通过项。

## 发现与知识

- ✅ 官方站把已 gzip 的 `.tgz` 又声明 `content-encoding: x-gzip` ⇒ 同一 URL 有两种字节形态（31787 B gzip `3ecfa6fa…1b77f` / 102400 B 纯 tar `d72967ed…370e`，实测 `gzip -dc` 原件逐字复算相同）；conan 下载通道会剥这一层，用 urllib 原始字节回退即可保住官方哈希，既不换镜像也不改哈希凑数（同根因既有条目：`knowledge/drafts/DRAFT-conan-downloader-xgzip-content-encoding`，本包是其第二症状面——那一条是解压后尺寸小于声明值报"传输中断"，本包是尺寸大于声明值故校验放行、改由 sha256 报红）。
- ✅ 1996 年老 tarball 会把预编译产物与源码同包发布：`file` 实测包内 `xringd`/`uartcount` 是 `ELF executable, 32-bit LSB 386, /lib/ld-linux.so.1, stripped`，且文件名正好等于 make 目标名 ⇒ 会不会被判定"目标已最新"取决于双方 1997 年 mtime 先后，属不确定行为，构建前必须显式清除，否则可能把外来架构二进制当交付物打包。
- ✅ 上游 `install:` 目标写成 `-install -o root -g bin ...`：行首 `-` 吞掉非 root 失败，形成"安装目标执行成功、实际什么都没装"的静默空交付；本设备还实测没有 `install` 工具（`which install` 退出码 1）⇒ 小型 makefile 包的 `package()` 应显式装配，不依赖 `make install`。
- ✅ 上游 `CFLAGS` 里的架构专属旋钮 `-m486` 在本平台是硬失败（`clang-15: error: unknown argument: '-m486'`，交叉与本机两种调用均退出码 1）；用 make 命令行变量覆盖 `CFLAGS`/`LDFLAGS` 就能同时去掉它和链接期 `-s`，且 `$(DEFS)` 由 make 自身展开（实测），无需改 Makefile 一个字节（R6）。
- ✅ OHOS sysroot 的 Linux uapi 头并不缺：`linux/serial.h`、`linux/version.h` 实测存在，`LINUX_VERSION_CODE=330240` 越过上游 `#error` 的 1.3.48 门限，`TIOCGICOUNT=0x545d`/`TIOCMIWAIT=0x545c`/`sizeof(serial_icounter_struct)=80` 都可编可链 ⇒ 本包的缺口只在**运行期设备节点**，不在头文件或 ioctl 编号。
- ✅ 串口守护类的运行面在本平台不可达（`/dev/modem`、`/dev/ttyS*`、`/dev/ttyUSB*` 实测全部不存在，`open()` 直接 ENOENT）⇒ 按"编译 + 静态 + 真实失败形态"申报，不宣称功能可用（同族先例 `knowledge/graph/E485`）。
- ✅ 零测试用例的老工具要如实保留分母：`Makefile` 无 `check`/`test` 目标、包内无测试文件 ⇒ 上游用例数记 0，只报消费者断言 33/33，绝不写"上游测试全通过"。
- ✅ 自查纠偏记录：补丁生成脚本一度把 `---`/`+++` 头整行删掉，`patch` 仍返回 rc=0 但零改动——**"patch rc=0"不是证据**，round-trip 后用 `grep -c` 复算实际变更计数才抓得到（本包该计数为 `0 -> 1`）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/xringd` | 主程序（arm64 ELF，未 strip；上游默认装 `/usr/local/sbin`，此处装包内 `bin/`） |
| `bin/uartcount` | 上游附带的小工具，显示内核 modem 输入计数（需打补丁后可编） |
| `share/man/man8/xringd.8` | 上游 man 文档（装到 `man8`，与上游 `MANDIR/man8` 语义一致） |
| `res/xringd.conf.sample` | 上游 `xringd.conf` 样例配置（上游编译期内置 `/etc/xringd.conf`，运行期用 `-c` 指定，不改源码字面量） |
| `licenses/COPYING` | GPL 全文 |
| `res/doc/xringd/{README,CHANGES,TODO}` | 上游文档 |

## 注意事项

- 上游编译期内置配置文件 `/etc/xringd.conf` 与设备 `/dev/modem`，两者都可用命令行覆盖
  （`-c` / `-m`），因此**不需要**改源码字面量；使用者需自备配置并显式传 `-c`。
- 本包交付不含任何 systemd/init 脚本，也不自动起守护进程。
- 定源哈希记的是**官方 tarball 原件**（gzip 态，`3ecfa6fa…1b77f`）；配方内的 sha256 校验
  经 `source()` 的 urllib 原始字节回退生效，走的仍是这一串官方哈希。
- ⚠ **本地 W3 的绿跑不是跑在官方 HTTPS 址上**：harness 的 W3 会先把源码预取到
  `.build-cache/predl_cache/`，并把 `conandata.yml` 临时改写成 `file://` 再跑
  （日志原话：`[done] Pre-downloaded 1 files, conandata.yml updated to file:// URLs`、
  `Sources correctly downloaded from file:///...854b4309_xringd-1.20.tgz`）。
  ⇒ 绿跑时的 recipe revision = `55168508ba00e6f0fb7028a80b4563fb`；
  交付件（conandata 已还原成官方 HTTPS 址，`git status` 对本文件为空）
  `conan export` 的 revision = `6bd120b9a9253a7b698c641e36cd4b96`。**两者不同一档，不宣称同一 rev**；
  官方址取源的端到端验证另见「定源（一手）」的 3 次采样读数
  （复算命令：`grep -oE "xringd/1.20#[0-9a-f]+" reports/w3-local-ci.log | sort -u`、
  `conan export archives/x/xringd/1.20 --user=ohpcd --channel=stable`）。
---

**编译结束**: 2026-09-27 04:26
**最终状态**: built

---

## 本地门禁证据（程序化抄录，非手写）

- 来源文件：`archives/x/xringd/1.20/.ci-result.json` 与 `reports/w3-local-ci.log`。
- `.ci-result.json` 四字段：`step=W3_local_ci`、`exit_code=0`、`integrity_hash=56d40d1c3b7fc1a2`、`log_sha256=d49b7c57336698d964e94af2f4f2d3f3e0e3a7779000b05f53b74206034dfabf`。
- `sha256sum reports/w3-local-ci.log` 实算值：`d49b7c57336698d964e94af2f4f2d3f3e0e3a7779000b05f53b74206034dfabf`，与上面 `log_sha256` **逐字相同（证据同源，无需另注差异）**。
- conan-verify：`**Verdict**: PASS`，G0/G1/G2/G3 真 PASS，**G4 只有 `⚠️ 无法找到程序包 ID` 一行、未做任何 bin/lib/include 产物清点**，**L2/L4/L5 三者同为 `⏭️ 跳过（无 cache 路径）`**（一手代码依据：`scripts/ohc/conan_verify.py` L741 在 G4 处 early return，`self._cache_path` 直到 L756 才赋值 ⇒ L795-800/L846-851/L936-942 三条走同一条 skip 分支）（逐字见 `reports/conan-verify-report.md` 的 `## <门名>:` 节行，复核命令须带 `-A1` 才证得出子行状态：`grep -A1 -nE "^## (G[0-4]|L[0-9])" reports/conan-verify-report.md`——只打头行会看到 8 个 `✅ PASS` 标题，反而证不出 skip 结论）（报告 `reports/conan-verify-report.md`，该目录被 .gitignore 覆盖，不入 PR）。
- 消费者测试：33 条断言全通过，汇总行 `SUMMARY xringd consumer: total=33 passed=33 failed=0`；上游用例数 0。
- ⚠ **注入痕迹**：交付件 `conandata.yml` 实物只有官方 ibiblio 址一条
  （`grep -n "url:" conandata.yml` = 第 18 行官方址，无 gh-proxy/ghfast/`file://`），
  但 W3 绿跑用的是 harness 预取的 `file://`（见「注意事项」）⇒
  **RREV 差一档**：绿跑 `55168508ba00e6f0fb7028a80b4563fb` vs 交付 `6bd120b9a9253a7b698c641e36cd4b96`，据实登记不粉饰。
