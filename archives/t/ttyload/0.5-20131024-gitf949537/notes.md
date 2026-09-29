# ttyload 0.5-20131024-gitf949537 适配笔记

> 构建主机：**B 机**（HarmonyOS aarch64，HongMeng Kernel 1.12.0，'uname -s' = 'HarmonyOS'）
> 配方：'ttyload/0.5-20131024-gitf949537'（上游 'Version' 文件实物内容 = **0.5.3**）
> 结果：'conan create' 全绿，test_package 4/4 断言通过

## 0. 这个软件是什么

终端里的负载均值曲线图。把 1/5/15 分钟系统负载画成一张随时间滚动的 ANSI 字符图。
**零外部依赖**：不用 curses、不用 ncurses、不用任何库，纯 libc + 直接写转义序列。
上游是 3 个 C 文件的手写 Makefile 工程：'ttyload.c' / 'archtest.c' / 'loader.c'
（'loader' 在 Makefile 里被注释掉，默认不建）。

## 1. 关键机制：架构目录白名单（这是本包的唯一硬障碍）

上游 Makefile 用内核自报的家门号去拼一个**目录名白名单**：

'''
ARCH = <反引号>uname -s | sed -e 's/ /-/g'<反引号>
OBJS = arch/${ARCH}/getload.o arch/${ARCH}/terminfo.o
'''

tarball 里 'arch/' 实物只有四个目录：**FreeBSD / IRIX / Linux / SunOS**（2013-10-25 原貌）。
B 机 'uname -s' = 'HarmonyOS' ⇒ 未改动的源码在 HarmonyOS PC 上**必挂**，实测第一条真实错误：

'''
$ make
make[1]: *** No rule to make target 'arch/HarmonyOS/getload.o', needed by 'archtest'.  Stop.
make: *** [Makefile:65: archbuild] Error 2
'''

### 为什么映射到 Linux 后端，而不是新写一份

不是"先试试再说"，是**逐个函数看过两个源文件的平台依赖面之后**判定的：

| 文件 | 全部平台依赖 | B 机实测 |
|---|---|---|
| 'arch/Linux/getload.c' | 只 'fopen("/proc/loadavg")' + 'fscanf("%f %f %f")' | '/proc/loadavg' 可读，值与 ttyload 自己报出的完全一致 |
| 'arch/Linux/terminfo.c' | 只 'ioctl(TIOCGWINSZ)' | 可调用；非 tty 时按上游逻辑返回 -1 行/列，不致命 |

而上游 Makefile 本来就为"平台之间互相模仿"准备了机制 —— 'ARCHLINKS'
（'arch/Darwin'、'arch/Isilon-OneFS' 就是这样 'ln -s FreeBSD' 得到的）。
所以补丁 **0001-Makefile.patch** 只做一件事，且完全走上游自己的路数：

'''
+ARCHLINKS_LINUX = arch/HarmonyOS
+$(ARCHLINKS_LINUX):
+       ln -s Linux $@
'''

+11/-0，不加新文件、不改算法、不用任何平台宏（PF5/R8 干净）。
'archlinks' 列表里把 Linux 系谱排在 'arch/thisarch' 之前，保证
'ln -s ${ARCH} arch/thisarch' 建出来的链接不是悬空的。

### 反证（为什么不选别的方案）

- 'make ARCH=Linux' 也能建出来，但它只对我们这条 conan 命令有效，别人拿 tarball
  直接 'make' 仍然挂；ARCHLINKS 补丁把修复留在源码里，一次修好。
- 手写 'arch/HarmonyOS/getload.c' = 把 Linux 那 64 行抄一份进补丁，凭空多 100+ 行
  双份维护；上游的 symlink 系谱机制存在的理由就是避免这个。

## 2. 工具链：'gcc' 在构建机上根本不存在

'Makefile:17' 把编译器写死成 'gcc -pedantic -Wall -Werror'。
B 机实测：'command -v gcc' / 'command -v cc' **全部为空**，只有
'/data/service/hnp/bin/clang'（OHOS SDK clang 15.0.4）。⇒ 不改 CC 连一步都走不下去。

CC 从 'self.conf' 的 'tools.build:compiler_executables' 取（**R33**：不裸用 shell 变量），
取不到再退到 'settings.compiler' 的名字。

### 关于 -Werror：只摘掉"把告警当错误"这一档，告警一条不少

实测 '-pedantic -Wall -Werror' 在本平台**必挂**，而且挂的原因不在我们身上：

'''
/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/../../sysroot/usr/include/sys/fcntl.h:1:2:
  warning: redirecting incorrect #include <sys/fcntl.h> to <fcntl.h> [-W#warnings]
'''

这条 '#warning' 是 **OHOS sysroot 自己的头文件**发出的，源码里没有任何办法消掉它；
'-Werror' 下它直接判死。另外 'ttyload.h:41' 的 'extern void gettermsize();'
（上游 1996 年的 K&R 声明）在 clang 15 下命中 '-Wstrict-prototypes'。

⇒ 处理：'OTHER_FLAGS="-pedantic -Wall -Wno-error"'。上游要的 '-pedantic -Wall'
**原样保留、每条告警照样打印**（实测 10 条全在日志里），只把 '-Werror' 降级。
这不是"放宽测试断言"，是把一个由平台头文件引起的构建档期问题如实降级，
并且降级理由与证据都留在 PR 与本文里。

### 一个 make 变量传参坑（实测踩到）

