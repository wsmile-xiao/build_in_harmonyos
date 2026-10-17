# pMARS 0.9.5 — HarmonyOS PC 适配笔记

软件：pMARS（portable Memory Array Redcode Simulator），Core War 对战模拟器，ICWS'94 标准。
上游主页 <http://www.koth.org/pmars/>（koth.org 即 pMARS 的官方归属站）。
构建系统：**bare Makefile**（无 configure / 无 CMake / 无 autotools）。语言：C。
本包产物：单个可执行文件 `pmars` + 随包战士/选项/文档数据。

---

## 1. 货源与版本口径

### 1.1 货源

官方发布物是 **zip**，不是 tar.gz：`http://www.koth.org/pmars/pmars-0.9.5.zip`。
文件名不是猜的——在构建主机上取目录页 `href` 实测：

```
curl -sS http://www.koth.org/pmars/ | grep -o 'href="[^"]*"'
  href="ptools11.zip"
  href="pmars-0.9.5.zip"      <-- 命中
  href="pmars-0.9.5-win.zip"
  href="pmars-0.9.4.zip"
```

`sha256` 由构建主机对**实下载文件**跑 `sha256sum` 得出（不取自任何第三方页面）：

```
pmars-0.9.5.zip  HTTP=200 SIZE=243479
6c7c72dbd2a6670d36ba7a96b113d2b54557508afdd99573dfa1da6557700d37  pmars-0.9.5.zip
file: Zip archive data, requires at least v2.0 to extract
头 8 字节: 50 4b 03 04 14 00 00 00   (PK\x03\x04)
```

**载体与批次**（棒-66c 货源探测，2026-09-26 09:24 CST，B 机；该批日志是配方定稿前的中间产物、
**未随包交付**）：上面第一行由 `~/tmp/uc2/03-pf7-download.sh:31-32` 的
`curl -sS -o pmars-0.9.5.zip -w "HTTP=%{http_code} SIZE=%{size_download} TIME=%{time_total}" -D "$LOGDIR/pmars-zip-headers.txt" <官方 zip 址>`
产出。`SIZE=243479` 另有独立载体 `~/tmp/uc2/棒-66c-pmars/pmars-zip-headers.txt`（`:1` =
`HTTP/1.1 200 OK`、`:7` = `Content-Length: 243479`）；sha256 另存
`~/tmp/uc2/棒-66c-pmars/pmars-0.9.5.zip.sha256`（与本节同值）。**同一条命令回显的耗时读数
（`TIME=…s`）、上面那段 `href` 目录页清单与"HEAD 采样 3/3"都没有留档载体**，故只算过程记录、
不进证据链；sha256 的交付面证据是**构建主机侧日志** `reports/conan-create.log:88`（该文件命中框架 `.gitignore`、本仓常态不入库，行号指构建主机留档件；conan 自行下载并校验通过）。
站点在探测期间可达（HEAD 采样 3/3 均 HTTP=200；同上，该读数无留档载体）。

zip **没有公共顶层目录**，解出来直接是 `src/ doc/ config/ warriors/ AUTHORS CONTRIB
COPYING ChangeLog README`。因此配方里 `get()` 不能用 `strip_root=True`，必须
`destination=self.source_folder`。格式声明的**实物口径**：`tar_format: zip` 只写在**版本级**
`manifest.yaml:13`（归档元数据）；`conandata.yml` 的 `sources` 只有 `url` 与 `sha256` 两枚键、
**没有 `tar_format`**（见 `conandata.yml:16-18`），解压由 `get()` 按 `.zip` 后缀自行识别——
`reports/conan-create.log:88` 下载校验通过、`:90 Unzipping 757.4KB` 就是"确实走 zip 路径"的实物证据。

### 1.2 版本串 = 0.9.5（三处独立互证）

| 依据 | 原文 |
|---|---|
| `ChangeLog:1,3` | `:3` 原文 = 制表符 + `- Release 0.9.5`；日期 `2026-01-03`、作者 `John Metcalf`、邮箱 `digital.wilderness@googlemail.com` 三个字段都在 `:1`（制表符分隔），`:2` 是空行 ⇒ 承重串 `Release 0.9.5` 落在 `:3` |
| `doc/pmars.6:29` | `.TH PMARS 6 "January 3, 2026" "PMARS v0.9.5"` |
| `src/global.h:130` | `#define PMARSVER  95` |

