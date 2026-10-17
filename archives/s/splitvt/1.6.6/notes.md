# splitvt 1.6.6 -- HarmonyOS PC (OHOS) aarch64 适配笔记

- 任务：平台任务 10861，分支 `feat/splitvt-1.6.6`，基线 `origin/main`
- 源码：`https://slouken.libsdl.org/projects/splitvt/splitvt-1.6.6.tar.gz`
  sha256 `70a03afe3a43c7458c5fe0152c386f62669107e045b973aecc667259b1820937`（64797 B）
- 构建系统：作者手写的 `/bin/sh` `configure`（**没有 configure.ac，也没有 CMake**）：它编译
  `config.c` → 在构建机上运行它 → 由 `config.c` 用 `fprintf()` **打印出整个 Makefile**
- 产出：`bin/splitvt`（PIE ELF64 aarch64，50816 B，DT_NEEDED 只有 `libc.so`）
- 依赖：**无**（详见 §7，登记表里写的 ncurses 经实测不是本包依赖）

证据件（鸿蒙 PC A 机实拍，均在 `~/tmp/uc2/z41-splitvt/`）：
`logs/upstream-test-audit.log`、`logs/consumer-suite.log`、`logs/ohos-suite.log`、
`logs/probe-pty2.log`、`build5.log`、`cfg.log`、`probe-pty2.c`。

---

## 1. 症状：1993 年的"探测"在现代 sysroot 上全体静默判否

**症状。** 直接跑上游 `sh configure && make` 会得到一个"看起来正常"的 Makefile：

```
CC = gcc
PTYOPTS = -DPTYCHAR=\"\" -DHEXDIGIT=\"\"
CFLAGS =  -O2 -DSHELL=\"/bin/sh\" $(PTYOPTS)
LIBS =
```

注意 `CFLAGS` 里**一个 `HAVE_*` 能力宏都没有**。随后 `make` 在
`splitvt.c` / `misc.c` 处炸出成串错误，且报错点离根因很远：

```
misc.c:568:16: error: variable has incomplete type 'struct sgttyb'
misc.c:573:16: error: use of undeclared identifier 'TIOCGETP'
misc.c:576:22: error: use of undeclared identifier 'ECHO'
cut-paste.c:315:2: error: non-void function 'vt_getsel' should return a value [-Wreturn-type]
```

**根因。** `config.c` 的全部特性判定都是对 FHS 路径做 `stat`：

```c
#define INCLUDE "/usr/include/"
if ( exists(INCLUDE, "termio.h") )   strcat(cflags, " -DHAVE_TERMIO_H");
if ( exists(INCLUDE, "unistd.h") )   strcat(cflags, " -DHAVE_UNISTD_H");
if ( grep (INCLUDE, "utmp.h", "ut_host") ) strcat(cflags, " -DHAVE_UTHOST");
if ( exists("/usr/lib", "libtermcap.a") )  { -DTERMCAP; -ltermcap }
```

而本机 **`/usr/include` 根本不存在**（头文件在 clang 的 sysroot 里：
`/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/../../sysroot/usr/include`）。
于是每一个探测都回答"没有"，`config.c` 也不会报错——它只是把"探测失败"当成"特性不存在"，
把一份缺能力宏的 Makefile 打印出来。**探测层判否，代码层却另有依据**：本机 clang 15
（`aarch64-unknown-linux-ohos`）**同时预定义 `linux`、`__linux__`、`__OHOS__`**
（`echo | clang -dM -E -x c -` 实测四条都在），所以 `config.c` 自己走
`#ifdef linux` 分支（打印 "Aha! You are running Linux!"、写 `CC = gcc`、链接加 `-s`），
`misc.c:187` 的 `#if defined(SOLARIS) || defined(linux)` 也选中 SVR4 pty 路
（`/dev/ptmx` + `grantpt/unlockpt/ptsname`，这正是我们要的路径）。
⇒ **同一份源码里，"能力探测"与"分支选择"两套机制给出的答案互相矛盾，而探测那套是错的。**

**最小复现。**