'Autotools.make(args=["OTHER_FLAGS=-pedantic -Wall -Wno-error"])' **不生效**：
conan 只是把 args 用空格拼成命令行交给 shell，不做转义，make 只收到
'OTHER_FLAGS=-pedantic'（实测编译行里 '-Wall -Wno-error' 消失）。
⇒ 带空格的值必须自带引号：''OTHER_FLAGS="%s"''。

## 3. install：不碰上游的 '/bin/cp' + 绝对路径

'Makefile:84-85' 的 'install:' 是 '/bin/cp ttyload /usr/local/bin/ttyload'。
'/usr/local' 字面量正踩 PF6/R49（禁止注入共享系统前缀）。
⇒ 'package()' 直接用 Conan 的 'copy()' 把 'ttyload' 放到包内 'bin/'，
'LICENSE' 放到 'licenses/'。上游本来也只 install 这一个文件，无库无头。

## 4. 上游测试（R51 三步法：清点 → 实跑 → 如实回填）

实物清点（24 个文件逐个扫过；口径 = 解包后普通文件数，6 个目录不计，'tar tzf' 条目共 30）：
没有 'tests/' 目录、没有 ctest/pytest、Makefile 里唯一的测试目标就是 'test'。

| 上游"测试" | 实物 | 能否原样跑 | 本次怎么跑 |
|---|---|---|---|
| 'make test' = './ttyload -i 1' | 交互式绘图 | **不能**：'ttyload.c:38' 的 optstring 是 'i:hvmr:c:'，**没有任何"跑 N 帧就退出"的选项**，作者文档写的是 "(Note: use ctrl-C to quit)"。裸跑会把构建机挂死 | 在 'test_package/test_ttyload.sh' 里执行**同一程序、另加 '-m' 单色选项**（实物 '"$BIN" -m -i 1 </dev/null'；'-m' = "monochrome mode (no ANSI escapes)"，'ttyload.c:45'），用"stdout 交给 head，读够 40 行 head 关管道 → ttyload 收 SIGPIPE 自然终止"的方式有界化 |
| 'archtest' | 上游自写的架构后端隔离自检程序（'archtest.c:2-4' 自述 "so that we can test those things in relative isolation"），有限运行 | 能 | 'build()' 里真跑，rc=0 |

台账（**合计口径**：build() 位点 1 项 + test_package 位点 1 项）：
'discovered=2, executed=2, passed=2, failed=0, skipped=0'。配方日志里以 'UPSTREAM_TEST_RESULT=' 机器可读行输出的是**另一个口径**（只算 build() 位点），实测 'executed=1, passed=1'（'reports/w3-local-ci.log:256'）⇒ 两口径**不可相加**，拆分见 §10.3。

### test_package 的 4 条断言（全部实测通过）

- **T1** 'ttyload -v' 输出含 'ttyload version 0.5.3'
  （注意：上游 '-v' 的实现是"打印版本后掉进 usage 分支并 exit(1)"，这是上游设计，
  所以只断言输出内容，不拿这条的退出码当判据）
- **T2** 'ttyload -h' 输出含 'Usage: ttyload'
- **T3** **实质证据**：真跑一次绘图，把标题行里 ttyload 报出的 1 分钟负载和
  '/proc/loadavg' 的第一列比对，容差 3.0。实测 'ttyload=21.53 / kernel=21.383'（在盘读数 'reports/conan-create.log:101-102'，本窗 §10.6 那轮重跑）
  → 证明"我们选的 arch/Linux 后端在 HarmonyOS 上真的取到了内核的负载数"，
  而不是把一个 0 或随机值画成图。
- **T4** ASCII 图真的被画出来：y 轴刻度行 33 行、含数据点 36 行、共 40 行。

## 5. 平台事实：'/proc' 访问是**按工具**不对称的（写测试脚本必踩）

B 机实测（同一个 '/proc/loadavg'）：

| 用法 | 结果 |
|---|---|
| 'cat' / 'head -1' / 'sed -n '1p'' / 'cut -f1 -d' '' / shell 'read < file' | **可以** |
| 'grep xxx /proc/loadavg' | 'Permission denied' |
| 'awk '{print $1}' /proc/loadavg' | 'awk: fatal: cannot open file ... for reading' |
| 'ls -l /proc/loadavg' | 'Permission denied' |
| 'test -r /proc/loadavg' | **返回"可读"（与实际可 open 不一致）** ——〔本行括注：此归因已被本文 §10.1 的 **32 行纯 libc 探针**否证，access 与 open+read 一致，真正相反的是 stat/lstat/fstat〕 |

⇒ 结论：SELinux 域内"**打开读内容**"和"**对同一 inode 做 stat/按常规文件处理**"
不是一回事。'awk'/'grep' 这类先 stat 再读的工具会碰壁，而 'test -r' 反而会误报可用。〔本句括注：此归因已被本文 §10.1 的 **32 行纯 libc 探针**否证，access 与 open+read 一致，真正相反的是 stat/lstat/fstat〕
本包测试脚本因此只用 'sed' + 'cut' 取 '/proc/loadavg'，
并在取空时**判失败而不是跳过**（这个软件本身依赖 '/proc/loadavg'，读不到就是适配没成，
不能当成环境噪声放过去）。

## 6. 版本串两种形态（不得归一化）

| 场合 | 形态 |
|---|---|
| 平台任务 / 登记表 / 归档目录 / conan 版本 | '0.5-20131024-gitf949537'（连字符）|
| tarball 文件名 / 解包后的顶层目录 | '0.5+20131024+gitf949537'（加号）|
| 上游 'Version' 文件 → '-DVERSION' 宏 → 程序自报 | '0.5.3' |