运行期另有两处（见 §6）：banner 打印 `pMARS v0.9.5, 03/01/2026`、`-Q 1000` 退出码 95。
归档目录 `archives/p/pmars/0.9.5/`、`conanfile.version`、分支 `feat/pmars-0.9.5`
与任务版本串完全一致，未做"归一化"。

⚠️ `README` 首行写的是 `README for pMARS version 0.9.0` —— 这是**上游自己没更新的
陈旧文本**（同一棵树里 ChangeLog/man/宏都已到 0.9.5），不作为版本依据，也不据此改版本号。

---

## 2. 构建系统：四个 makefile，为什么驱动 `Makefile.clang`

`src/` 下有 `Makefile`（generic UNIX）、`Makefile.clang`、`Makefile.djg`（DOS/DJGPP）、
`Makefile.wat`（Watcom）。目标集只有 `all / flags / clean`（**没有 install**，也**没有
check/test**）。

选 `Makefile.clang` 的两条硬理由，都来自读源码：

1. **它的 `CFLAGS` 是普通赋值** `CFLAGS = -DEXT94 -DPERMUTATE -DRWLIMIT`，可被 make
   命令行整体替换；而 `src/Makefile` 写的是 `CFLAGS += -O -DEXT94 -DXWINGRAPHX ...`，
   make 命令行变量只能**追加**、无法移除 `-DXWINGRAPHX`。
2. **它完全不碰 X11**；`src/Makefile` 硬编 `LIB = -L/usr/X11R6/lib -lX11`。

其余要点：`sim.o` 的依赖行 `sim.o: curdisp.c uidisp.c lnxdisp.c xwindisp.c` 揭示上游
用 `#include` 把显示模块折进 `sim.c`（`sim.c:53` include `curdisp.c`），所以显示模块
没有独立 .o——四个 makefile 都这么写，与选哪个无关。设备侧 `GNU Make 4.4.1`。

---

## 3. 显示层：X11 怎么"编译期关掉"，以及为什么 OHOS 要关

`src/config.h` 把**所有**显示/形态开关都留在 `/* */` 注释块里（GRAPHX、SERVER、SMALLMEM、
EXT94、KEYPRESS、BSD44、XWINGRAPHX、`__linux__` 全部是被注释掉的 `#ifndef/#define/#endif`），
只有 `HAVE_UNISTD_H`、`HAVE_USLEEP`、`PMARSLANG` 等是生效的。⇒ **显示层完全由 CFLAGS 决定**，
关 X11 的动作就是"不定义 `-DXWINGRAPHX`"，既不改源码也不引入平台宏（R8/PF5 合规）。

为什么在 OHOS 上必须关 X11：`-DXWINGRAPHX` 会拉 Xlib（`xwindisp.c`/`xgraphio.c`），
链接期需要 `-lX11` 与 `/usr/X11R6`，而 HarmonyOS PC 不给原生 CLI 包提供 X 显示服务；
反过来终端面是有的（pty 在设备上实测可用）。所以本包发布 **curses 显示变体**
（`-DCURSESGRAPHX`），把 X11 变体留在编译选项之外。

生效编译集（与配方 build() 逐字一致）：

```
-O -DEXT94 -DCURSESGRAPHX -DPERMUTATE -DRWLIMIT
```

`config.h` 的自洽逻辑保证 `-DCURSESGRAPHX` 蕴含 `GRAPHX`：

```
#if (... || defined(CURSESGRAPHX) || defined(XWINGRAPHX))
#ifndef GRAPHX
#define GRAPHX
#endif
#endif
```

---

## 4. 症状 → 根因 → 最小复现（真正的适配点）

### 4.1 opaque WINDOW 结构：5 处直接读字段

**症状**（第一次探索编译，构建主机，RC=2）：

