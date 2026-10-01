# lcdproc 0.5.9 — HarmonyOS PC (OHOS aarch64) 适配记录

## 1. 软件概况

| 项 | 值 |
|---|---|
| 上游 | https://github.com/lcdproc/lcdproc |
| 版本 | 0.5.9（2017-06-19 发布，AC_INIT([lcdproc], [0.5.9])） |
| 语言 / 构建系统 | C / Autotools（configure + automake，**无 CMake/Meson**） |
| 许可证 | GPL-2.0-or-later |
| conan 包类型 | `application`（**不产出可链接库**，见 §3） |
| 源码 URL | https://github.com/lcdproc/lcdproc/releases/download/v0.5.9/lcdproc-0.5.9.tar.gz |
| sha256 | `d48a915496c96ff775b377d2222de3150ae5172bfb84a6ec9f9ceab962f97b83` |

R39 源合规：conandata.yml 只登记**上游项目自己的 GitHub release 制品**，已实测
下载并取哈希（上面的 sha256 就是该次下载的摘要），写作时 HTTP 状态为 200。

> **曾经写错的地方（已修正，W4 审计抓出）**：初版 conandata.yml 还登记了
> Savannah/freedesktop 的 `https://download.savannah.nongnu.org/releases/lcdproc/lcdproc-0.5.9.tar.gz`
> 作为备用，并声称它与 GitHub 制品"字节一致、同一 sha256 双向校验"。这两句话
> 都**没有依据**——实测该地址重定向到一个**返回 404** 的镜像，根本取不到
> 文件，既不能当备用源，更谈不上比对。已删除该 URL 并把来源说明改成
> "仅声明真正做过的验证"。
>
> W4 复审时用 `curl -IL` 复测：`num_redirects=1`、最终码 404 —— 即前端一次 302
> 重定向到某个 nongnu 镜像、该镜像直接答 404。镜像主机名会轮换（连续复测轮到过
> `fosszone.csd.auth.gr`、`mirror.rabisu.com` 等不同主机），所以 conandata.yml 只写
> "重定向到返回 404 的镜像"这一可复现事实，**不写死任何具体码值、跳数或主机名**。
> 结论（源不可用）不变。
>
> 旁证（首轮尝试 predl 时缓存下来的是 153 字节的 nginx 404 HTML 页）已随
> `.build-cache/` 一并清理，此处只留结论。

一次 `make` 构建出整个套件：

```
shared/           libLCDstuff.a   ← noinst_LIBRARIES，不安装
clients/lcdproc   lcdproc         ← 系统状态屏客户端
clients/lcdexec   lcdexec         ← 执行 LCDd 菜单命令
clients/lcdvc     lcdvc           ← 虚拟控制台
clients/metar     lcdmetar.pl     ← perl (bin_SCRIPTS)
clients/examples  5 个 perl 脚本
server/           LCDd + 10 个驱动插件 .so + libLCDcommands.a
docs/ scripts/    man 页、sysvinit/debian/rpm 启动脚本
```

## 2. W0 依赖发布检查（R35：用 `conan download -r=ohpcd --only-recipe`）

探测结论：

| 依赖 | 制品仓状态 | 处置 |
|---|---|---|
| **libc / libdl** | 系统自带 | 唯一强制依赖（`LIBS = -ldl`） |
| ncurses/6.5 | 已发布 | **不接入**，理由见 §4 |
| libusb/1.0.27 | 已发布 | 不接入（只有 picolcd/futaba 用，不在默认驱动集） |
| libgd/2.3.3, zlib/1.3.1, libiconv/1.17 | 已发布 | 不需要 |
| libftdi/1.0 | **未发布** | `--disable-libftdi` |
| freetype/2.13.2 | **未发布** | `--disable-freetype` |
| libpng/1.6.45 | **未发布** | `--disable-libpng` |
| glib/2.80.0 | **未发布** | 自动降级 |
| libxml2/2.13.5 | **未发布** | 自动降级 |
| libudev/1.6.15 | **未发布** | 自动降级 |
| libhid, libX11, libusb(0.1) | **未发布** | `--disable-libhid` / `--disable-libX11` / `--disable-libusb` |

> 探测注记：cnb.cool 对**不存在**的配方返回 `ERROR: error:system acceleration policy
> not enabled.`，这是服务端对 404 的误导性文案。判定用 `conan download ... --only-recipe`
> 并把该串映射为 MISSING、用已发布的 `zlib/1.3.1` 做探针标定（R35 禁止用 `conan list` 判定）。

**关键结论：lcdproc 0.5.9 没有强制外部依赖。** 所有重集成都在 `--enable-*`
后面且探测失败即优雅降级，configure 最终以 `LIBS = -ldl` 收尾，因此不需要
按 R36 先补适配任何依赖包，本 PR 也不捎带其它软件（JC6）。

## 3. 为什么是 `application` 而不是库

`shared/Makefile.am` 明确写着：

```make
noinst_LIBRARIES = libLCDstuff.a
```

上游**有意不安装** liblcdproc（它只是给自家客户端和服务端用的内部便利库，
`make install` 也不装任何头文件）。所以本包交付的是**可运行套件**而非可链接库：

- `package_type = "application"`，`cpp_info.libs = []`
- 产物含可执行文件 → 按 **R38** 在**软件级** `archives/l/lcdproc/commands.json` 声明

> 若下游确实需要可链接的 liblcdproc，那是给上游 `shared/Makefile.am` 加
> `include_HEADERS` + `lib_LIBRARIES` 的功能变更，不属于本次「适配到 OHOS」范围。

### bin/ vs sbin/ 的取舍

上游 `server/Makefile.am` 用 `sbin_PROGRAMS=LCDd`。但 conan 的
`AutotoolsToolchain._default_configure_install_flags()` 从
**`cpp_info.bindirs[0]` 同时派生 `--bindir` 和 `--sbindir`**，所以：