'get(..., strip_root=True)' 直接吃掉加号形态的顶层目录，所以配方里不出现解包目录名；
归档目录与 conan 版本保持平台侧的连字符串。

## 7. 取源

'https://deb.debian.org/debian/pool/main/t/ttyload/ttyload_0.5+20131024+gitf949537.orig.tar.gz'
sha256 '2c07532785fbf87895111b69bfec70adc8913855bdc025a57582da0cfefea82b'（B 机对下载件实测一致）。

- 上游主页 'http://www.daveltd.com/src/util/ttyload/' 是明文 http 且 2013 年后不再发布 tarball；
  GitHub 'lindes/ttyload' 只有 git 快照、无对应本版本的 release tarball。
- Debian 的 '.orig.tar.gz' 是**未经改动的上游原始源码包**（不是 dfsg 重打包），
  解包实物 24 个普通文件（6 个目录不计）与 git 'f949537' 一致。
- 本仓同形态先例：'archives/c/chrpath/0.18'、'archives/b/blockdomains/0.1'、
  'archives/a/audtty/0.1.12'（后者用 ftp.debian.org 的 .orig）。

⚠ **需要登记的一条口径冲突**：本 worktree 的框架侧静态检查
'scripts/ohc/preflight.py' 的 **PF7 源 URL 闸**把 'deb.debian.org' 一律判为
"Debian 下游重打包源"（无 '.orig.tar.gz' 例外分支）。PF7 挂在
'ohc-run.py submit' 的 create-pr 咽喉点上，而 CI 侧 'build_and_test.sh' 的
L0 检查**不含**该规则 ⇒ CI 不受影响。本包按主窗给定的取源与上述先例执行，
并把该冲突如实留档，交主窗判断是否走"官方托管例外 + PR 说明"。

## 8. 遗留 / 未做

- 'Jamfile'（上游的第二套构建入口）与 'loader.c'（被注释掉不建）本次不动、不验证。
- 'arch/default/' 在 Makefile 的 '-I' 里被引用，但 tarball 里**根本没有这个目录**
  （gcc 对缺失 -I 静默忽略）—— 上游死引用，不属本包问题，未改。
- 交互式行为（resize 跟随、时钟条）无法在非 tty 下验证；'archtest' 在无 tty 时
  报 'termsize: -1 rows, -1 cols' 属上游既有逻辑。
## 9. 路径 B 知识贡献（3+2 声明）

- **适配路径**：路径 B（知识库扩展）——新增「HarmonyOS PC 上 /proc 单文件按 syscall 粒度受限」机制草稿：
  /proc/loadavg 与 /proc/uptime 允许 open()+read()，却对 stat()/lstat()/fstat() 返回 EACCES(13)，
  凡「先 stat 再读」的工具（GNU grep 3.12 / gawk 5.4.0 / ls / stat）都在**确实可读**的文件上报 Permission denied
- **使用知识库**：复用 E008/E076/E161（fstat/lseek 族）、E009（SELinux 域转换）、E031/E324/E429（/proc 与指标降级族）；
  新增 knowledge/drafts/DRAFT-ttyload-0.5-20131024-gitf949537-harmonyos-proc-stat-denied-read-allowed（同 stem .kv/.md 成对）
- **知识库扩展**：上述 1 条 —— 15 路径 × 6 syscall 实测矩阵 + 两条阴性对照（同一 GNU 二进制经 stdin 可读、
  在 stat 被允许的 /proc/stat 上以文件参数也可读），并给出「取 /proc 值一律走 open+read、C 侧不得用 stat/fstat 门控 open」的可复用纪律
- **关联 Issue**：#3500（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3500）（标题与本条机制同一表述、Issue 侧略去细节故非逐字；正文含 32 行探针读数（3992 为 UTF-8 字节数）、两条阴性对照、与 E031/E161/E008/E076/E324 的层次差 ⇒ 2026-09-27 04:59 已 PATCH 该计数并由主窗 GET 回读 body_len=3992 逐字一致）
- **PR 前缀**：【知识库扩展】

## 10. 棒-2 复核（2026-09-27 03:00–03:20，第二棒 / B 机；只增不改，上文原样保留）

### 10.1 §5「/proc 按工具不对称」的结论更正

§5 的现象记录全部复核成立（cat/head/sed/cut 可、grep/awk 不可、ls -l 不可、test -r 说"可读"），
但**归因要反过来写**：32 行纯 libc 探针（同一进程、同一凭据、逐路径 stat/lstat/access/open/read/fstat）实测

    /proc/loadavg  stat=FAIL/13 lstat=FAIL/13 access=ok/0 open=ok/0 read=33/0 fstat=FAIL/13
    /proc/uptime   stat=FAIL/13 lstat=FAIL/13 access=ok/0 open=ok/0 read=19/0 fstat=FAIL/13
    /proc/stat     stat=ok/0  lstat=ok/0  access=ok/0  open=ok/0  read=63/0  fstat=ok/0