```
In file included from sim.c:53:
./curdisp.c:464:26: error: incomplete definition of type 'struct _win_st'
./curdisp.c:465:36: error: incomplete definition of type 'struct _win_st'
./curdisp.c:466:33: error: incomplete definition of type 'struct _win_st'
./curdisp.c:468:24: error: incomplete definition of type 'struct _win_st'
./curdisp.c:480:36: error: incomplete definition of type 'struct _win_st'
make: *** [<builtin>: sim.o] Error 1
```

**根因**：`curdisp.c` 直接读 `WINDOW` 的内部字段 `curwin->_curx` / `curwin->_cury`，而
**本仓制品 `ncurses/6.6` 是不透明发布**——它包内 `include/curses.h:152` 就是
`#define NCURSES_OPAQUE 1`，`:456` 只有 `typedef struct _win_st WINDOW;`（前向声明、无成员），
字段 `_cury,_curx` 被关在 `#if !NCURSES_OPAQUE` 的块里（`curses.h:505/510`）。
上游 pmars 写于 ncurses 5 时代。
⇒ **触发面锚在"链到本仓这枚 ncurses/6.6 制品"上，不是 OHOS 平台能力问题**：这条是纯编译期类型
可见性，碰不到 syscall / ioctl / 设备节点，在任何 `NCURSES_OPAQUE=1` 的 ncurses ≥6（含普通 Linux
发行版）上都会报出同一签名 ⇒ 属上游与 ncurses 6 的**通用兼容修复**，不得叙述成"鸿蒙特有/OHOS
独有能力面"（见 §6 末段与本包知识草稿
`knowledge/drafts/DRAFT-pmars-0.9.5-ncurses-opaque-window-direct-field-read-needs-public-accessors.md`
的「边界（这条不是什么）」节）。

**最小复现**（不依赖 conan，纯 make）：

```
make -f Makefile.clang -j1 CC=clang CPPFLAGS=-I<ncurses>/include \
  CFLAGS="-O -DEXT94 -DCURSESGRAPHX -DPERMUTATE -DRWLIMIT" \
  LDFLAGS=-L<ncurses>/lib LDLIBS=-lncursesw
```

### 4.2 最终方案：改用公共访问器（不是关不透明开关）

`libncursesw.a` 里 `getcurx()`/`getcury()` 是**真函数**（不是只在非不透明构建下才有的宏）：

```
curses.h:923  extern NCURSES_EXPORT(int) getcurx (const WINDOW *);   /* generated */
curses.h:924  extern NCURSES_EXPORT(int) getcury (const WINDOW *);   /* generated */
$ nm -g --defined-only libncursesw.a | grep -w 'getcury\|getcurx'
00000000000031d8 T getcurx
000000000000322c T getcury
```

补丁 `patches/0001-curdisp-opaque-window-accessors.patch` 把 5 处直接字段读改成
`getcurx(curwin)` / `getcury(curwin)`。这个方向不是我们的偏好而是**上游自己的写法**：
同一函数里第 478 行本来就用同类公共宏 `getyx(curwin, oy, ox)`（`curses.h:1181` 把 `getyx`
定义成调用 `getcury()/getcurx()`），那 5 处是漏改的遗留。

改完 5 处（BSD44 段的 `#define _curx curx` 是无害别名，不动）后编译链接一次通过：

```
BUILD2_RC=0
-rwxr-x--- ... 551360 ... pmars
```

**载体与批次**（棒-66c 手工最小复现，2026-09-26 09:36 CST，B 机；配方定稿前、**未随包交付**）：
`BUILD2_RC` 由驱动脚本 `~/tmp/uc2/08-explore2.sh:53` 的 echo 回显，该轮 stdout 未单独留档；
链接段原文在 `~/tmp/uc2/棒-66c-pmars/explore-build2.log`（末两行是那枚 clang 链接命令，全日志
`error:` 计数为 0）；`551360` 是那次产物的大小，**当场可复算**——
`wc -c ~/tmp/uc2/pmars-explore/src/pmars` = 551360（该文件 mtime 2026-09-26 09:36）。
本节只是"改完能编过"的早期结论，交付面的编译证据在**构建主机侧日志** `reports/conan-create.log:102`–`:561`（该文件不入库，行号指构建主机留档件）。