```sh
[ -e /usr/include ] && echo EXISTS || echo MISS     # -> MISS
[ -e /usr/lib/libtermcap.a ] && echo YES || echo NO # -> NO
echo | clang -dM -E -x c - | grep -E 'define (linux|__linux__|__OHOS__)$'   # 三条都有
CC=clang sh ./configure            # 打印 "Aha!  You are running Linux!"
grep -n CFLAGS Makefile            # CFLAGS 里没有任何 HAVE_* 宏
make CC=clang                      # 上面那串 error
```

## 2. 已试过、被否掉的方案

| 方案 | 结果 | 为什么不用 |
|---|---|---|
| `make CFLAGS="… -DHAVE_UNISTD_H …"` 覆盖 CFLAGS | **失败**：`splitvt.c:264: error: use of undeclared identifier 'bin' / 'sh'` | 上游 Makefile 里 `-DSHELL=\"/bin/sh\"` 的引号要经过 make 与 recipe shell **两级解析**（E575 的机制）：命令行传 `"… -DSHELL=\"/bin/sh\" …"` 时反斜杠在第一级就被吃掉，第二级把引号剥光，宏退化成 `/ bin / sh` 三个 token。覆盖 CFLAGS 还顺带丢了上游的 `-O2`/`PTYOPTS` |
| 改 `config.c`，把探测改成 sysroot 感知 | 可行但补丁面大 | 要为每个特性手写探测程序，等于重写一份 autoconf；且生成物（Makefile）不可审计 |
| 配方自己手写一份 Makefile | 可行 | 绕开上游构建系统，`-DSHELL`/`PTYOPTS`/目标拓扑全靠抄，升级即失效 |
| 给缺的原型加 `extern` 声明补丁（逐函数） | 可行但散 | 见 §3，`-include unistd.h` 一次解决且顺带暴露真 bug |
| 关掉 `-Wreturn-type`（`-Wno-error=return-type`）凑绿 | 不采用 | 那是真的 UB（函数落到末尾返回垃圾指针），消音等于把缺陷藏进产物 |

## 3. 最终方案

### 3.1 能力宏走 **CPPFLAGS**，绝不覆盖 CFLAGS

上游生成的 Makefile 从不给 `CPPFLAGS` 赋值，而 GNU make 内置 `.c` 规则是
`$(CC) $(CFLAGS) $(CPPFLAGS) -c` ⇒ `CPPFLAGS` 是唯一"命令行能进、又不顶掉任何东西"的槽位：

```python
_CAPABILITY_FLAGS = ("-DHAVE_UNISTD_H", "-include unistd.h")
self.run('make -j%s CC="%s" CPPFLAGS="%s" splitvt' % (jobs, cc, caps), ...)
```

- `CC` 必须走命令行（不是环境变量）：生成的文件里有 `CC = gcc`，而 **makefile 内的赋值优先于环境变量**；
  编译器路径取自 `tools.build:compiler_executables`（R33：不从裸 shell 变量取）。
- `-DHAVE_UNISTD_H`：补回 `splitvt.c` 被探测层关掉的那个宏。
- `-include unistd.h`：**这是正确性修复，不是卫生问题。** `utmp.c:36` 在没有原型的情况下调
  `ttyname(0)`，隐式声明返回 `int` ⇒ aarch64 上指针被截成 32 位（`strlen` 拿到的是垃圾地址）。
  原型一可见，立刻又暴露第二处真缺陷：`misc.c:409` 用的是 BSD 双参
  `setpgrp(0, 0)`，而 musl 只声明 POSIX `setpgrp(void)` ⇒ 从"静默 no-op"变成硬错误。
  于是有了补丁 0001（`setpgid(0, 0)`）。**判据**：`-include` 之后新冒出来的错误，
  都是原本就在源码里的缺陷，不是被 flag 制造出来的。

### 3.2 五个补丁（都是 portability，无平台宏，R8/PF5 安全）