⇒ ①**access() 与 open()+read() 是一致的**（都说"可读"），§5 说 test -r「与实际可 open 不一致」不成立；
真正与事实相反的是 stat/lstat/fstat。②被判拒的是 **getattr 这一权限位**，不是"这个路径不可读"：
对**已经 open 成功的 fd** 调 fstat 仍 EACCES，而 read 正常。③工具相关性是派生现象：
GNU grep 3.12 / gawk 5.4.0 对文件参数先 stat 预检 ⇒ 失败；toybox grep、toybox awk、busybox grep 不做该预检 ⇒ 成功。
两条阴性对照排除"进程域/凭据"解释：`cat /proc/loadavg | grep -c .` rc=0、`grep -c . /proc/stat` rc=0（同一 GNU 二进制）。
⇒ §5 的落地纪律（测试脚本只用 sed + cut 取 /proc 值、取空判失败）**保持不变、仍然正确**；
本窗把它连同证据写成路径 B 草稿（§9）。探针与日志：~/tmp/uc2/z75w-ttyload/probe2.c、
probe-proc-syscall.log、probe-proc.log。

### 10.2 三条机制复核（行号为 tarball 实物，构建树 ~/tmp/ch/home-ttyload/p/b/ttylo3ca8cf8bbea2d/b）

- 机制①架构目录白名单：'Makefile:9' ARCH 取 uname -s、':12-13' OBJS、':20-22' INCLUDES 全部指向 arch/${ARCH}；
  'arch/' 实物只有 FreeBSD / IRIX / Linux / SunOS 四个真目录。补丁 0001 实测：新增 'ARCHLINKS_LINUX = arch/HarmonyOS'
  （打后 ':53-55'）、规则 `$(ARCHLINKS_LINUX): ln -s Linux $@`（':67-68'），且 `$(ARCHLINKS_LINUX)` 排在
  `$(ARCHLINKS_THISARCH)` **之前**（':57-61'）⇒ 建链顺序正确，走的就是上游给 Darwin/Isilon-OneFS 用的同一机制。
  构建树实测 `ls -l arch`：`HarmonyOS -> Linux`、`thisarch -> HarmonyOS`、`Darwin -> FreeBSD`、`Isilon-OneFS -> FreeBSD`，
  四个链接目标全部在盘（`arch/Linux/getload.c:1` 定义 LOADFILE "/proc/loadavg"、`:26` 直接 fopen 不 stat；
  `arch/Linux/getload.o` 已产出）⇒ **无悬空链接、+11/-0、无平台宏**（PF5/R8 干净）。
- 机制②gcc 字面量：实物在 'Makefile:17'（§2 正文写的 ':17' 正确；任务转述里的"第 6 行"是 INSTALLDIR 那行，特此校正）。
  B 机复核：`command -v gcc` 与 `command -v cc` 均空，`/data/service/hnp/bin/clang` 存在；
  配方 CC 走 `tools.build:compiler_executables` 解析（R33），未裸用 shell 变量 ✓。
- 机制③：见 §10.1 与 §9 草稿（本窗选它作 B 交付物，理由：平台行为、与 ttyload 无关、任何读 /proc 的库都会撞，
  且证据是 32 行零依赖探针 + 两条阴性对照，任何窗口可在任一台 HarmonyOS PC 复算）。

> **⚠ 本包 `reports/` 下全部文件不随 PR（`review-memory §19` `*.log` 禁入 + 生成物不入库，2026-09-29 按审查意见删除）**：
> `conan-create.log` / `conan-verify-report.md` / `w3-local-ci.log` / `w4-report.log` / `z75j-audit-result.json` / `z75j-w4-report.log` / `z75o-audit-result.json` **7 件已 `git rm --cached`、磁盘原件保留**（`<worktree>/archives/t/ttyload/0.5-20131024-gitf949537/reports/`）；**随 PR 的 `reports/` 件 = 0**。
> ⇒ 下文所有 `reports/...` 行号坐标（`:256`、`:101-102`、`:101`、Verdict `:3` 等）**按本机现件核**、**关键读数已逐条内嵌本节**，读者不依赖这些文件在库；判决结论以 `.json` 同内容的文本摘录与本节为准。

### 10.3 上游测试账本（五维拆开；对 §4 台账的复算结论）

| 维度 | 数 | 口径 |
|---|---|---|
| N_static | 2 | 上游**测试资产/入口**清点：`Makefile:37-38` 的 `test:` 目标（实体只有一条命令 `./ttyload -i 1`）+ `archtest` 自检程序（`archtest.c:12-29`） |
| N_registered | 1 | `test_package/MANIFEST.yml` 注册的消费者测试 `test_ttyload.sh`（CI L0e 认这一项） |
| N_executed | 2 | `build()` 裸跑 `./archtest`（rc=0）+ `test_package` 有界执行 `ttyload -m -i 1` 一次 |
| N_consumer | 4 | 断言 T1(-v) / T2(-h) / T3(与 /proc/loadavg 比对) / T4(ASCII 曲线)，被测二进制实际被调用 3 次 |
| N_runner | 2 | 执行位点：conan `build()` 与 `test_package test()`；上游 runner `make test` **未**以 make 目标形式跑过 |

⇒ 对 §4 那句 `discovered=2, executed=2, passed=2, failed=0, skipped=0` 的复算结论：
**"2" 只能是"测试资产 2 个"，不是"用例 2 个"** —— `make test` 内部 1 条命令、**0 条断言**
（`ttyload.c:38` 的 optstring 是 `i:hvmr:c:`，无迭代上限；`:54` usage 自述 "(Note: use ctrl-C to quit)"）；
`archtest` 的非零退出全部来自 `arch/Linux/getload.c`：`:29`（fopen 失败）、`:37`（fclose 失败）、`:62`（fscanf 返回 0）三处 `exit(1)`；`:23` 另有 `exit(2)`，只在调用方传空 `loadavgs` 指针时触发，`archtest.c:19` 传的是 `&loads` ⇒ 不可达。`return(0)` 恒定，
等价于 1 条「能 open 并读出 /proc/loadavg」的断言。conanfile 里 `UPSTREAM_TEST_RESULT` 记的
`discovered=2/executed=1/passed=1` 是**只算 build() 位点**的资产数，与 §4 的合计口径不同、**不可相加**。
`make test` 未原样跑这一点，§4 表格已如实写明，本窗维持"有界复现同一程序（加 `-m` 单色选项）+ 4 条内容断言"的取证强度，
未放宽任何断言；终端交互能力受限项（resize 跟随、时钟条、非 tty 下 termsize=-1）仍按 §8 逐项说明，
不计入 skipped（实跑的 2 项资产全部通过）。