**可复现性验证**：在 pristine 副本上 `patch -p1` 干净命中（2 个 hunk），再从零重建成功；
即配方从官方 zip + 本补丁可完全自包含构建。

### 4.3 链接库名：必须 `-lncursesw`

制品仓 `ncurses/6.6` 包内 `lib/` 实测只有宽字符静态库：

```
libformw.a  libmenuw.a  libncurses++w.a  libncursesw.a  libpanelw.a  pkgconfig  terminfo
find <pkg> -name 'libncurses*.a'  -> libncurses++w.a、libncursesw.a（没有 libncurses.a）
find <pkg> -name '*.so*'          -> 空
```

⇒ 没有 `libncurses.a`，`-lncurses` 在此包上不可能成立；本配方按发布件实际形态取
`-lncursesw`（与本仓 `aeolus/0.10.4` 对 `libncursesw.a` 的处置一致）。
因全部是静态库，产物不再动态依赖 ncurses——`readelf -d pmars` 实测：

```
0x0000000000000001 (NEEDED)  Shared library: [libc.so]
NEEDED 中 ncurses 计数 = 0
```

---

## 5. 运行期依赖：`requires("ncurses/6.6", run=True)` 是承重的

这一条不是"防御性写法"，实测两边都拍过：

- **有** ncurses 的 runenv（`TERMINFO`/`TERMINFO_DIRS` 指向包内 terminfo）：
  `pmars -b -r 1 -s 8000 -c 500 sonofvain.red excalibur.red </dev/null` → **rc=0**，
  输出 `Results: 0 0 1` 与两行 `scores`。
- **没有**（只留 `TERM=xterm-256color`）：**rc=1**，第一条错误原文
  `ncurses: cannot initialize terminal type ($TERM="xterm-256color"); exiting`。

机制：设备上的 `/usr/share/terminfo` 只有 2 项（其中有 `x/xterm-256color`），但发布件
ncurses 编译期内置的 terminfo 搜索路径不指那里，它自带的库在包内 `share/terminfo`；
`archives/n/ncurses/6.6/conanfile.py:406-407` 正是用

```python
self.runenv_info.define_path("TERMINFO", terminfo)
self.runenv_info.define_path("TERMINFO_DIRS", terminfo)
```

把这两个变量交付给消费者。而 conan 只在依赖带 **run=True** 时把 runenv_info 纳入
运行环境，所以本包必须写 `self.requires("ncurses/6.6", run=True)`。
（同族先例：本仓 presage 因运行期装载判错而恒红——`tool_requires` / 不带 run 的
`requires` 都不解决运行期。）

边界说明：终端用户**不经 conan 运行环境**直接执行 `pmars` 时，需要自行给出
`TERMINFO`/`TERMINFO_DIRS`，否则会看到上面那条 rc=1。装配类操作（`-A`）与
`-Q` 探针不初始化 curses，因此不受影响。

---

## 6. OHOS 行为观察（实测面）