| 补丁 | 文件 | 症状 → 处置 |
|---|---|---|
| 0001 | misc.c | `error: too many arguments to function call, expected 0, have 2`（`setpgrp(0,0)`）→ BSD `setpgrp(pgid,sess)` 就是 POSIX `setpgid(pgid,sess)`，一字对齐替换，后面的 `TIOCNOTTY` 语义不变 |
| 0002 | misc.c | `struct sgttyb` incomplete / `TIOCGETP` / `ECHO` / `RAW` undeclared：本机既无 `<termio.h>` 也无 `<sgtty.h>`（sysroot 实测 `MISSING termio.h`、`MISSING sgtty.h`），legacy 分支**两头都死** → 用 `__has_include(<termios.h>) && !__has_include(<termio.h>)` 守卫，把 System V 那支改接 POSIX termios：`struct termio→termios`、`TCGETA→TCGETS`、`TCSETA/TCSETAW→TCSETS`（TCSETAW 的"等输出排空"由 termios 的 TCSADRAIN 语义承担）。glibc 上 `__has_include(<termio.h>)` 为真 ⇒ 原行为完全不变 |
| 0003 | vttest.c | 同 0002（终端自检程序 `vttest.c` 自己再复制了一套 `#define termio sgttyb`）；定义 `HAVE_TERMIO_H` 还顺带让它走 VMIN/VTIME 字符定时器，而不是 `SIGALRM`+`setjmp` 兜底支 |
| 0004 | cut-paste.c | `error: non-void function 'vt_getsel' should return a value`（clang 15 把 `-Wreturn-type` 当错误）→ 按同函数"取消选择"分支的既有语义 `return(NULL)` |
| 0005 | misc.c | **功能缺陷，不是编译缺陷**：`dropctty()` 只在 `_POSIX_SOURCE` 等旧条件下才 `setsid()`，否则走 `setpgid + TIOCNOTTY`。但 fork 之后 `pty_open()` 用的 `ioctl(0, TIOCSCTTY, 0)` **只允许会话首进程调用** ⇒ 子进程永远拿不到自己的 pty，窗口里的交互式程序（shell）判定自己是后台作业，**你敲进去的行被 ldisc 回显、却永远不被执行**。⇒ 把 POSIX 支的条件扩成"凡有 `TIOCSCTTY` 者"（能力守卫，非平台宏）。实测对照见 §4 |

### 3.3 构建/打包流程

1. `sh ./configure`（**故意不带参数**）：让 `config.c` 把它每一问的答复打进日志——
   那就是 §1 的证据链（`cfg.log`）。
2. `make -jN CC=<clang> CPPFLAGS="<能力宏>" splitvt`。
3. `./splitvt -v | grep -F "Splitvt 1.6.6"`：上游唯一能在构建期跑的自述，跑真、断言、失败即红。
4. `package()` 显式装：`bin/splitvt`、`licenses/COPYING`、
   `man/man1/splitvt.1`（= 上游 `install-man` 的 `cp splitvt.man …`）、
   `res/splitvt/{examples,escapes,utils,docs}`。**不调 `make install`**：
   上游的 install 用 `mv` 把二进制搬进 `/usr/local/bin`（无 PREFIX、无 DESTDIR）。

## 4. 实测对照（补丁 0005 的依据）

同一份已打 0001-0004 的源码，仅 `dropctty()` 一支的差别，在真 pty 下跑
`splitvt -norc -upper /bin/sh -lower "/bin/echo LOK"`，往 master 里灌 `echo XOLY\r`：

| 构建 | 子窗口 shell 提示符 | 命令是否被执行 |
|---|---|---|
| 未扩 POSIX 支（`setpgid`+`TIOCNOTTY` 路） | 无 `$` | 只回显 `echo XOLY`，**不输出** `XOLY` |
| 扩 POSIX 支（`setsid()`，等价 0005） | 有 `$ ` | 输出 `XOLY` ⇒ 真执行 |

⇒ 消费者套件把这条钉成断言：S4 `upper window shell became interactive` + `command typed into the upper window was executed`。

## 5. 测试账本（五维，判据见 `logs/`）