### 10.4 门禁复跑读数（本窗，B 机 2026-09-27）

- `preflight_check.sh ttyload/0.5-20131024-gitf949537`：rc=0，`[OK] 预检通过（无依赖需要检查）`（~/tmp/uc2/z75w-ttyload/preflight.log）
- `ohc-run.py conan-verify`：rc=0；三一致齐 —— 日志 G1/G0/G2/G3 全 PASS + `✅ 配方验证通过` + `可标记 published`，
  报告 `**Verdict**: PASS`（件内 `**Date**` 现为 `2026-09-27T04:16:53.531230`，该件已被 §10.6 那轮重跑重写）。
  ⚠ 棒-2 当初把此句写成"G4/L2/L4/L5 全 PASS"不确：那四节是**标题 ✅ + 正文 ⚠️/⏭️** 的相反态，
  实际覆盖 G0 预检 + G1 结构 + G2 干净构建 + G3 隔离，G4 未取到程序包 ID、L2/L4/L5 跳过（逐行读数见 §10.6）。
  槽位：机动 1/3、长杆 0/2，gate --light 通过后才起构建。
  ⚠ G0 附带提示「已知风险 E490 未在配方中处理」（Autotools 脚本可执行位）—— 本包无 configure/autotools
  （纯手写 Makefile，`build_system: makefile`），判定不适用、未处理，如实留档。
- `ohc-run.py draft-review DRAFT-ttyload-...`：rc=0，质量预检 signature/root_cause/rec 三项 ✅，
  预审建议 `review-similar → E031`（灰区，纳入决策归人工/主编）；相似 TOP3 为 E031(0.36)/E161(0.24)/E008(0.22)，
  本窗已在草稿的「查重差异」里逐条给出行号级层次差，并与 E161 标为 **conflicts_with**（方向相反：E161 要"改管道为文件"，
  本机制上文件形态才是被拒的那一侧）。
- `conandata.yml` 复核（E017）：`git status` 未列该文件（与 HEAD 一致），`:14-15` 仍是官方
  `https://deb.debian.org/debian/pool/main/t/ttyload/ttyload_0.5+20131024+gitf949537.orig.tar.gz` 标量形态 +
  sha256 `2c07532785fbf87895111b69bfec70adc8913855bdc025a57582da0cfefea82b`；本窗 verify 那轮的镜像注入由框架自行回写并恢复
  （日志 `🧹 已清理陈旧 conandata.yml.ghfast-bak` / `🔄 已恢复原始 conandata.yml`）。`conandata.yml.ghfast-bak` 仍被 gitignore、未提交、未手删。
- `finish` / `graph validate`：见下一节（棒-2 第二段落盘）。

### 10.5 finish 与 graph validate 读数（棒-2，2026-09-27 03:27–03:35）

- `ohc-run.py finish ttyload 0.5-20131024-gitf949537 built`（先过 `gate.sh --light`，走机动槽 short）：
  收尾块 `EXIT_REASON: finish_success / EXIT_CODE: 0`，但**外层 rc=2**，失败步骤 = step5b + step8；
  这两项在上一棒的 finish 日志（`~/tmp/uc2/z75y-ttyload/finish.log`）里同样失败，属**既有问题**、非本窗引入：
  · step5b 是 submit 就绪预检缺 `reports/test-report.md`、`packaging/`、`.staging-verified`；
  · step8 是框架自身异常 `gen_summary 失败: 'str' object has no attribute 'append'`。
  本窗另记两条观察，均**不改配方**、交主窗判断：
  ① Step3 的通用 clean-build-verify 报 `G0: configure 失败 (exit 127)` —— 上游没有 configure
  （纯手写 Makefile），框架按 autotools 模板试跑 `./configure` 必然 127；真正用于判定的 G0 在
  conan-verify 内部（✅ PASS，见 §10.4），且 G2 干净构建（补丁 + create）全绿。
  ② W5 报 `manifest.yaml: knowledge_count=8 unreferenced=8 / 存在知识遗漏` 与
  `知识整理未完成（缺少 .knowledge-done 标记）`，与上一棒同形；`.ci-result.json` 已刷新为
  `timestamp 2026-09-27T03:28:32 / exit_code 0 / integrity_hash 8cdeb70988d71deb` ⇒ `check` 前置可读。
- finish 写回复核：`manifest.yaml` 只改 `patch_generation` 的 work hash 与时间戳；`notes.md` 只更新页脚
  时间戳（`**最终状态**: built` 子串原样保留）；`conandata.yml` **未被改写**（`:14-15` 仍是官方
  deb.debian.org 的 .orig 标量形态 + sha256 `2c0753…`），`.ghfast-bak` 仍被 gitignore、未提交、未手删。
  ⚠ 一次自纠：本窗最初在 §10.4 里逐字照抄框架提示（含 status 冒号形态），被 finalize 的一致性检查
  当成 notes 状态、多报一条「状态不一致 vs manifest=built」（一致性问题 1→2）。已改写该行并复跑
  `finalize-archive` ⇒ 回到基线 **1 个一致性问题（notes.md 无对话记录，存量）+ 1 个缺失项
  （release/debug tar.gz，application 包本就不产）**，与上一棒基线一致。