| 面 | 实测结论 |
|---|---|
| 终端/pty | pty 可用（`pty.fork()` + `os.execve` 起真终端能跑 curses）。curses 对战在 pty 下输出 5605 字节真实画面，含屏幕切换/复位序列（`\x1b[H`、`\x1b[?1049l`）与颜色属性序列。**载体与批次**：`~/tmp/uc2/ascii-p12.log:6` 原文 `PTY_BYTES=5605`，由探针 `~/tmp/uc2/12-pty-probe.py` 于棒-66c 探测批次（2026-09-26 09:44 CST，B 机）产出；该批日志未随包交付，本数字只作行为观察、不进任何门禁判决 |
| 无终端也能初始化 | 只要 terminfo 可解析，stdout 不是 tty 时 curses 仍初始化成功：`...</dev/null >/dev/null 2>&1` → rc=0（CI 抓日志的场景因此可测） |
| 终端尺寸 | `COLS/LINES` 路径正常（画面按 80x24 渲染，状态行落在第 24 行；未见因尺寸取不到而崩） |
| 交互阻塞点 | ⚠️ 上游在显示结束后打印 `Press any key ..` 并等按键：接 pty 而不应键 → 进程不退出（本仓第一次 pty 探针就因此挂住，改 `select` 有界读 + 补发回车才拿到结论）。测试口径统一用 `</dev/null`，此时 `wgetch()` 立即返回 ERR、流程正常走完 |
| 信号 | 未改上游行为：`pmars.c` 里 `signal(SIGINT, sighandler)`/`SIGTSTP` 装配正常；curses 变体未定义 `KEYPRESS`（`config.h` 里该开关也仍是注释态，且 `curdisp.c` 的 KEYPRESS 分支要求 `SYSV && KEYPRESS`），故不走 `wgetch` 抢中断那条路。本包**没有**观察到 SIGHANDLER 类 EPERM 症状，也不需要禁用 |
| 进程/内存 | 未撞到平台限制：纯用户态模拟器，`-s 8000 -c 800` 级别对战在 8 核/31G 机器上瞬完；无 fork/exec、无裸设备访问 |
| 无 FHS 解释器 | 本包**不装任何脚本**（产物只有 ELF `pmars` 与数据文件），因此不触碰 `/bin/bash`、`/usr/bin/python3` 缺失那条 ENOENT 陷阱 |
| `/tmp` 只读 | 未触发：配方与测试的中间文件都落 conan 自己的构建目录 |

**没有观察到的**（明确留白，不编造）：`SCHED_FIFO`、`timerfd`、`/proc/net/tcp`、`/dev/vcs*`
这些面本包代码路径完全不涉及。

**OHOS 特有面到底有哪几条**（W4 r1 后收紧口径）：本包真正 OHOS 特有的只有两条——
① **X11 只能编译期关闭**（§3：`src/config.h` 的开关全在 `/* */` 里、`src/Makefile:22` 写的是
`CFLAGS +=`、`:26` 硬编 `-L/usr/X11R6/lib -lX11`，命令行只能追加不能移除，故必须改驱动
`Makefile.clang`）；② **运行期 terminfo 需要 `requires("ncurses/6.6", run=True)`**（§5）——
该条本仓已有 presage 先例，**不申报成新知识**。其余都不算平台特有：§4.1 的 opaque WINDOW
锚在本仓制品 `ncurses/6.6`（`curses.h:152` 即 `#define NCURSES_OPAQUE 1`）上，任何
`NCURSES_OPAQUE=1` 的 ncurses ≥6 Linux 同样会报，是上游与 ncurses 6 的通用兼容问题；
"zip 无公共顶层目录"是**上游发布形态**（§1.1），"制品只发宽字符静态库故用 `-lncursesw`"
是**本仓依赖制品形态**（§4.3），两者都与 OHOS 无关。除此之外**没有其它 OHOS 特有症状**。

---

## 7. 已试过 / 已排除的方案（含未采用的原因，如实标注）

**真跑过并失败/否决的：**

1. `ohc-run.py init-build pmars 0.9.5 --url=... --tar zip --auto` → **崩在框架**：
   `scripts/ohc/check_env.py:33` `except Exception:` 未接 `as e` 却 `return False, str(e)`
   ⇒ `NameError: name 'e' is not defined`。触发链是设备事实：`~/usr/local/bin/automake`
   存在但其 shebang 是 `#!/storage/Users/currentUser/usr/local/bin/perl`，而那个 perl 不存在
   （真 perl 在 `/data/service/hnp/bin/perl`）⇒ 执行 `automake --version` 抛
   `FileNotFoundError`。`check_env()` 只被 `init_build.py:543` 调用，所以
   `conan-init / conan-verify` 不受影响。**不改 harness**（红线），改走
   `conan-init` 直接生成配方。⚠️ 需要单独一条框架 PR。
2. `conan-init` 自动产的首稿按 `build.system: autotools` 生成（脚手架 manifest 是模板），
   与实际的 bare makefile 不符 ⇒ 手工重写，并按 §3 定编译集。