- 写 `bindirs = ["bin", "sbin"]` → `--sbindir=${prefix}/bin`，**LCDd 也会落进 bin/**
- 本包显式只声明 `bindirs = ["bin"]`，守护进程与客户端同目录

这是有意为之且已记录：commands.json 按名字寻址，消费者只需把**一个**目录放进
PATH。没有手工补 `--sbindir` 去还原 FHS 拆分，避免与 conan 默认行为打架。

## 4. 功能矩阵（上游默认驱动集，确定性配置）

上游 `LCD_DRIVERS_SELECT` 的**默认**驱动列表是 11 个：

```
bayrad, CFontz, CFontzPacket, curses, CwLnx, glk, lb216, lcdm001, MtxOrb, pyramid, text
```

configure 逐个探测各自依赖，缺依赖的静默跳过。OHOS 上探测结果：

| 能力 | 探测 | 影响 |
|---|---|---|
| `linux/i2c-dev.h` | ✔ | i2c 类驱动可用 |
| `linux/spi/spidev.h` | ✔ | spi 类驱动可用 |
| `sys/select.h` | ✔ | CFontzPacket 可用 |
| 并行口 (`/dev/lp*`) | ✘ | 依赖 LPT 的驱动跳过 |
| ncurses/curses | ✘ | **`curses` 驱动缺席**（见下） |
| libusb / libftdi / libhid | ✘ | 仅 picolcd/futaba 用，本就不在默认集 |
| libpng / freetype / X11 | ✘ | 仅 glcd 等非默认驱动用 |

**实际交付 10 个驱动**（11 减去 curses），且**由配方显式钉死**（见下节
「为什么还要 `--enable-drivers`」）。这里没有裁剪软件：驱动集就是上游默认
列表，减掉的 curses 是因为探测不到 ncurses —— 这正是上游自己设计的行为。

### 为什么不上 ncurses（已发布却仍不接）

ohpcd 的 `ncurses/6.5` **只提供 `libncursesw.a`（宽字符版）**，没有
`libncurses.a`。而上游探测的是非宽字符库（`acinclude.m4` 的 `LCD_DRIVERS_SELECT`）：

```m4
curses)
    AC_CHECK_HEADERS(ncurses.h curses.h)
    AC_CHECK_LIB(ncurses, main, [ AC_CHECK_HEADER(ncurses.h, [
        LIBCURSES="-lncurses"
        DRIVERS="$DRIVERS curses${SO}"])],
    dnl  else
        AC_CHECK_LIB(curses, main, [          ← 活代码，不是被注释掉的
        AC_CHECK_HEADER(curses.h, [
            LIBCURSES="-lcurses"
            DRIVERS="$DRIVERS curses${SO}"])])
```

两处 `dnl else` 只注释掉了**字面量 `else` 关键字**（m4 层不需要它），
其后的 `AC_CHECK_LIB(curses, main, ...)` 是**活代码**、仍会作为
`AC_CHECK_LIB(ncurses, ...)` 的 else 分支执行。

所以真实链路是：`AC_CHECK_LIB(ncurses, main)` 因只有 `libncursesw.a` 而失败
→ 落到 else 分支的 `AC_CHECK_LIB(curses, main, ...)` → 同样探测不到 →
`AC_MSG_WARN([The curses driver needs the curses (or ncurses) library.])`，
驱动进不来。**约束来自"宽字符库不与非宽字符符号探测兼容"这一上游写法**，
不是注释掉代码造成的。要开 curses 驱动只能改上游 `acinclude.m4` 把
`-lncursesw` 接进去（或 `autoreconf` 重新生成），那是上游功能变更、且会把
autoreconf 依赖带进 CI 风险面——**超出本次适配范围**。等制品仓补一个带
`libncurses.a` 的 ncurses 包后，可低成本接入。

### 为什么还要 `--enable-drivers`（`curses` 关不掉）

`curses` 是上游 11 个默认驱动里**唯一没有 `--enable/--disable` 开关**的一个
（实测 `configure --help` 的选项表里既无 `--enable-curses` 也无
`--disable-curses`；`acinclude.m4` 全文无 `AC_ARG_ENABLE(curses)`，只有
`AC_ARG_ENABLE(drivers)` 等）。它是否进 `DRIVERS` 取决于**构建主机上恰好
装没装 ncurses**，所以光靠 `--disable-*` 消不掉主机依赖：同一份配方在装了
ncurses 的 Linux 机器上会打出 **11** 个驱动、在 OHOS CI worker 上打出 **10** 个。

上游 `configure.ac:421` 的 `LCD_DRIVERS_SELECT`（`acinclude.m4:7`
`AC_ARG_ENABLE(drivers)`）为此提供了正解——显式枚举：

```python
tc.configure_args.append(
    "--enable-drivers=bayrad,CFontz,CFontzPacket,CwLnx,glk,lb216,"
    "lcdm001,MtxOrb,pyramid,text"
)
```

这份列表就是**上游默认 11 个减去 curses**，没多删任何一个。实测
configure 输出 `DRIVERS = bayrad.so CFontz.so CFontzPacket.so CwLnx.so glk.so
lb216.so lcdm001.so MtxOrb.so pyramid.so text.so`，本地与 CI 得到同一套驱动，
`test.sh` 用例 7/8 才可以把 "10" 断言成事实而不是平台假设。

### 显式 --disable-* 的理由

留成 `auto` 会让驱动集随构建主机上「恰好装了什么」漂移，导致本地与 CI 不一致。
最典型的坑是 **`--disable-libX11`**：在 Linux 构建机上 pkg-config 会 happily
解析出**宿主机 x86_64 的 `x11.pc`**，交叉编译绝不能捡这个（本地实测
`checking for LIBX11... yes` 就是这个假阳性）。显式关掉让配置可复现。

这 7 个开关都经 `./configure --help` 核对确实存在。`glib2` / `libpango` /
`libgd` / `libxml2` 则**上游根本没提供开关**（只是不探测而已），靠自动降级
处理，因此不在 `--disable-*` 列表里。

## 5. OHOS 适配（4 个补丁，全部登记在 conandata.yml）

### 0001-config-guess-ohos-triplet（E007 / E072）

tarball 自带 **2014-03-23** 版 config.guess，不认识 HarmonyOS。`--build/--host`
是**禁止**的（E007 forbid_1：那会让 configure 认定在交叉编译、跳过全部
`AC_RUN_IFELSE`、生成错误的 config.h）。补丁给两条路：

1. dispatch 里加 `*:HarmonyOS:*:*` uname 分支 —— 供**真机 CI worker**（uname -s = HarmonyOS）
2. **主 dispatch 之前**的独立 case 里加编译器 target 探针 —— 供**交叉构建**：
   只要 `$CC_FOR_BUILD -dumpmachine` 命中 `*-linux-ohos` 就直接输出
   `<cpu>-unknown-linux-ohos`

第 2 点是让本地 WSL 与真机 CI 得到**同一个 host** 的关键：

```
$ config.guess                      # 无 CC
x86_64-unknown-linux-gnu            # 普通 Linux 探测未被破坏
$ CC=/opt/lpk-fixed/clang config.guess
aarch64-unknown-linux-ohos          # 与真机 CI 完全一致
$ ./configure
checking host system type... aarch64-unknown-linux-ohos
checking whether we are cross compiling... no
```

> **踩坑记录**：第一版把探针写成 dispatch 里的 `*:Linux:*:*` 分支，结果**吞掉了
> 所有非 OHOS 的 Linux 探测**——无 CC 时 config.guess 直接
> `unable to guess system type`。shell case 一旦匹配某个分支就不再看后续分支，
> 所以想「可选命中」的逻辑必须放在主 dispatch **外面**。
> 另外 `config.guess` 第 120 行 `CC_FOR_BUILD=$CC` 会自动采纳环境里的 `CC`，
> 所以探针可以直接用 `$CC_FOR_BUILD` 而不必自己找编译器。

### 0002-config-sub-linux-ohos（E072）

**2014-09-11** 版 config.sub 同样不认识 ohos。仓库自带的
`scripts/patch-autotools-ohos.pl` 对这个年代的脚本**一个锚点都匹配不上**
（`android-linux` / `linux-uclibc` / `__ANDROID__` 全部缺失，脚本自评
`Score: 1/5`，config.sub 零改动），所以自己写补丁。

E072 说要改三处，但在 2014 版上**是两处**（第三处 kernel-OS 就是这里的
`case $maybe_os`）：

1. `case $maybe_os` 的 kernel-OS 白名单加 `linux-ohos*`
2. 末尾 `case $os` 的 OS 白名单加 `-linux-ohos*`

> **踩坑记录**：**只改第 1 处**时不会报错，但 `config.sub` 会把
> `aarch64-unknown-linux-ohos` 规范化成 **`aarch64-unknown-linux-gnu-ohos`**——
> 一个错误的、看起来合法的三元组。两处都要改。

### 0003-iface-extern-definition（-fno-common 经典杀手）

```
ld.lld-15: error: duplicate symbol: iface
>>> defined at main.c
>>> main.o:(iface)
>>> defined at iface.c
>>> iface.o:(.bss+0x0)
```

根因：`clients/lcdproc/iface.h` 在**头文件**里放了 tentative definition：

```c
IfaceInfo iface[MAX_INTERFACES];   /* interface info */
```

它被 `main.c` 和 `iface.c` 同时 include。GCC 老版本靠 `-fcommon` 把跨 TU 的
tentative definition 合并成一个 COMMON 符号；**clang ≥ 11 默认 `-fno-common`**，
于是每个 TU 各生成一个强 `.bss` 定义 → 链接期重复符号。

正解（也是最小改动）：`iface.h` 改 `extern`，`iface.c` 补唯一定义。
已确认这是**全树唯一**的头文件 tentative definition——`server/drivers/*.h` 里的
`MODULE_EXPORT char *api_version` 是各驱动 `.so` 各自的模块 ABI（本就该各有一份），
`port.h` 那个是 `static`（内部链接），都不是冲突。

> 备选方案是加 `-fcommon` 编译开关。之所以不选：它是用旗标掩盖根因，且对本树
> 唯一的这一个问题而言收益为零；若日后出现第二处同类问题再权衡。

### 0004-configure-umask-022（E011 / E114）

生成的 configure 第 10477 行与 config.guess 的 3 处：

```sh
tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`
```

在 HMDFS 上运行进程 UID 与映射属主 UID 不一致，`drwx------` 的临时目录
**连属主都写不进去**，config.status 会死在
`can't create ./confXXXXXX/...: Permission denied`。改 `umask 022`（与
jpegoptim 1.4.7 的 0001 同源）。本地 Linux 复现不出来，属于**只在 CI 显形**的
问题，故按 W0b「历史命令在 CI clean 环境里逐字可执行吗」的口径预先规避。

### 无补丁的第 5 项：`ac_cv_mtab_file=/proc/mounts`（构建主机依赖，CI 才暴露）

`acinclude.m4:638` 的 `AC_FIND_MTAB_FILE`（由 `configure.ac:237` 调用）用
**纯 shell `test -f`** 去猜 mount table：

```sh
if test -f "/etc/mtab";      then ac_cv_mtab_file=/etc/mtab
elif test -f "/etc/mnttab";  then ac_cv_mtab_file=/etc/mnttab
elif test -f "/etc/fstab";   then ac_cv_mtab_file=/etc/fstab
fi
if test ! -z "$ac_cv_mtab_file"; then
    AC_DEFINE_UNQUOTED([MTAB_FILE], ["$ac_cv_mtab_file"], ...)
fi
```

**这三个 `test -f` 探的是构建主机，不是目标平台。** 三个都不存在时
`MTAB_FILE` 不会被定义，于是 `clients/lcdproc/machine_Linux.c:265` 命中：

```c
#ifdef MTAB_FILE
	mtab_fd = fopen(MTAB_FILE, "r");
#else
#error "Can't find your mounted filesystem table file."     ← 编译直接死
#endif
```

**为什么本地绿、CI 红**：

| 环境 | `/etc/mtab` | 结果 |
|---|---|---|
| 本地 WSL 交叉构建 | **存在** | `MTAB_FILE="/etc/mtab"` → 编得过 |
| OHOS CI worker | **三个都不存在** | `MTAB_FILE` 未定义 → `#error` |

这正是"交叉构建不应依赖构建主机状态"这一原则的一个实例，而且它**躲过了
E007 forbid_1 的保护**：forbid_1 禁的是显式 `--build=`/`--host=`，而这里是
`test -f`（不是 `AC_RUN_IFELSE`），所以 `cross_compiling=no` 拦不住它。
`ac_cv_mtab_file` 是全 `configure` 里**唯一**一处会喂给 `AC_DEFINE` 的
构建主机文件系统探针（已全量扫描确认；其余 `AC_DEFINE_UNQUOTED` 要么是常量、
要么由编译/链接测试得出）。

**修法：预置 autoconf cache 变量，不改上游源码。** 生成的 `configure:6638`
是

```sh
if ${ac_cv_mtab_file+:} false; then :
  $as_echo_n "(cached) " >&6
else
  ... test -f 探针 ...
```

即预置后**整段探针被短路**，直接采用我们给的值。配方里因此加一行
`ac_cv_mtab_file=/proc/mounts`——`/proc/mounts` 是 Linux 内核系目标真正存放
mount table 的位置，其 `dev mpoint type ...` 行格式正好能被现有的
`sscanf(line, "%s %s %s", ...)` 解析。

实测（OHOS 工具链）：

```
$ ./configure ... ac_cv_mtab_file=/proc/mounts
checking for your mounted filesystem table... (cached) /proc/mounts
$ grep -E '^#define (MTAB_FILE|STAT_STATVFS)' config.h
#define MTAB_FILE "/proc/mounts"
#define STAT_STATVFS 1
```

`STAT_STATVFS 1` 顺带确认了 `machine_Linux.c:293` 的第二处
`#error "statfs for this system not yet supported"` 也不会被命中
（`AC_GET_FS_INFO` 里 `AC_CHECK_FUNCS(statvfs)` 先成功，5 处 `AC_TRY_RUN`
的 statfs 变体探测根本不会执行）。

## 6. R51 上游测试三步法

**第一步 · 清点**：上游**没有**自动化测试。清点证据（在解包后的 tarball 里跑）：

```
find . -maxdepth 3 -type d \( -name 'test*' -o -name 'tests' \) | wc -l            -> 0
grep -rlE '^(TESTS|check_PROGRAMS|check_LTLIBRARIES)' --include='Makefile.am' . | wc -l -> 0
grep -rnE '^(TESTS|check_PROGRAMS)[[:space:]]*=' --include='Makefile.am' . | wc -l     -> 0
```

`make check` 只会走 automake 的空 `check-recursive` → `check-am` 链，什么都不跑、
空洞成功（实测 `make check` rc=0，无任何测试输出）。故属「**上游确无测试**」，
覆盖率全部由 consumer 侧 test_package 新增。

**第二步 · 实测**：本地实跑 8 个用例全部通过（见 §7），是**真实执行被测二进制**
并断言真实输出，不是 echo 空壳。

**第三步 · 回填**：PR 正文如实申报「上游 0 个 / 实测执行 8 个 / 通过率 100%」。

## 7. test_package（9 个用例 / 46 个失败分支）

上游不安装库，consumer 可见面就是可执行套件，所以测试**执行真实二进制**：

| # | 用例 | 断言要点 |
|---|---|---|
| 1 | `lcdproc -h` | 横幅 + `Usage:` + `-s <host>` / `-p <port>` 选项文档（上游只认 `-h`，`--help` 会被拆成短选项而拒绝） |
| 2 | `lcdexec -h` | 横幅 + `Usage:` + `-p <port>` |
| 3 | `lcdvc -h` | 横幅 + `Usage:` |
| 4 | `lcdproc -s 127.0.0.1 -p 39117 -f` | 真实连接拒绝诊断原文 `Error connecting to LCD server 127.0.0.1 on port 39117.` + `Check to see that the server is running`，且**显式断言退出码 = 1** |
| 5 | `lcdvc -a 127.0.0.1 -p 39117 -f` | 真实运行到错误路径 + 真实诊断 + **退出码 = 255**。诊断内容按本机是否有 `/dev/vcs` 二选一，见下方说明 |
| 6 | **鸿蒙特有** | 打包后的 aarch64 OHOS 客户端跑通一次**完整 LCDd 会话**（详见下方专节） |
| 7 | **鸿蒙特有** | `lcdproc`/`lcdexec`/`lcdvc`/`LCDd` 的 ELF `e_machine == 0xB7`（AArch64） |
| 8 | **鸿蒙特有** | LCDd 全部 **10** 个驱动插件同为 AArch64（驱动是运行时 `dlopen` 的，ABI 不匹配只会在 LCDd 启动时才炸） |
| 9 | 载荷完整性 | LCDd + 10 驱动 + 4 个随包配置（`LCDd.conf` / `lcdproc.conf` / `lcdvc.conf` / `lcdexec.conf`） |

用例 4 走的是**真实客户端代码路径**（`sockets.c` → `sock_connect` → TCP 拒绝），
不是只打 usage。用例 6/7/8 是本次要求的**鸿蒙特有测试（N=3）**，其中用例 6 是
**完整消费者端到端用例**（真正跑通一次功能流程），用例 7/8 是产物 ABI 断言。
这些二进制只有因为工具链 target 了 `aarch64-linux-ohos` 才可能存在，
而 1–6 已经证明它们真的在 OHOS 加载器上执行起来了。

### 用例 6：完整 LCDd 会话（不是纯断言）

用例 1–5 只走到客户端的**用法页**和**错误路径**；用例 7/8 是对产物字节的断言。
本套件真正的功能是**客户端与 LCDd 守护进程的一次完整会话**，所以用例 6 把它跑通：

```
TCP 连接 → hello → 几何协商 → 用本机实时数据建屏（C/L/T）→ bye → 退出码 0
```

对端是 `test_package/lcdd_stub.py`——一个最小的 LCDd 线路协议实现。
**它只是测试夹具，不进入包产物**；断言的每一条都落在**打包后的 aarch64 OHOS
客户端真实写上线路的字节**上。

**为什么不用真 LCDd 当对端**（这一点必须写清楚，否则会被读成"绕开真守护进程"）：
`server/sock.c` 用了 `FD_SET`，而 OHOS NDK 的 `<sys/select.h>` 把该宏改写成先调
`__fd_chk(d)`。真机 OHOS libc 导出 `__fd_chk`，本地 WSL 仿真 guest 是普通 musl、
不导出，于是本地连动态加载器都拒绝启动 LCDd（详见 §8）。**拿真守护进程当对端，
这条用例的成败就取决于机器碰巧装的是哪个 libc**——那正是本 PR 前面两次栽跟头的
那类"平台假设"（`AC_FIND_MTAB_FILE` 与用例 5 的 `/dev/vcs`）。被测的客户端
不用 `FD_SET`，所以对它做全程会话在任何 libc 上都是确定的。

**关键断言为什么是硬证据**：

| 断言 | 为什么排除"空壳" |
|---|---|
| `widget_set L zero 33 6 0` | 客户端在收到 `connect` 之前的内置回退是 **20x4**（`main.c:328-331`）。对端协商的 33x6 被逐字回显 ⇒ 握手确实被解析。若客户端忽略了 `connect`，这里只会出现 `20 4` |
| `screen_add` C/L/T + `widget_set C bar 3 4 N` | 屏幕与控件是 `main_loop()` 里 `connected` 为真后才建的；没握手就一个屏幕都不会建 |
| `widget_set L bar19 19 6 N` | 第 19 根柱的行号 `6` 来自协商的 `lcd_hgt`（`load.c:120`），数值来自 `/proc/loadavg` |
| `widget_set T three <x> 4 {HH MM SS N% idle}` | 真实挂钟读数；列偏移由 `lcd_wid` 算出（`chrono.c:150`），分隔符按心跳闪烁（`tickTime`），故断言容忍 `:` 与空格 |
| 客户端自报主机名 == `socket.gethostname()` | 交叉校验：证明客户端读的是**这台机器的实时系统信息**，不是罐头字符串 |
| 收到 `bye` 后**退出码 = 0** | 走 `exit_program(EXIT_SUCCESS)`，即协议级干净退出，而不是被看门狗杀掉（超时会是 124） |

实测抓到的真实上行报文（节选，本机 WSL）：

```
hello
client_set -name {LCDproc lkyz}
screen_add C
widget_set C bar 3 4 0
screen_add L
widget_set L zero 33 6 0
widget_set L bar19 19 6 0
screen_add T
widget_set T title {Linux 6.18.33.2-microsoft-standard-WSL2: lkyz}
widget_set T three 8 4 {15 45 46 3080% idle}
```

**反向验证**（证明它不是"永远通过"的壳）：

| 破坏方式 | 结果 |
|---|---|
| 移走包内 `bin/` | `test.sh` rc=1，停在 `FAIL: lcdproc -h did not exit cleanly (rc=127)` |
| 对端不接任何客户端 | `lcdd_stub.py` rc=1，用例 6 判失败 |
| 对端只收不发（不发 `connect`） | 客户端 `screen_add` 计数 = **0** ⇒ 33x6 断言在结构上不可能被满足 |

### 用例 5 为什么写成"二选一"（平台 CI #64338 的教训）

`lcdvc` 是**虚拟控制台**客户端，它的第一个真实动作是打开 `/dev/vcs` 并读配置，
之后才去连 LCDd。于是**看到哪条诊断取决于机器**：

| 机器 | 路径 | 诊断 |
|---|---|---|
| 有 `/dev/vcs` 的构建宿主 | 走到 `sock_connect` | `Connecting to 127.0.0.1:39117 failed` |
| 无 `/dev/vcs` 的真机（OHOS 硬件） | 提前一步中止 | `Could not open /dev/vcs: No such file or directory` |

初版用例 5 只硬断言第一种，**本地 WSL 全绿、CI #64338 挂在这一行**——
和"驱动数 `-eq 10`"是同一类错误：把平台假设写成了事实断言。
现在断言的是**到处都成立**的不变量：二进制真的跑起来了、走到了错误路径、
打印了真实诊断、**退出码是 255**；两种阶段诊断都接受。
连接路径本身由**用例 4（`lcdproc`，不依赖 `/dev/vcs`）无条件覆盖**，
所以覆盖面没有丢。

顺带：CI 日志里那句 `Could not read config file: //etc/lcdvc.conf` 是
`--sysconfdir` 被 OHOS 工具链传成 `//etc`（双斜杠）所致，客户端读不到就
用默认值继续，**不影响功能**。包内配置实际装在 `<pkg>/etc/`，用例 8 已校验。

### ELF 读取不依赖 `od`

用例 6/7 需要读 ELF 头。`od` 在 OHOS CI worker 上**不保证存在**（该 worker
连 `curl` 都没有，见 §9），而把用例 6/7 变成"考 `od` 存不存在"是本末倒置。
因此抽了 `elf_hex()`：有 `od` 用 `od`，没有就用 `python3` 读——
**conan 本身就是 Python 程序，worker 上 `python3` 必然在**。
两条路径本地实测输出逐字节相同（magic `7f454c46`、`e_machine` `b700`）。

用 `/tmp` 在 OHOS 上只读，故 scratch 树放 `$HOME` 下；OHOS 的 `/system/bin/sh`
是 mksh、没有 `timeout`，超时看门狗用 `background + sleep + kill` 手工搭。

失败分支数（28）与 `test_package/MANIFEST.yml` 的 `assertion_count` 对齐，可复算：

```
grep -c '^pass '   test.sh   # -> 8
grep -c 'fail "'   test.sh   # -> 28
```

（注意别用 `grep -c 'fail '`：注释行 "would only fail at LCDd startup" 也会被计入。
以 `fail "` 为锚点才是精确的调用点计数。）

> §12 里几张审计记录表写的是 **27**，那是**各轮审计当时**的实测值，保留原样不改写
> （改写审计历史等于伪造记录）。活口径是上面的 **28**：CI #64338 之后用例 5 被重写，
> 失败分支从 6 个增加到 7 个（多了"什么都没打印"和"两种阶段诊断都不匹配"两条）。

## 8. 已知环境限制（非包缺陷）

**LCDd 在本地 WSL 无法执行**，因此测试只跑客户端、LCDd 只校验 ELF ABI。

根因链已查清：

1. NDK 的 `sys/select.h` 把 `FD_SET`/`FD_CLR` 改写成先调 `__fd_chk(int)`：
   ```c
   void __fd_chk(int fd);
   #define FD_SET(d, s) do { __fd_chk(d); ... } while(0)
   ```
2. `server/sock.c` 用了 `FD_SET` → LCDd 带 `__fd_chk` 重定位
3. 本地交叉编译用的 sysroot 里 `libc.so` 是 **72KB、0 个动态符号的链接期桩**，
   真正跑起来的是 `/opt/ohos-guest/lib/libc.so`——**普通 musl**，没有 `__fd_chk`
4. 3 行 `FD_SET` 最小复现：`link rc=0`，`run rc=127 / __fd_chk: symbol not found`

真机 OHOS 的 libc 有 `__fd_chk`（NDK 头就是照着它写的），所以 **CI 不受影响**。
这是本地仿真 guest（普通 musl）与 NDK 头（OHOS）不匹配导致的
**验证环境限制**，不是包缺陷。已如实记录，未为此改动任何源码或链接行为
（塞一个假的 `__fd_chk` 会与真机 libc 符号冲突，绝对不能做）。

> 该限制**不影响用例 6**：被测的 `lcdproc` 客户端不用 `FD_SET`，因此"完整 LCDd 会话"
> 这条端到端用例对端用的是线路协议夹具而不是真守护进程（理由见 §7 用例 6）。

## 9. 本地验证结果

| 阶段 | 命令 | 结果 |
|---|---|---|
| W3 硬门槛 | `conan create archives/l/lcdproc/0.5.9 -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing` | **rc=0** |
| 编译 | configure + `make -j1` + `make install` | 4 可执行文件 + 10 驱动 .so + 4 配置 + 5 man |
| test_package | 9 用例 | **9/9 通过** |
| 同源门禁 | `CI_PACKAGES='archives/l/lcdproc/0.5.9' zsh ci/conan/build_and_test.sh` | **Pass rate 100.0% (1/1)**，rc=0 |

E074：`make` 必须 `-j1`（HMDFS 不允许创建 jobserver FIFO）。

### 平台评审（2026-09-29 14:24，评论 id=192115383）三条 FAIL 的整改

评审裁决 `VERDICT=FAIL`，三条阻塞项与处置：

| 规则 | 评审判定 | 根因 | 处置 |
|---|---|---|---|
| rule5 | 非 `archives/`、`knowledge/` 目录的文件改动 1 个：`.gitignore` | 为让 `reports/audit-result.json` 入库改了仓库根忽略规则，但本仓惯例本来不靠改 `.gitignore` | **还原 `.gitignore`**（对 `origin/main` diff 归零），改用已跟踪文件方式保留报告。实测全仓 359 个已跟踪 `reports/audit-result.json` 中 **355 个在 `.gitignore` 里没有任何例外行**，即靠强制入库；本包按多数惯例走 |
| rule12 | 鸿蒙特有测试 N=2 但**只有断言**，缺完整消费者用例 | 改前鸿蒙特有的两条都是 ELF 字节断言，套件真正的功能流程（客户端↔LCDd 会话）一条都没跑 | **新增用例 6**：真实 TCP 会话 + 几何协商 + 实时数据建屏 + 协议级干净退出，详见 §7 |
| rule6 | 未找到 AI 检视评论 | 平台侧 AI 检视只留下两条占位（id=192059809 / id=192059814「正在进行中」），P0–P3 正文自建 MR 起从未落地 | **平台侧问题，代码无法修复**。处置方式＝推送新 SHA 让平台重新触发，不伪造任何检视结论 |

三条都**没有靠改措辞绕过**：rule5 是把越界改动真的删掉，rule12 是补了真实
端到端用例并给出三组反向验证，rule6 如实说明为平台侧并交由重新触发处理。

### 平台 CI 首次跑分（2026-09-29）与它抓出的东西

| 构建 | 结果 | 说明 |
|---|---|---|
| 本地门禁（多次） | 100% (1/1) | 见 §11 |
| CI #64261（worker CI-027） | ❌ 网络问题 | 源码下载超时（`gh-proxy.com` 镜像）。**非配方缺陷**：复测官方 URL `curl -L` 200 / 1091292 字节 / sha256 与申报一致，镜像 2s 可达。按 CI bot 的指引"重试一次" |
| CI #64274（worker CI-037） | ❌ 编译失败 | **真缺陷**：`machine_Linux.c:265: error: "Can't find your mounted filesystem table file."`。根因与修法见 §5「无补丁的第 5 项」 |
| CI #64338（worker CI-011） | ❌ 测试失败 | **真缺陷（测试侧）**：编译已过、**包已产出**，但用例 5 挂在 `FAIL: lcdvc did not report the refused connection`。用例 1–4 在真机通过、`rc==255` 也通过，只是真机无 `/dev/vcs` 导致诊断文案不同。修法见 §7「用例 5 为什么写成二选一」 |

**两次失败暴露的是同一类问题，值得单独记**：本地 WSL 全绿，却连续两次漏掉
**只在真机 worker 上才存在**的行为差异。

1. `AC_FIND_MTAB_FILE` 的 `test -f /etc/mtab` 探的是构建主机——本地交叉环境
   恰好复制了宿主 Linux 的文件系统布局，把这个构建主机依赖**掩盖**了。
2. 用例 5 硬断言了"有 `/dev/vcs` 时"的诊断文案，而真机没有该设备。

两者都指向同一个结论：**"本地 W3 全绿"对构建主机依赖与环境假设是免疫的**，
真机 CI 是唯一能暴露它们的关卡。所以 `create-pr` 之后必须真的等 CI 结果，
绿之前不能报 success。

顺带记录两条 worker 环境问题（与本包无关，但让日志更难读）：
- #64274 日志里 worker 上 **`curl` 不存在**，CI 的 pre-download 步骤 6 次全部
  `[fail] [Errno 2] No such file or directory: 'curl'`，只能退回让 `conan get()`
  自己下载。CI 脚本可以加一条 curl 存在性检查。
- `gitcode_pr.py ci-status` 曾把 `## CI 校验失败` 报成 `✅ PASSED`
  （疑似按正文里出现的"校验通过"字样做匹配，而失败正文里也含该词）。
  **不要以它的摘要为准，要读评论正文首行。**

### 已知非阻塞告警：L4 误报

CI 的 L4 阶段用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 扫补丁，0001 会被命中，
但这是**纯误报**：命中的是英文注释里的单词 **"tar*gets*"**（`when the selected compiler
targets a OHOS triple`）与 **"nbsd *targets* should"**。后者还是 config.guess 的
**未修改上下文行**（patch 的 hunk 上下文），无法在不改动上游内容的前提下去掉。
补丁里没有任何真实的 strcpy/sprintf/gets/strcat 调用。L4_RESULT=warn，不阻塞。

## 10. 环境变更留档

适配过程中（2026-09-28 19:33–19:34）**共享环境**被本会话之外的进程改动过：
conan profile `ohos-aarch64-wsl` 的 `tools.build:compiler_executables` 从
`/opt/ohos-toolchain/clang` 改为 `/opt/lpk-fixed/clang`（自称 “CORRECTED shim v4”，
额外预定义 `__OHOS__`、补 libcxx 头目录），旧 profile 备份为
`ohos-aarch64-wsl.bak-origtoolchain`。

处置：**不还原**（共享基础设施，不在本任务授权范围）。改为**在新旧两个 shim 下
各做一次全量验证**——两次都是 `configure rc=0 / make rc=0 / install rc=0`、
`config.guess` 同样输出 `aarch64-unknown-linux-ohos`、8/8 用例通过。
本包的 0001 补丁用 `-dumpmachine` 探测 compiler target，**不依赖 `__OHOS__`
是否被预定义**，因此对两版 shim 都成立。

## 11. 门禁实测记录

| 阶段 | 结论 | 备注 |
|---|---|---|
| G0 / G0e | pass | 知识图谱 541 条一致；根目录白名单通过 |
| L0 | pass | 含 L0j 版本冲突（首次发布）、L0k commands.json（R38）、L0m 目录结构 |
| KC1–KC5 | pass | 草稿泄漏 / 模板占位符 / rec_auto_fix / 非标准字段 / index.tsv 一致性 |
| JC1–JC6 | pass | 无杂项文件、单软件原子性通过 |
| L1a/L1b | pass | test_package 由 conan create 执行且有断言输出 |
| **L1e** | pass | 破坏性反向验证：移走 `bin/`+`lib/` 后 `conan test` 以 **rc≠0** 失败（`bin/` 不在 → 首个用到它的用例即挂在 `FAIL: lcdproc -h did not exit cleanly (rc=127)`），证明测试真依赖被测包。门禁脚本把 `conan test` 的输出丢进 `/dev/null`，所以本地日志里只留 `[ok] L1e: Negative test confirmed` |
| L2 | pass | 非阻塞 warn：只有 `-h` 的客户端探测不到 `--version/--help`（上游只认 `-h`）；`LCDd` 因 `__fd_chk` 无法在本机执行 |
| L4 | warn | 见 §9「已知非阻塞告警：L4 误报」，不阻塞 |
| L5 | pass | `bin/` 有内容 |

L1e 曾一度失败（"fake test detected"），根因是 test_package 里写了
`if not can_run(self): return`——产物缺失时它让 `test()` **静默返回 0**，
正好是 R34 要抓的空壳形态。去掉该守卫后：产物齐全 → 8/8 通过；
产物被移走 → 立即 rc=1 失败。这是本包唯一一处"测试写法"级别的修正。

新增用例 6 后再次复跑 L1e 仍为 pass（`[ok] L1e: Negative test confirmed`），
且该用例自身还带三组反向验证，见 §7「用例 6」末尾的表。

## 12. W4 独立审计的产出

审计以 `scripts/pre_pr_audit.py generate` 生成输入、由独立子任务按
`templates/audit-prompt.md` 执行，结论与修复见 §1 的 R52 段落
（伪造来源声明 → 删除失效 URL 并改写为只声明真实做过的验证）。
另按审计意见把 `test.sh` 的 `run_guarded` 改为**透传子进程真实退出码**，
并让用例 4/5 显式断言期望的退出码（lcdproc=1、lcdvc=255），超时仍报 124。

### 二次复审（verdict=pass，P0=0 / P1=0）

复审对第一次的 P0 逐条实测复核，全部清零：

| 复核项 | 方法 | 结果 |
|---|---|---|
| GitHub 源可用 | `curl -L` 实测 | 302 → `release-assets.githubusercontent.com` → **200**，1091292 字节 |
| sha256 属实 | 从第一方 CDN 重算 | `d48a91…7b83`，与 conandata/manifest/notes 三处申报值**逐字符相同** |
| 无伪造"字节一致"声明 | 全仓 grep | 3 处命中**全部是否定式免责**或"曾写错已修正"的引述，肯定式声明 0 处 |
| 无 `file://` | 全仓 grep | 0 处 |
| 退出码透传 | 抽出 `run_guarded` 跑退出码矩阵 | 0/1/2/42/255/127 原样透传，看门狗返 124 |
| 断言数自洽 | `grep -c` 实测 | `fail` 27 处 / `pass` 8 处，与当时的 `MANIFEST.yml` 的 `assertion_count: 27` 一致 |

复审另提出 4 条 P2 / 4 条 P3，均已修：

| 级别 | 问题 | 处置 |
|---|---|---|
| P2 | `manifest.yaml` 第 58 行反斜杠+反引号不是合法 YAML 转义，`yaml.safe_load` 抛 `ScannerError`；`scripts/ohc/dispatch.py:290-295` 用 `except: pass` 吞掉它，`manifest_status` 变 `None`，因文件本身存在最终落到 `dispatch.py:325` 的 `init_done` 而**不是** `finished`（少一档进度）；`status: built` 读不出来 | 改成不含非法转义的写法，已用 `yaml.safe_load` 验证通过且 `status` 读出 `built` |
| P2 | 配方宣称"确定性配置"，但 `curses` 是唯一没有 `--enable/--disable` 开关的默认驱动（实测 `configure --help` 里两个都没有），驱动集仍随构建主机装没装 ncurses 漂移，`test.sh` 的 `-eq 10` 实际是平台假设 | 加 `--enable-drivers=<10 个>`（上游默认 11 减 curses），已实测 configure 输出 `DRIVERS = bayrad.so … text.so` 共 10 个，断言升级为事实 |
| P2 | `notes.md` §7 标题写 25 个失败分支，与 `MANIFEST.yml` 的 27 及 test.sh 实测的 27 自相矛盾 | 改为 27，并附可复算的 `grep -c` 命令 |
| P2 | `notes.md` §4 称 curses 探测的 else 分支"整段被注释掉"——实际只有字面量 `else` 被 `dnl`，其后的 `AC_CHECK_LIB(curses, main, ...)` 是活代码 | 按 `acinclude.m4` 原文改述；结论（curses 缺席）不变，但理由换成"宽字符库不兼容非宽字符符号探测" |
| P3 | `conandata.yml` / notes 里写死 Savannah "HTTP 500"，当前实测是 302 → 404 | 改成只陈述可复现的 404 结论，不写死会漂移的码值 |
| P3 | `commands.json` description 写 `sbin/LCDd`，与"只声明 `bindirs=["bin"]`、守护进程与客户端同目录"矛盾 | 改为 `bin/LCDd` |
| P3 | `conanfile.py` docstring 把 `glib2/libpango/libgd/libxml2` 列进 `--disable-*` 清单，实际这四个上游没有开关、只是自动降级 | 拆成"显式 --disable-*"与"无开关、仅自动降级"两句 |
| P3 | worktree 残留 `conandata.yml.orig`（已被 `archives/.gitignore` 的 `*.orig` 忽略）与未跟踪的 `.build-cache/`（未被任何规则忽略，一次 `git add -A` 就会把它扫进 PR 触发 JC1） | 提 PR 前删除 |

### 三次复审（终审，verdict=pass，P0=0 / P1=0）

对上表 8 条逐条**实测**复核，全部修好、且没有引入新问题：

| 复核项 | 实测证据 |
|---|---|
| 失败分支计数 | `grep -c '^pass '` = 8、`grep -c 'fail "'` = 27，与当时的 `assertion_count: 27` 一致；`grep -c 'fail '` = 28 的多出 1 处经 `grep -v 'fail "'` 定位为 test.sh:140 的注释行，正是 notes §7 警告过的那行 |
| manifest YAML | 三个历史版本（`4b2470e`/`877f95a`/`3d35152`）第 58 行均复现 `ScannerError`；当前版本 `yaml.safe_load` 通过，`status` 读出 `built` |
| 驱动钉死 | `./configure --help` 中 `--enable-curses` / `--disable-curses` **各 0 命中**；用配方原样那串 `--enable-drivers=…` 跑完整 out-of-tree configure → rc=0，`server/Makefile` 的 `DRIVERS =` 恰 10 个 `.so`、无 curses；逐项比对 `acinclude.m4:24` 的 11 个默认值确认**只减了 curses、没多删任何驱动** |
| ncurses 论述 | `acinclude.m4:71-99` 确认只有 4 处字面量 `else` 被 `dnl`，第 85 行 `AC_CHECK_LIB(curses, main, ...)` 是活代码且确为第 73 行的 else 分支 |
| bin/sbin 布局 | 读 conan 源码确认 `--bindir`/`--sbindir` 同取 `cpp_info.bindirs[0]`；按此实跑 install → `bin/LCDd` 存在、`sbin/` 不存在 |
| `--disable-*` 清单 | `generate()` 的 for 元组恰 7 项，`configure --help` 里 7 个开关全部存在；`glib2/pango/gd/libxml2` 的 8 种拼写各 0 命中，与"无开关、仅自动降级"一致 |
| R51 清点 | MANIFEST.yml 申报的 4 条清点命令在**全新解包**的纯净 tarball 上实测全部返回 0；`make check` rc=0 且只输出 `Nothing to be done for 'check'`，"空洞成功"属实 |
| 反向验证 | 审计方自行 configure+`make -j1`+install 后用提交的 test.sh 实跑 8/8 全 PASS，并复现 L1e 的 rc≠0 失败 |
| 权限边界 | 12 文件全在 `archives/l/lcdproc/` 下，`git diff --stat 401c1e75a9...HEAD -- SKILL.md references/ templates/ scripts/ ci/ index.tsv SUMMARY.md` 为空 |

终审另提 1 条 P2 / 5 条 P3，均已修：

| 级别 | 问题 | 处置 |
|---|---|---|
| P2 | `conanfile.py` 的 `import os` 是死代码（AST 全量核对：9 个导入名里只有 `os` 从未引用，无 `os.path`/`os.environ`/`os.makedirs`） | 删除该行 |
| P3 | §11 里引用的 L1e 失败原文 `FAIL: lcdproc -h lacks its banner`（test.sh:83）在门禁真实的 `mv` 走 `bin/`+`lib/` 路径下到不了——`bin/` 不在时第 80 行就先炸，`rc=127` | 换成实测到的 `FAIL: lcdproc -h did not exit cleanly (rc=127)`，并说明门禁脚本把 `conan test` 输出丢进 `/dev/null`、本地日志看不到这行 |
| P3 | §1 写死镜像主机名 `mirror.accum.se`（会轮换，今天已换成别的镜像） | 删掉主机名，与 conandata.yml 统一口径 |
| P3 | §1 拿 `.build-cache/predl_cache/ab9f9175_*.tar.gz` 当证据，但该文件已随清理删除，读者无法复核 | 改为"旁证已随 `.build-cache/` 清理，此处只留结论" |
| P3 | 上表把 dispatch.py 的后果写成"误判 `not_started`" | 按 `dispatch.py:296-327` 的实际分支订正为"落到 `init_done`、少一档，不会到 `not_started`" |
| P3 | worktree 的 `conandata.yml.orig` 在二次复审时只清了一半（`.build-cache/` 删了，`.orig` 被后续门禁跑重新生成） | 提 PR 前再清一次 |

### 四次复审（定稿，verdict=pass，P0=0 / P1=0）

对上轮 6 条逐条实测：死导入已清（AST 全量核对，`conanfile.py` 8 个导入名 /
`test_package/conanfile.py` 2 个，死导入均为 0）、`.build-cache/` 与
`conandata.yml.orig` 均已不存在、`dispatch.py` 档位与 `L1e` 失败原文均已订正。
其中「镜像重定向」那条只修了一半（主机名删了、跳数还写死），见下表。

定稿另提 1 条 P2 / 1 条 P3，均已修：

| 级别 | 问题 | 处置 |
|---|---|---|
| P2 | `commands.json` 声明 `binary: true`，与同 PR 的 `manifest.yaml` `status: built` 矛盾。`references/iron-rules.md:695-700` 明确 `true` = 已通过 release 流水线发布、"适配完成并 CI upload 成功后"才置 `true`；本包尚未 upload。全仓实测同为 `status: built` 的版本声明里 `binary: false` 1695 条、`true` 962 条，`false` 才是多数口径 | 改为 `binary: false`，待 release 流水线 upload 成功后由 finish 步骤置回 `true` |
| P3 | §1 把镜像重定向的**跳数**写死成 "302 → 302 → 404"，与紧邻的"不写死任何具体码值"自述矛盾；实测 `curl -IL` 是 `num_redirects=1` 直接到 404，从未出现第二跳 302 | 改为陈述可复现事实："前端一次 302 到某个 nongnu 镜像、该镜像直接答 404"，并注明主机名会轮换（实测轮到过 `fosszone.csd.auth.gr`、`mirror.rabisu.com`） |

定稿轮的其它取证结论：12 文件 100% 在 `archives/l/lcdproc/` 下，框架文件
`git diff --stat` 全空；4 个 patch 在纯净 tarball 上 `patch -p1` 全 rc=0、无
`.rej`；sha256 实测下载 200 / 1091292 字节 / 摘要与申报四处逐字符相同；
`--enable-drivers` 列表与 `acinclude.m4:24` 的 11 个默认值作差集**只差
`{curses}`**（无偷裁软件）；R51 的 4 条清点命令在全新解包的纯净 tarball 上全返回
0，`make check` rc=0 且 15 处 `Nothing to be done`、0 条 PASS/FAIL。

> 一处如实标注的取证边界：§2/§4 关于「ohpcd 的 ncurses/6.5 只提供
> `libncursesw.a`」的制品内容断言，四轮审计均未能独立核实（`--only-recipe`
> 可用、`conan list` 能看到 OHOS armv8 包 ID，但按 pkgid 拉二进制返回
> `ERROR: error:route not matched`）。该前提即使有偏差也不影响结论——配方已用
> `--enable-drivers` 显式钉死驱动集，curses 无论在不在制品仓都不会被编进去。