- `ohc-run.py graph validate`：rc=0，`✅ All checks passed (169 warnings)`，540 kv / 540 md / 540 index 行；
  169 条全是存量警告（C13 长尾 category 词、C14 编号空洞 E429/E479），与本窗改动无因果关系；
  本窗新增草稿位于 `knowledge/drafts/`，不参与 graph validate（其预审走 `draft-review`，见 §10.4）。
  日志：`~/tmp/uc2/z75w-ttyload/graph-validate.log`、`finish-z75w.log`。
- 交回主窗的缺口清单（本窗**未**做，按分工不碰平台/PR/阶段）：Issue 号回填（主窗已完成：#3500，标题与正文经 GET 回读UTF-8 字节数一致（内容同一机制、措辞有详略，非逐字））、
  PR 标题/正文 3+2 同步、step5b 三项就绪预检、W4/W5 独立审计。

### 10.6 精修棒（z75s）W4 整改与门禁重跑读数（2026-09-27 04:05–04:25，B 机）

W4 独立审计对起点 HEAD `4ab05d4198f24f1324153a7d75a9e93c67d7e5c5` 判 P0=0 / P1=1 / P2=5 / P3=4。
本棒只改文字与自检模式，**不改 B 判定（create 维持）、不删草稿、不动 `~/tmp/uc2/z75w-ttyload/` 的探针证据**，
逐条处置与本窗复算读数：

- **P1**（本文 `:138`/`:141`）：不删旧文，两行行尾各加括注指向 §10.1 的 32 行纯 libc 探针否证结论。
- **P2-1**（optstring 行号 39→38）：本窗复算 tarball 实物 `ttyload.c:38` = `*optstring = "i:hvmr:c:"`、
  `:39` = `*usage =`、`:45` = `-m -- monochrome mode (no ANSI escapes)`、`:54` = "(Note: use ctrl-C to quit)"；
  改本文 `:110` 与 `test_package/MANIFEST.yml:25`（本文 `:242` 与草稿 `.md:233` 原本已是 `:38`）。
- **P2-2**（26 个文件→24）：本窗复算同一 tarball（sha256 `2c07532785fbf87895111b69bfec70adc8913855bdc025a57582da0cfefea82b`，
  与 `conandata.yml:15` 对字）：`tar tzf` = 30 条目、其中目录条目 6、解包后 `find -type f` = **24**（含 `arch/.README`）
  ⇒ 计数口径"按普通文件数、目录不计"，改本文 `:105`/`:165`、`MANIFEST.yml:17`、`conandata.yml:7`、`conanfile.py:116`
  （审计列 4 处；`conanfile.py:116` 是同串第 5 处，一并改，否则文内互斥）。
- **P2-3**（28 行→32 行）：`wc -l ~/tmp/uc2/z75w-ttyload/probe2.c` = **32**（非空行亦 32，sha256 `6e9c0df86b560cf5f1fca884cbc50f4873041b0147411754f40630a43788ae47`；
  旧版 `probe.c` = 33 行）⇒ 改本文 `:192`/`:200`/`:228` 与草稿 `.md:36`/`:76`（**实测共 5 处**，审计写的 6 处里
  `notes.md:212` 那行并无"28 行"字样）；草稿 `.md:176`（审计写作改前的 `:172`）的"框架草稿池 `knowledge/draft/` 1396+ 条"改实测对象：
  该目录只有 **2** 个文件（`DRAFT-duckdb-1.5.5-build-time-target-binary-platform-probe` 的 .kv/.md 成对，`git ls-files` 同 2），
  原"0 命中"结论不变（本窗 `grep -ril loadavg knowledge/draft/` 复算仍 0）。
- **P2-4**（T3 读数无源）：`21.08/21.083` 在盘无出处 ⇒ 换成本轮在盘读数并注明件名+行号（本文 `:123`、草稿 `.md:237-238`）。
- **P2-5**（"同一个命令"不实）：实物 `test_package/test_ttyload.sh:55` 是 `"$BIN" -m -i 1 </dev/null`（`-m` = 单色，`ttyload.c:45`）
  ⇒ 改为"同一程序 + `-m` 单色选项"，改本文 `:110`/`:246`、`conanfile.py:118-119`、软件级 `manifest.yaml:14`、软件级 `README.md:45`
  （审计列 4 处；`:246` 是同串第 5 处）；"上游 `make test` 从未以 make 目标形式跑过"的如实表述一字未动。
- **P3①**（`:113-114`）：合计台账与 `UPSTREAM_TEST_RESULT` 分句、各标口径（后者只算 build() 位点，现落 `w3-local-ci.log:256`）。
- **P3②**（`test_ttyload.sh:56`）：残留进程自检模式 `'[t]tyload -i 1'` → `'[t]tyload -m -i 1'`。**正向验证**（本窗 04:21，
  对包内产物 `ttyload -m -i 1` 常驻 2 秒后取 `ps -ef` 快照，件 `~/tmp/uc2/z75s-ttyload-fix/poscheck.out.txt`）：
  旧模式命中 **0**、新模式命中 **1**（快照行 `… ttyload -m -i 1`）、`kill` 后命中 **0** ⇒ 不再是死分支；
  本轮 W3 重跑里该自检未触发 WARN（`w3-local-ci.log:300-308` 四条 PASS 之间无 WARN 行）。