| 维度 | 数 | 依据 |
|---|---|---|
| `N_static`（上游静态声明） | **0** | 发行包 46 条目全清单里无任何 test/spec/check 命名文件；全树无 `check:`/`test:` 规则；无 `t/`、`tests/`、`test/`、`spec/` 目录（扫描过程与逐项目录清单见本节文字；原始扫描输出 `logs/upstream-test-audit.log` 第 1/2/4/6 节是设备侧历史件、未随 PR，判据以上表可复核的目录/规则零命中为准） |
| `N_registered`（构建系统注册） | **0** | 生成的 Makefile 只有 5 个目标：`splitvt`/`clean`/`distclean`/`install`/`install-man`（审计第 3 节） |
| `N_executed`（上游套件实跑） | **0**（无可跑对象） | 同上；`make check` 在上游不存在，**不声称跑过**。构建期实跑的是上游自带的自述入口 `splitvt -v`（1 项，在 `build()` 中真实执行并断言） |
| 未执行/跳过分类 | **0 项需解释** | 上游没有声明任何用例，故没有"因平台受限而跳过"的用例 |
| `N_consumer`（新增消费者测试） | **2 个测试程序 / 29 条断言**，全通过 | `test_splitvt_pty.py`：6 场景 18 断言；`test_ohos_specific.py`：6 检查点 11 断言。两条判决行原文取自带新 HEAD 的 W3 日志：`reports/w3-local-ci.log:1504` = `RESULT: passed=18 failed=0 skipped=0`、`reports/w3-local-ci.log:1519` = `RESULT: passed=11 failed=0 skipped=0`。（改引说明：`logs/consumer-suite.log`/`logs/ohos-suite.log` 是配方末次改动**之前**那轮的设备侧日志，mtime 早于 `conanfile.py`，故不再充当判据，只作历史件披露、未随 PR。）（该日志按仓内 .gitignore 的 reports/ 规则未随 PR，属设备侧 W3 产物；两条 RESULT 判决行已原文引在本行，读者无需取件即可核对。）

适配后合计 29 ≥ 上游静态合计 0。**分母口径**：上表"通过率"只按已执行项算，
不把不存在的上游用例并入分母，也不把消费者断言冒充上游全量。

消费者测试为什么是"真测"：splitvt 的产物是"造两个伪终端并在上面跑程序"，
所以两套测试都在**真 pty** 下起 `bin/splitvt`，从 outer master 读它渲染出来的字节，
断言"两个子程序的输出都到了屏幕 / 敲进去的命令被 shell 执行 / 非 vt100 终端按文档拒绝并 exit 3 /
退出时滚动区被复位"。文件存在性检查一个都没有；把 `bin/splitvt` 搬走，两条用例立刻失败（CI L1e 反向验证可过）。

## 6. pty / termios 能力面探针（机制矩阵 #5，一次做清）

探针 `~/tmp/uc2/z41-splitvt/probe-pty2.c`（非阻塞版：master 设 `O_NONBLOCK`，
所有等待走 `select` 超时，失败一律打 errno），读数 `logs/probe-pty2.log`：