3. 用 `src/Makefile` 驱动、命令行覆盖 `CFLAGS`：**否决**——`CFLAGS +=` 使命令行只能追加，
   `-DXWINGRAPHX` 与 `-lX11` 去不掉（见 §2）。
4. pty 探针无界 `os.read()` → **挂住**（`Press any key` 等键），改有界读才拿到结论（§6）。

**评估后未采用（未跑，不冒充实测）：**

5. `-DNCURSES_OPAQUE=0`：可让 `curses.h` 露出字段从而"零改源码"编过，但它把配方绑在
   ncurses 头文件的内部宏约定上，而 `getcurx()/getcury()` 在 ncurses 5/6、不透明与否下都
   是稳定公共 API，且正是上游自己同函数里已用的路子 ⇒ 选补丁方案。
6. 把 `warriors/validate.red`（上游 Mark Durham validation suite）的行为级结论
   （"合规则自和局、不合规则自杀"）纳入 CI 断言：**不纳入**——单战士模式下上游不打印
   `Results:` 行（实测只有 `Validate 1.1R by Stefan Strack scores 0`），机器判据不确定，
   只作已观察行为留档，不计入通过数。

---

## 8. 测试口径（两套数字，不混用）

**上游官方完整测试**：**0 个**。证据（静态全量清点，非推断）：
`find . -name 'Makefile*' -exec grep -Hn "^check\|^test\|check:" {} \;` 输出为空
（5 个 makefile 全无 check/test 目标），`test -d tests` 不存在，**上游原始**源码树共 68 个文件、
顶层目录只有 `config/ doc/ src/ warriors/`。**68 的口径**（棒-66f 复验批次 2026-09-26 10:14 CST）：
`find` 在实际被扫的那棵 conan 工作树上原始输出是 **69**——多出的 1 枚是 conan 经
`export_conandata_patches()` 注入的 `patches/0001-curdisp-opaque-window-accessors.patch`，
因此那棵树的顶层另有 `patches/`；68 = 排除 `patches/` 后的复算值
（`find $SRC -type f -not -path '*/patches/*' | wc -l`）。原文见
生成物 `reports/upstream-test-scan.txt` **按 §19 不随 PR、磁盘留档**，其 §0（`ls` 与 `find | wc -l` 得 69）与 §结论 5。 ⇒ `build()` 里**不**写 `make check`
（写了只会得 `No rule to make target 'check'`，那不是"测试通过"）。
本包如实标注"上游无成体系测试，消费者测试自建"。

**上游作者确实写的可执行断言 = 6 条**（战士内 `;assert`，由装配器求值）：

```
warriors/artofcorewar.red:6    ;assert CORESIZE == 8000
warriors/excalibur.red:5       ;assert CORESIZE == 8000
warriors/forgottenloreii.red:2 ;assert CORESIZE==8000
warriors/sonofvain.red:5       ;assert 1
warriors/sunset.red:2          ;assert CORESIZE==8000
warriors/validate.red:24       ;assert MAXLENGTH >= 90
```

五维账本（实测数字以 `reports/` 下 conan-verify 日志的 `SUMMARY:` 行为准）：

| 维度 | 上游 `;assert` | 消费者自建（test_package） |
|---|---|---|
| 静态总数 | 6 | 13 |
| 可执行数 | 6 | 13 |
| 实测通过 | 6 | 见日志 SUMMARY |
| 跳过 | 0 | 0 |
| 失败 | 0 | 见日志 |

机器可读探针（pmars 没有 `--version`，上游用退出码传值，源码注释
"return exitcode based on SWITCH_Q setting, useful mainly in scripts"）：

```
-Q 1000 -> 95     PMARSVER
-Q 1001 -> 2      VARIANT=2（pmars.c:349-357：GRAPHX→2 / SERVER→0 / 无显示→1）
-Q 1002 -> 184    95*10+2=952，退出码取低 8 位
-Q 1003 -> 4      sizeof(ADDR_T)=4，反证未开 -DSMALLMEM
```

消费者断言里含一条负控制（`-Q` 退出码 3 + `Number of errors: 1`），证明装配器真的在
求值 `;assert` 而不是忽略它；同时所有断言都按**绝对路径**执行包内二进制，避免
harmonybrew 里可能存在的同名二进制造出"本地全绿"假验证。