- **P3③**（`:243`）：补全 `arch/Linux/getload.c` 的三处 `exit(1)` —— `:29`（fopen 失败）、`:37`（fclose 失败）、
  `:62`（fscanf 返回 0）；`:23` 的 `exit(2)` 只在传空 `loadavgs` 时触发，`archtest.c:19` 传 `&loads` ⇒ 不可达。
- **P3④**：§10.4 的报告时间戳已换成件内读数（见该节），并在原处标注"标题 ✅ + 正文 ⚠️/⏭️"的相反态。

**门禁重跑**（`conanfile.py`/`conandata.yml` 注释与 `test_package/*` 都算构建输入面 ⇒ 旧 W3 证据作废，本窗重跑；
日志落 `~/tmp/uc2/z75s-ttyload-fix/`，与执行棒 `z75w-ttyload/`、审计棒 `z75x-ttyload-audit/` 隔离）：

- `gate.sh --light`：rc=0，`GATE_PASS:probe=clang MemAvailable=5608MB load=21.250 21.806 22.456 PSI_full=avg10=74.47`。
- `build-slot.sh --kind short --wait 1800 -- ohc-run.py conan-verify ttyload 0.5-20131024-gitf949537`：**rc=0**
  （`SLOT_OK 04:14:48`、`SLOT_DONE:ok MemAvailable=5623MB`；起建时机动 2/3、长杆 0/2）；三一致：日志
  `✅ 配方验证通过` + `可标记 published` + `reports/conan-verify-report.md` 的 `**Verdict**: PASS`（`:3`）。
  ⚠ **报告图标不可照抄**：`G4`（`:39-40`）标题 `✅ PASS`、正文 `⚠️ 无法找到程序包 ID`；`L2/L4/L5`（`:42-49`）
  标题 `✅ PASS`、正文 `⏭️ 跳过（无 cache 路径）` ⇒ **实际覆盖 G0 预检 + G1 结构 + G2 干净构建 + G3 隔离**。
- `build-slot.sh --kind short --wait 1800 -- ohc-run.py finish ttyload 0.5-20131024-gitf949537 built`：外层 **rc=2**，
  失败步骤 step5b + step8，与棒-1/棒-2 同形的**既有问题**、非本窗引入（step5b 缺 `reports/test-report.md`、
  `packaging/`、`.staging-verified`；step8 是框架自身 `gen_summary 失败: 'str' object has no attribute 'append'`）；
  收尾块 `EXIT_REASON: finish_success / EXIT_CODE: 0`；finalize 回到基线 **1 个一致性问题（notes.md 无对话记录，存量）
  + 1 个缺失项（release/debug tar.gz，application 包本就不产）**；W2 原子性 `仅含配方变更 (13 文件)` ✅；
  W5 仍报 `manifest.yaml: knowledge_count=8 unreferenced=8`（同形既有）。
- W3 本地 CI（由 finish 内部重跑）：`build_and_test.sh archives/t/ttyload/0.5-20131024-gitf949537 (RC=0)`（`w3-local-ci.log:15`）、
  `G0_RESULT=pass`(`:23`)、`KC_RESULT=pass`(`:63`)、`JC_RESULT=pass`(`:90`)、`L0_RESULT=pass`(`:324`)、
  `L1_RESULT=pass`(`:325`)、**`L2_RESULT=skip: ttyload version/help failed`**(`:326`，框架模板按 `--version/--help` 探、
  上游只有 `-v/-h`，non-blocking ⇒ 如实记 skip，不并进 pass)、`L4_RESULT=pass`(`:327`)、`L5_RESULT=pass`(`:328`)。
- **本轮在盘读数（§4 T3 引用的就是这一轮）**：`reports/conan-create.log:101` 首行
  `localhost 21.53, 21.93, 22.35 04:16:47 ttyload, v0.5.3`、`:102` `ttyload 报出 1min load = 21.53，
  内核 /proc/loadavg = 21.383`（差 0.147，容差 3.0 内）；T4 `:104` `y 轴刻度行数=33 含数据点的行数=36 总行数=40`；
  `:107` `全部 4 项通过`（create 日志共 108 行）。W3 那一路同一测试的另一轮读数在 `w3-local-ci.log:303`
  （22.18 / 21.916），同为 PASS ⇒ **台账一字未改**：`N_static=2 / N_registered=1 / N_executed=2 / N_consumer=4 /
  N_runner=2`，合计 `discovered=2, executed=2, passed=2, failed=0, skipped=0`。
- `.ci-result.json` 随本轮刷新：`timestamp 2026-09-27T04:17:27.440657 / exit_code 0 / integrity_hash 0ca2f5ce79f5a981 /
  log_sha256 a318d836ca579c9d0753e6cbed5714b5ada6df5d1b183b1a0eee35ab29c390b1`。
- 写回复核：`conandata.yml` **未被改写**（verify 的镜像注入由框架自行回写并恢复，本窗 `git status` 对 HEAD 复核无差异）；
  `manifest.yaml` 只被 finish 改 `patch_generation`（`source_work_hash 8ffce3e7fbaac230`、`generated_at '2026-09-27T04:16:43'`）；
  `notes.md` 页脚被 finish 更新为 `编译结束 2026-09-27 04:16`（`最终状态` 子串原样）。