| 面 | 读数 | 结论 |
|---|---|---|
| `openpty()` + winsize | rc=0，master=3/slave=4，`ttyname=/dev/pts/2`，`TIOCGWINSZ` 回读 24x80 | **可用** |
| `/dev/ptmx` + `grantpt`/`unlockpt`/`ptsname`（splitvt 实际走的路） | open fd=5；grantpt rc=0；unlockpt rc=0；ptsname=/dev/pts/3；`stat` mode=**600** uid=gid=**20020105**（调用者自己）；access/open 均可 | **可用，且从节点天然归属调用者** ⇒ splitvt 历史上的 setuid-root 需求在本机是空转（其 `chown/chmod /dev/tty` 一律 EPERM，但源码里都 `(void)` 掉了） |
| ldisc 回显 | 写 master 2 字节 → master 读回 2 字节（ECHO+ICANON 默认态） | **回显由行规程产生**，不是 master 自环；raw 模式下双向 4 字节互传正常 |
| canonical 缓冲 | 写 master `"xy"` 不敲换行 → slave 读超时；切 raw 后 slave 一次读到 6 字节（残留 2 + 新 4） | 与 glibc/POSIX 语义一致 ⇒ **先前"读 slave 卡住"是探针没敲换行，不是平台墙** |
| `struct termios` | `sizeof=60`、`sizeof(tcflag_t)=4`、`NCCS=32`；成员名 `__c_ispeed/__c_ospeed`（**没有** `c_ispeed/c_ospeed`）⇒ 必须用 `cfgetispeed()` | 命中既有草稿 `DRAFT-ohos-ndk-termios-ispeed-ospeed-member`，非新知 |
| `TIOCPKT`（packet 模式） | 宏存在（21536），但 `ioctl(master, TIOCPKT, &1)` → **rc=-1 errno=13 EACCES** | **本机不可用**。但 splitvt 源码里**一次都没用** TIOCPKT ⇒ 与本 PR 无实质关联，按"不得搭便车"不作为本 PR 的 B 交付（只回填探针清单矩阵） |
| `SIGALRM` 真实定时器 | `alarm(1)+pause` 实测 elapsed=**1.000s**；`alarm(0)` rc=0 | 可用（`vttest.c` 的非 termio 兜底支依赖它，本机走的是 VMIN/VTIME 支） |
| setuid 降级路（`misc.c:112/880`） | `setuid(getuid())` rc=0；`setuid(0)` EPERM | 非 setuid 安装下是 no-op，安全 |
| 正向对照 | `isatty(slave)=1`、`tcsetattr(TCSADRAIN)` rc=0、`fork+waitpid` 状态 7 | 全通过 ⇒ 上面任何 EACCES 不是"整条机制挂了" |

## 7. W0：ncurses 到底要不要（证伪登记表的依赖）

登记台账把依赖写成 ncurses。实测结论：**本包不需要任何第三方库**。

1. 源码里 termcap 全部在 `#ifdef TERMCAP` 之后（`terminal.c:88` 起），
   `TERMCAP` 只由 `config.c` 在 `exists("/usr/lib","libtermcap.a")` 为真时打开——本机 **MISS**（`/usr/include` 都不存在，`/usr/lib` 里没有 `libtermcap.a`）。
2. 未定义 `TERMCAP` 时，`terminal.c:207` 起的 `#else` 支把 VT100 转义序列**硬编码**
   （`\033[?3h`、`\0337`、`\033[%sm` …），功能不缺，只是不查库。
3. 产物 `DT_NEEDED` 只有 `libc.so` —— 这条被 `test_ohos_specific.py` 的 C3 钉成断言，
   不是口头声明。
4. 因此配方 `requires()` 为空，W0/R36 没有需要先发布的依赖；
   `preflight_check.sh splitvt/1.6.6` 复跑见 `reports/`。
   （登记台账的依赖项**不修改**——那是主理的权限，结论在此报告。）

## 8. 已知限制（对外口径）

1. `examples/xsplitvt`、`examples/menu`、`utils/getxtitle`、`utils/treset` 是
   `#!/bin/sh` / `#!/usr/bin/perl` 包装脚本，依赖 xterm / perl 环境；本包按上游
   原样装进 `res/splitvt/` 作参考，**不写进 `commands.json`**（命令清单的语义是
   "可执行命令"，装了跑不起的不算少报）。`bin/` 下唯一的可执行命令就是 `splitvt`。
2. 未定义 `TERMCAP` ⇒ 终端能力走硬编码 VT100 序列，与上游在非 termcap 系统上的
   行为一致；`splitvt.man` 里提到的 termcap 取能（`li`/`co`）在本机构建里不生效，
   行列为固定 24x80 起点，再按 `TIOCGWINSZ` 校正（`vt100.c:875`）。
3. utmp 记账实际不可用：`/etc/utmp` 不存在（实测 MISS），且
   `utmp.h` 提供的 `struct utmp` **没有 `ut_host` 字段** ⇒ 探测层"猜对"了
   （不会定义 `HAVE_UTHOST`）。程序在 `getpwuid()` 返回 NULL 时只打印
   `Warning: Can't find your passwd entry; no utmp logging.` 并继续
   （与既有条目 E338 的 musl 无 NSS 行为一致），每次启动多等 2 秒。
4. `install` 目标搬文件到 `/usr/local/bin`，本配方不调用它。
5. 本包按"造伪终端"的工具适配，测试**全部带硬超时**（`select` + 会话级预算 +
   超时即 SIGKILL 后回收），任何一步都不可能把构建挂住。