---

## 9. 打包内容与适用边界

包内布局：

```
bin/pmars                       唯一可执行文件（curses 变体）
res/warriors/*.red              6 只自带战士（含 validate.red）
res/config/*.opt                14 个 KotH 风格选项文件（实测 conan 只 copy *.opt，config 目录里另有 2 枚 *.mac 不随包）
res/doc/pmars.txt               上游手册正文
res/licenses/COPYING            GPL-2.0+
```

`package_info()`：`bindirs=["bin"]`、`resdirs=["res"]`，`libdirs/includedirs` 显式清空
（纯应用包，不导出库/头）。

适用边界：
- 支持的 os 仅 `Linux`/`OHOS`（`validate()` R32 写法，不写 `== "Linux"`）。
- 只走 `Makefile.clang`；不生成 install 补丁（上游本就没有 install 目标）。
- 显示形态 = curses。要 X11 形态的人需要另一份带 `-DXWINGRAPHX` 且制品仓有 X11 的构建，
  本包不提供、也不静默回退。
- 不经 conan 运行环境直接执行时需要自备 `TERMINFO`/`TERMINFO_DIRS`（§5）。

---

## 10. test_package 脚手架文件说明（棒-66f 收口时补，如实标注）

`test_package/CMakeLists.txt` 与 `test_package/test.c` 是本仓 test_package 脚手架的标准组成
（多数归档保留这一对文件），本包一并保留。**本条不申报跨仓计数**——tracked 文件数是基线
commit 的确定性函数，任何不指名该 commit 的全仓数字都不可复核，故 W4 r1 起把原先那两个
全仓计数删掉。留可复算口径给要用的人（自己跑、并写明当时 HEAD）：
`git ls-files | grep -c /CMakeLists.txt` 与 `git ls-files | grep -c /test.c`。
但**它们不参与本包的验证，也不贡献任何测试计数**：

- 本包 `package_type = "application"`，`package_info()` 显式清空 `libdirs`/`includedirs`
  ⇒ 没有可链接目标，`find_package(pmars REQUIRED)` 在本包上没有语义（无 CMake config 生成）；
- `test_package/conanfile.py` 的 `test()` 因此**不驱动 cmake**，而是
  `self.run('sh test_pmars.sh <包内绝对路径>/bin/pmars <包内>/res', env="conanrun")`；
- `conan create` 日志里 `======== Testing the package: Building ========` 段为空，即此事实的直接证据。

`test.c` 里只打印一行 `test pmars 0.9.5: OK`，不被编译、不被 ctest 调用，
MANIFEST.yml 的 `test_package_tests` 也只登记 `test_pmars.sh` 一个载体（13 条断言全部来自它）。
若审查判定应删除脚手架，`git rm` 这两个文件即可，不影响任何断言与计数。


---

**编译结束**: 2026-09-26 10:12:46 （取构建主机侧 reports/conan-create.log 的 mtime；本包盘上无 .ci-result.json，见下条）
**最终状态**: built

- 收尾块说明（收口窗 主理-74 实算，非转抄）：本包按 `--skip-finish` 收口，构建主机侧 `reports/conan-create.log`
  （621 行 / 39854 字节，`sha256sum` 实算 `979117370d719aa7387081d3dc37d1f177d792f080514b40f07ab65801bf7ca9`）属仓根 `.gitignore` 通配 `reports/` 排除范围、**不入库**；
  入库的可回读证据为 `reports/{conan-verify-report.md,test-report.md,upstream-test-scan.txt,audit-result.json}` 四件。
- W3 真跑锚（同一日志内，行号为该日志自身行号）：`Calling build(` 命中行 [102]；`Built package` 命中行 未命中；
  消费者测试汇总 `13/13` 命中行 [620]。
- 本包目录与仓根均无 `.ci-result.json`（实测 MISSING）⇒ 状态判定以 conan-verify 报告 `Verdict: PASS` 与本日志为准，⛔ 不虚构 .ci-result 读数。