- 本窗**未**做：B 判定改判、Issue/PR/平台/登记表动作、上述 11 项之外的文字改动。
- 卫生复算（本窗，按码位扫描）：13 个 PR 可见件 + 随 PR 的 3 件 reports 共 16 件，U+00AD / U+200B–200D /
  U+FEFF / U+00A0 / U+2011 / 双向控制符（U+202A–202E、U+2066–2069）与 CR **全部 0 命中**；
  两处非缺陷控制符如实留档：`patches/0001-Makefile.patch` 含 35 个 U+0009 制表符（Makefile 配方行必须以
  真制表符起始，本窗未改该件），`reports/conan-create.log` 与 `reports/w3-local-ci.log` 各含 5 个 U+001B（
  被测程序 ANSI 绘图的原始字节，日志按原样存档、未做清洗）。
- `reports/` 三件（`conan-create.log` / `conan-verify-report.md` / `w3-local-ci.log`）默认被 gitignore，
  因本文与草稿**按行号引用**它们，本窗以 `git add -f` 随分支提交，使 PR 可见文本里的行号级引用可解析。

---

**编译结束**: 2026-09-27 04:16
**最终状态**: built

### 10.7 主窗二次校正（04:33，两处 PR 可见文本）

- 草稿 §阴性对照原写 `awk 1 /proc/stat` 得 27 行 ⇒ 主窗在 B 机复测为 **28 行**（`awk 1 /proc/stat` 与 `cat /proc/stat` 行数计数均为 28，与同行 `grep -c . /proc/stat` 的 28 一致），已改。
- 草稿查重表两行「草稿目录 loadavg 命中 0」：现在重跑得 **2**，且这 2 件就是本条草稿自身的 `.kv`/`.md`（写作时该目录内无同类，故当时的 0 成立）⇒ 已在表内注明「今日重跑为 2 = 本稿自我命中」，避免读者按 0 复算失败。
- 这两处都不在 recipe revision 面上（草稿与 notes 均非构建输入）⇒ W3/verify 证据不因此作废。

### 10.8 第二轮审计（HEAD 12d72ec7a5，判 P0=0/P1=1/P2=1/P3=3）整改记录

- P1（对外部件断言不同源）：notes:192 称 Issue 正文含 32 行读数，而 Issue 是我在 28→32 校正之前 PATCH 的，仍写 28 ⇒ 主窗已把 Issue #3500 正文改为 32 行（并注明 wc -l 实测 32、sha256 前缀 6e9c0df8），PATCH 200 + GET 回读 body_len=3992 逐字一致 ⇒ 断言现已为真；本行同时把「逐字对应」降为「同一表述、非逐字」。
- P2（查重表两行计数不可复算）：getattr 20 / fstat 11 两行补注「今日重跑 22 / 13，差值即本稿两件自我命中，排除本稿后不变」，与同表 loadavg 两行的口径统一。
- P3 三条：两处省略号件名还原全名；通用池命中数 2 改 3（该件 .kv/.md 两件 + README）；该行命令由交替式拆成三个单字面量，遵守本表自立的「一律单一字面量」规则。
- 第二轮审计另给两条对我有用的结论：① W3 证据与新 HEAD **绑定成立**（本包 recipe revision 输入面只有 conandata.yml、conanfile.py、0001-Makefile.patch 三件，其后两枚提交均未触碰 ⇒ 不需重跑）；② 其首轮报的 11 条「引用指向空行」经逐条开文件**证伪**（解析器猜错默认目标），本轮不再复述。

### 10.9 第三轮定向重审（HEAD c97d74b426）与判决件装载口径

- 第三轮审计判 **P0=0 / P1=0 / P2=1 / P3=3 ⇒ 可建 PR**；第二轮的 5 项（1 P1 + 1 P2 + 3 P3）逐条复算为**真闭环**（Issue #3500 正文只出现 32、无 28 残留；查重表 getattr 22 / fstat 13 / loadavg 2 与其排除本稿后的 20 / 11 同口径；池计数 3 与三条单字面量逐条实跑复现）。
- **判决件口径**：「reports/z75o-audit-result.json」 是**第二轮**判决（verdict=fail，5 项），保留作审计链留痕，其整改结果见 §10.8；「reports/z75j-audit-result.json」 是**第三轮**判决（**PASS**，绑 「c97d74b426」 （第三轮判决绑 c97d74b426；其后各枚提交仅为该轮判决件装载与它点名的 P2/P3 文字收口，未触 conandata/conanfile/patches/test_package 等构建输入 ⇒ W3 证据与判决对象不变）），是本包审计链的现行判决件；**两份 `.json` 判决件随 PR、两份 `*-report.log` 读版与三件运行日志按 §19 不随 PR（磁盘留档）**。审读时以 z75j 为准。
- 该轮另一条给主窗的口径纠正已采纳：「--skip-finish」 的三条同判**不能**建在归档 「reports/w3-local-ci.log」 的「W3 本地 CI 模拟通过」标记上（该串只出现在 finish 包装层控制台日志，本包权威件为 「~/tmp/uc2/z75s-ttyload-fix/finish.log:87」，mtime 04:17 与归档 w3 日志同分钟）；归档侧改用尾部判决行读数：「L0/L1/L4/L5_RESULT=pass」、「L2_RESULT=skip」（框架初值即 skip、non-blocking）、「Success: 1 / Failed: 0」、「All packages built and tested successfully」，且 「.ci-result.json exit_code=0」、失败步骤 Step6 非 Step5。