## 9. 适用边界（这条经验到哪为止）

- §1/§3.1 适用于**所有"手写 configure 靠 stat FHS 路径探测特性 + 自己 printf 一份
  Makefile"** 的上游（splitvt 这一类 1990s 时代的 `Configure`/`configure.com` 后裔）。
  前提条件：①`/usr/include` 不是目录（本机实测 MISS）；②编译器仍预定义
  `linux`（本机实测有）。两者有一条不成立，症状就会不同，别照搬。
- `CPPFLAGS` 注入这条，只在"上游 Makefile 用 `=` 给 CFLAGS 赋值、且没定义
  CPPFLAGS"时成立。若上游 Makefile 自己赋值了 `CPPFLAGS`，就得换
  `make CPPFLAGS+=` 或按 E575 的两级转义写全。
- 补丁 0002/0003 命中既有条目 **DRAFT-E567**（legacy termio ioctl 宏能力守卫）与
  **DRAFT-E565**（musl 宏重定义），差别只在：本包**两支都死**（既无 `<termio.h>`
  也无 `<sgtty.h>`），所以不是"隔离 legacy 支保留 POSIX 支"，而是
  "把 System V 支改接 POSIX termios 让它活下来"。
- 补丁 0005（会话首进程 + `TIOCSCTTY`）适用于任何"fork 后把 pty 从节点接成控制终端"
  的老代码：判据是"子进程的交互式程序只回显不执行"。
- §6 的 `TIOCPKT=EACCES` 是本机平台读数，但 **splitvt 不用 packet mode**，
  所以它只是探针清单矩阵 #5 的回填数据，不构成、也不申报本 PR 的路径 B 知识。
---

**编译结束**: 2026-09-25 20:00
**最终状态**: built

## 10. 路径 B 最小声明（3+2）

- **适配路径**：路径 A（配方直适配）+ 路径 B（知识库扩展）
- **使用知识库**：openharmony-compile-agent；次级两处归既有族——`-DSHELL` 经 make 与 recipe shell 两级解析、覆盖 CFLAGS 会丢 -O2/PTYOPTS 属 E575，musl 无 NSS 致 `getpwnam()` 返 NULL、每次启动多等 2s 属 E338
- **知识库扩展**：新增机制条目 `DRAFT-10861-splitvt-1.6.6-tioccsctty-needs-session-leader`（.kv/.md 成对，随本 PR 提交）
- **关联 Issue**：#3415（【知识库扩展】splitvt 1.6.6：fork 出的子进程必须先 `setsid()` 成为会话首进程，`ioctl(TIOCSCTTY)` 才能绑定 pty 控制终端）

**B 判定依据**：宽口径逐词检索 `TIOCSCTTY`、`setsid`、`TIOCNOTTY`、`setpgid`、`ctty`、`controlling terminal`、`session leader`、`ldisc`，检索面含 `knowledge/graph/index.tsv` 全域与 `knowledge/drafts/`（`draft-review` 不扫 drafts 目录，是已知查重盲区，故手工补扫）⇒ 无同类条目；图谱近邻 E361 经逐行读原文排除（其根因是 MPI 分离后代 canary 与 15s 清理窗口的时序，与本机制无交集）⇒ 不属 hit 四条件，判 create。

**本轮（2026-09-25 主理-48 按 W4 独立审计整改）**：草稿的 `rec_command` 与示例块原写字面 `defined(HAVE_TIOCSCTTY)`，与 0005 补丁实际落地的 `defined(TIOCSCTTY)` 不一致（归档内 `HAVE_TIOCSCTTY` 零命中，照草稿执行条件永假、缺陷复发）⇒ 已改为与补丁逐字一致；测试账本判据由设备侧 `logs/*-suite.log` 改引 `reports/w3-local-ci.log` 的判决行。两处均为文档/知识件修正，未动 `conanfile.py` 与 `conandata.yml` ⇒ 构建输入与 recipe revision 未变，W3 证据（`log_sha256` 见 `.ci-result.json`）仍对应当前产物。
