# jnoise 0.6.0 适配笔记

## 基本信息

- 软件：jnoise 0.6.0（Fons Adriaensen，命令行 JACK 白噪/粉噪发生器）
- 平台任务号：7652（档位【中】）
- 构建主机：**B 机**（HarmonyOS PC，HongMeng Kernel 1.12.0，aarch64，8 核/31G）
- worktree：`~/qzy/主理-32-jnoise-0.6.0`，分支 `feat/jnoise-0.6.0`，基线 `origin/main`
- 代号/署名：主理-32
- CONAN_HOME：`~/tmp/ch/home-jnoise`
- 构建日期：2026-09-25

## 源码清点（实测）

- 源：`https://kokkinizita.linuxaudio.org/linuxaudio/downloads/jnoise-0.6.0.tar.bz2`
- 状态码/大小：`HTTP=200 SIZE=10803`（curl -L 与 `size_download` 同读，排除 404-HTML 假下载）
- sha256（本机计算）：`483704462c2f02cbc9f39a800c3b75c4bb9d3a279c1fc33605fc51e27780464a`
- 交叉核对：与 Debian `jnoise_0.6.0-6.dsc` 的 `Checksums-Sha256` 行逐字一致
  （`4837044... 10803 jnoise_0.6.0.orig.tar.bz2`）
- 文件共 9 个：`AUTHORS COPYING README INSTALL` + `source/{Makefile,jnoise.cc,rngen.cc,rngen.h,prbsgen.h}`
- 语言构成：`.cc` 2 个（jnoise.cc、rngen.cc）+ `.h` 2 个（rngen.h、prbsgen.h），无 `.c` 文件
  ⇒ 上游**不是** "c=2/cpp=2"，而是 cpp=2 + 头文件 2
- 构建系统：裸 Makefile（无 configure/CMake/autotools），Makefile 位于 tarball 的 `source/` 子目录

## 依赖（W0）

| 依赖 | 版本 | 发布态核验 |
|---|---|---|
| jack | 1.9.22 | `bash ci/scripts/preflight_check.sh jnoise/0.6.0` → **RC=0** + `[OK] 已发布: jack/1.9.22` + `[OK] 版本号未被占用: jnoise/0.6.0`（R37）+ `[OK] 所有依赖均已发布到制品仓`。本包执行期原件 `~/tmp/uc2/z32-jnoise/preflight.log`；W4-r1 审计独立复算同一条：`~/tmp/uc2/z32-jnoise-w4/w0-recheck.log:8`（已发布）、`:11`（版本未占用）、`:14`（全部依赖已发布）。W3 内 L0i (R36) 另报 `[ok] dependency in registry: jack/1.9.22`（`reports/w3-local-ci.log:31-32`） |

- **作废一条第二证据形态（W4-r1 P2-1 勘误）**：本节此前写的"强制重下
  `conan download jack/1.9.22@ --only-recipe -r ohpcd -f` 亦从远端取回成功"**不成立**——在
  conan 2.29.1 上 `download` 子命令的 `-f` 是 `--format` 而非 force，该命令实测 **rc=2 用法错误**
  （`argument -f/--format: expected one argument`），从未成功执行；原文见
  `~/tmp/uc2/z32-jnoise/w0.log:1-6`、`w02.log:1-6`、`run_verify.out:1-6`（三处一致，W4-r1 复算同）。
  改用 `-f json` 复跑虽 rc=0，输出却是 `Skip recipe jack/1.9.22#db0f1c95… already in cache`
  ⇒ **属假成功，不证远端发布态**，同样不采。⇒ **W0 只认 `preflight_check.sh` 一条形态**；
  将来若需"从远端重下"的证据，必须看到 `Downloading recipe` 行，`Skip` 不算。
- 版本选择依据：上游 `source/Makefile` 的 `jnoise: LDLIBS += -ljack -lrt` 只要求 `libjack`，
  且源码使用 `jack_client_open()`（JACK 2 API，1.9.x 起提供）；Debian 侧 Build-Depends 为
  `libjack-dev | libjack-jackd2-dev` ⇒ 制品仓现有 `jack/1.9.22` 即满足，无需更早版本。
- 未使用通配 `conan list` 判定 binary（R35）。

## Makefile 事实（逐条复算，含对主窗预扫的修正）

`grep -nE 'Werror|TESTS|check|install' source/Makefile` 实测输出只有 install 三行：

| 事实 | 实测 |
|---|---|
| `-Werror` | **不存在**（预扫假设成立） |
| `TESTS` 变量 / `check` 目标 | **不存在**（预扫假设成立）；Makefile 只有 `all` / `install` / `clean` 三个目标 |
| `PREFIX` | `PREFIX = /usr/local` —— **普通 `=` 赋值**，不是 `?=` 也不是 shell 级烧死 ⇒ **make 命令行前缀变量可覆盖**，实测 `PREFIX=/` + `DESTDIR` 生效（未打补丁） |
| `SUFFIX`/`LIBDIR` | `LIBDIR = lib$(SUFFIX)`（由 `uname -m` 推出 `lib64`）**在本 Makefile 中从未被引用**，属死变量 |
| `-DSHARED="$(PREFIX)/share"` | 宏确实被编进 CPPFLAGS，但 `grep -n SHARED source/*.cc source/*.h` **0 命中** ⇒ 0.6.0 源码从不读它，**不存在"烧死路径的运行期后果"** |
| 链接命令 | `g++ $(LDFLAGS) -o $@ $(JNOISE_O) $(LDLIBS)` —— **编译器名写在命令位置字面量**，见下节 |
| install 命令 | `install -d ...` / `install -m 755 ...` —— 裸 `install`，无 `$(INSTALL)` 变量 |
| `-lrt` | 存在于 `jnoise: LDLIBS += -ljack -lrt`；**OHOS 工具链可解析，无需剔除**（本次实建链接成功） |

## 遇到的问题与解决方案（症状 → 根因 → 最小复现 → 失败方案 → 最终方案 → 边界）

### 1. 链接期 `g++` 不存在

- 症状：`make` 编译阶段可过（隐式规则用 `$(CXX)`），但**最后一步链接**报
  `/bin/sh: g++: not found`（Error 127）。〔括注（W4-r2 P3-N1）：该串是修复前的转述形态，本机现不可逐字复现；取证锚见本文件「收口修订 2」§2（错误原文口径修正）与草稿 DRAFT-jnoise-0.6.0-makefile-linkline-literal-cxx-name.md:44-46。历史症状按原样保留不删。〕
- 根因：上游把编译器名**写在 recipe 命令行位置的字面量**（`g++ $(LDFLAGS) -o $@ ...`），
  而不是从变量取。OHOS 只有 `clang/clang++`（`/data/service/hnp/bin/`），全盘无 `g++`。
- 最小复现：`sh -c 'g++ --version'` → not found；`command -v g++` → 空。
- 失败方案：
  - `make CXX=clang++` 只修好编译步，链接步仍用字面量 `g++` ⇒ 错误推迟到最后一步，更费时间；
  - 造一个 `g++` 软链/垫片进 PATH ⇒ 违背 R33（编译器必须来自 conan profile
    `tools.build:compiler_executables`），且 CI 侧 PATH 不可控。
- 最终方案：portability 补丁把该行改为 `$(CXX) $(LDFLAGS) -o $@ $(JNOISE_O) $(LDLIBS)`，
  配方在 make 命令行传 `CXX=<profile 取得>`。
- 边界：与草稿 `DRAFT-cohomcalg-0.32-makefile-gxx-override` 同族但**不同层**——
  cohomcalg 是 `CC := g++`/`LD := g++` **变量赋值**型（`:=` 压过环境变量，但 make 命令行变量
  仍可覆写）；jnoise 是**命令位置字面量**型，命令行/环境变量**都覆写不到**，唯一解是补丁。
  判别式：`grep -nE '^[[:space:]]+(g\+\+|gcc|cc)[[:space:]]' source/Makefile` 有命中 ⇒ 字面量型。

### 2. install 目标依赖 coreutils `install(1)`（E174 家族）

- 症状：`make install` 报 `install: command not found`。
- 根因：OHOS 无 GNU coreutils，PATH 上没有裸 `install`。
- 最小复现：`command -v install` → 空。
- 判定坑（重要）：`ls -l /bin/install` 返回 **`Permission denied`**，而
  `/bin/install -d d && /bin/install -m 755 f d/` 两次 rc 均为 **0** 且文件确实落地
  ⇒ **stat 面对这类路径是假阴性，能力判定必须用 open()/exec 面**。
- 失败方案：直接 `make INSTALL=cp`（上游没有 `$(INSTALL)` 变量，赋值无效）。
- 最终方案：补丁参数化为 `INSTALL ?= /bin/install`（与同作者兄弟包 aeolus/0.10.4 同法，
  即 M13 池件机制），配方用 `make install PREFIX=/ DESTDIR=<package_folder>`。
- 边界：`DESTDIR` 拼接是 `$(DESTDIR)$(PREFIX)/bin`，因 `PREFIX=/` 得 `<pkg>//bin`，
  双斜杠在 POSIX 路径中合法，故不需要 aeolus 那条"补斜杠"补丁。

### 3. make 变量传递方式

- 症状（若踩）：`make CPPFLAGS=-I...` 会让 `-DPROGRAM/-DVERSION/-DSHARED` 整行丢失。
- 根因：Makefile 用 `CPPFLAGS +=`，命令行变量优先级最高会**整体替换**而非追加。
- 最终方案：依赖的 `-I/-L` 走**环境变量** `CPPFLAGS=... LDFLAGS=...` 传入，
  使 Makefile 的 `+=` 照常追加。只有 `CXX`/`PREFIX`/`DESTDIR` 这类
  "Makefile 里没有 `+=` 语义"的变量才放命令行。
- 另需 E132：OHOS SDK 的 lld 依赖 `libxml2.so.16`，musl ldso 不展 `$ORIGIN`（E019），
  配方与 test_package 均注入 SDK `llvm/lib` 到 `LD_LIBRARY_PATH`（保持 lld，不换 GNU ld）。

## 构建与打包（配方实际命令）

```sh
CPPFLAGS="-I<jack>/include" LDFLAGS="-L<jack>/lib" \
  make -C source -j1 PREFIX=/ CXX=<profile clang++> jnoise
make -C source -j1 PREFIX=/ DESTDIR=<package_folder> CXX=<profile clang++> install
```

产物：`bin/jnoise`（27008 字节，EM_AARCH64 ELF）。打包内对产物做 `binary-sign-tool -selfSign 1`
自签（OHOS 不签不可执行），并 `chmod 0755`。

## 测试账本（五维，与 test_package/MANIFEST.yml、README 同源）

| 维度 | 数 | 说明 |
|---|---|---|
| 静态：上游测试用例合计 | **0** | 四形态逐形自数见下 |
| 可执行：上游用例中本机可执行数 | **0** | 无可执行对象 |
| 实测通过：适配后消费者断言 | **6** | `RESULT: pass=6 fail=0`，rc=0 |
| 跳过 | **0** | — |
| 失败 | **0** | — |
| 未执行（另计，不缩分母） | 1 | `jack_activate` 之后的白噪/粉噪输出分支 |

上游测试四形态逐形自数（对 tarball 全树 9 个文件实测）：

1. 独立测试框架（testsuite/、gtest、criterion…）→ **无**
2. 语料目录（t/、test/、tests/、samples…）→ **无**
3. RUNTEST/DejaGnu 脚本（`*.test`、runtest）→ **无**
4. 示例目录（examples/、demo/）→ **无**

⇒ 上游测试合计 0，按 rule4 如实记 0，由 test_package 消费者断言补齐（不冒充上游测试）。

test_package 的 6 条断言（`./test_jnoise <pkg>/bin/jnoise`，全部可证伪、失败即非零退出）：

| # | 断言 | 实测详情 |
|---|---|---|
| A1 | 打包产物是 EM_AARCH64 的 ELF（用 open()/read() 读，不用 stat） | `size=27008 e_machine=183` |
| A2 | 在打包二进制的**镜像字节里定位到 libjack 的 SONAME 串**，再交给 A3 做 dlopen 阳性对照（措辞按 W4-r1 P3-2 降级：实现是**对整个镜像做原始字节查找**，**不是**解析 `.dynamic`/`DT_NEEDED` 表） | `libjack.so.0` |
| A3 | dlopen 该 SONAME 并解析出 `jack_client_open`（运行期阳性对照） | `handle≠null jack_client_open=0x5ba407ec8c err=-` |
| A4 | `jnoise 0` → rc=1 且输出 `Level is too high, max = -10dB` | rc=1，文本逐字命中 |
| A5 | `jnoise abc` → rc=1 且输出 `Level is too high`（atof 非数值 → 0 dB 越上限）；**弱点已知**：该断言文本是 A4 的前缀子串、退出码同为 1，独立性只来自**输入不同**（走 `atof` 解析路径而非数值直取）——见下条 | rc=1，文本逐字命中 |
| A6 | `jnoise -10`（边界值被接受）→ rc=1 且输出 `Can't connect to JACK`，**且不含** `Level is too high` | rc=1，两条都满足 |

- **A2 措辞与实现的差距（W4-r1 P3-2，本轮只降级措辞）**：仓内 `test_package/conanfile.py:9-10` 与
  `test_package/MANIFEST.yml:25` 的 description 仍写作"动态字符串表里找到 NEEDED 名"，**强于实现**
  （`test_jnoise.cpp:171-181` 实为 `text.find("libjack.so")` 全镜像原始字节查找）。理论上存在
  "非 dynstr 文本造成假阳性"的空间，但 A3 随即对同一 SONAME 做 `dlopen` 阳性对照，两条件同时假阳性的
  概率极低。**把实现补成解析 `DT_NEEDED` 属 `test_package/` 测试代码改动** ⇒ 会作废已复算的 W3/审计证据链
  （13 文件集、`integrity_hash`、`log_sha256`），**本轮不动，需主窗决策**。
- **A5 判据不独立（W4-r1 P3-1）**：A5 与 A4 押同一前缀、退出码同为 1，差别只在参数解析路径
  （`abc` 经 `atof` 得 0.0）。要让 A5 真正押"不同输出面/不同退出码组合"，须另找 `atof` 路径独有的
  可观测差；那同样是测试代码改动 ⇒ **本轮不动，弱点如实登记，需主窗决策**。
- A6 的必要性：只有 A4/A5 时"随便给个参数都因电平超限而退出"也能全绿；A6 用**恰好等于上限**的
  值证明电平分支被正确越过、进程真的走到了 JACK 客户端路径 ⇒ 三条断言互为否证，非"两分支都记 ok"。
- A6 前提：主机上无运行中的 JACK server（本机与 CI worker 皆然）；若存在 server，
  jnoise 会常驻循环，由测试程序内的 10 秒看门狗判 FAIL（不会静默通过）。
- 汇总行前缀为 `RESULT:`，刻意不以 `[PASS]` 开头，避免被计入断言数。

## JACK 运行面探针（分层归因，证据 · **r1 起以盘上原始输出件为准**）

**探针脚本（r1 修复版）**：`~/tmp/uc2/z32-jnoise/probe.py`（ctypes 直调 libc/libjack；能力判定一律 open() 系。
上一棒原件已按字节备份为同目录 `probe.py.pre-fix-r1`，2904 B，未删）。
**原始输出件（带时间戳，整改棒实跑，2026-09-25 04:59:07）**：
`~/tmp/uc2/z32-jnoise-fix1/probe-out-20260925-045907.txt`（59 行，sha256 前 16 位 `a05bce0748d2bf39`；
`probe-out-latest.txt` 是指向它的软链）。一个文件里含两条环境：**RUN-1** 空 `LD_LIBRARY_PATH`（`:1-29`）、
**RUN-2** `LD_LIBRARY_PATH`/`CONAN_HOME` 指向 jack 包（`:31-59`）。完整调用形式写在输出件首行
（`INVOCATION python3 probe.py`，无 argv ⇒ 自动定位 jack 头文件目录，见 `:12`）。

**为什么上一棒没有可复算的读数（W4-r1 P2-3）——两个探针自身缺陷，已修**：

1. 原脚本第 9 行 `hdr = sys.argv[1]` 在无 argv 时抛 `IndexError: list index out of range`、rc=1
   （W4-r1 审计复跑踩到的就是这条）⇒ 本版把 argv 改为可选并自动发现头文件目录，且枚举常量按该目录
   **全部 `.h` 的并集**解析，使 `jack_options_t` 与 `jack_status_t` 分处不同头文件时也能解码。
2. 原脚本 `shm_open` 的 flags 写成 `os.O_RDWR | 0o200`，而 musl/Linux 上 **`0o200 = O_EXCL`、
   `O_CREAT = 0o100`** ⇒ **原写法根本不含 `O_CREAT`**，与上一笔记"shm_open(O_CREAT)"的口径不符。
   本版两种 flags 各跑一次并排打印，并显式印出数值。**据此推翻上一棒第 3 层的 `ENOENT` 结论**（下表）。

| 探针 | 读数 | 输出件行号 |
|---|---|---|
| `open("/dev/shm", O_RDONLY)` | FAIL **errno=13 EACCES** | `:14`（RUN-2 同读 `:45`） |
| `open("/dev/null", O_RDONLY)` | OK（阳性对照） | `:15` / `:46` |
| `open("/tmp", O_RDONLY)` | FAIL **errno=13 EACCES** | `:16` / `:47` |
| `open("/mnt/shmem", O_RDONLY)` | FAIL errno=2 ENOENT | `:17` / `:48` |
| `open("/data/local/tmp", O_RDONLY)` | FAIL **errno=13 EACCES** | `:18` / `:49` |
| `shm_open(name, O_RDWR\|O_EXCL)` flags=`0o202`（**＝上一棒实际写法**） | fd=-1 **errno=2 ENOENT** | `:19` / `:50` |
| `shm_open(name, O_RDWR\|O_CREAT)` flags=`0o102`（**修正后**） | **fd=4 errno=0 OK**；写读 1024 B 一致；backing path `/dev/shm/jnoise-z32-probe` | `:21`、`:23`、`:24` / `:52`、`:54`、`:55` |
| 两次 `shm_open` 返回后进程存活 ⇒ **未收 SIGSYS** | `call returned to python, pid … still alive => no SIGSYS delivered` | `:20`、`:22` / `:51`、`:53` |
| `dlopen("libjack.so.0")` 裸 SONAME、空 `LD_LIBRARY_PATH` | **FAIL** `Error loading shared library … No such file or directory` | `:25` |
| `dlopen` 绝对路径 `~/tmp/ch/home-jnoise/p/jackf82461c1df736/p/lib/libjack.so` | OK，`jack_get_version_string_ptr=True` | `:26` |
| `dlopen("libjack.so.0")` 裸 SONAME + `LD_LIBRARY_PATH=<jack 包 lib>` | **OK** | `:56` |
| `jack_client_open("z32probe", JackNoStartServer=0x1, &status)` | handle=None（**NULL**）、**errno=2 ENOENT**、**`status=0x11`** | `:27` / `:57` |

- `status=0x11` 的位解码以 `types.h` 的 `jack_status_t` 为准：**`JackFailure(0x1) | JackServerFailed(0x10)`**
  （PARSE 行 `:13` / `:44` 给出 `JackNoStartServer=1(types.h)`、`JackFailure=1(types.h)`、
  `JackServerFailed=16(types.h)`）。输出件里那一长串并列成员是本版"并集解析所有 jack 头文件"造成的
  **同名位值碰撞**（多个头文件里都存在取值 0x1 / 0x10 的成员），**不作结论用**。
- 探针进程捕获到的 libjack stderr 原文（`stderr` 无缓冲，故排在同一件的最前面）：RUN-1 `:2-6`、RUN-2 `:33-37`：

```
Cannot connect to server socket err = No such file or directory
Cannot connect to server request channel
jack server is not running or cannot be started
JackShmReadWritePtr::~JackShmReadWritePtr - Init not done for -1, skipping unlock
JackShmReadWritePtr::~JackShmReadWritePtr - Init not done for -1, skipping unlock
```

- 被测二进制自己打的 `Can't connect to JACK` 一行属 **test_package A6** 的读数，原件在
  `~/tmp/uc2/z32-jnoise/conantest.log:76-90`（上一版把两者混排进了同一个引用块，现已分开）。

分层结论（三分类不得混，**r1 按实跑读数修订**）：

1. **构建/链接/装载面：实测可用，但有前提**。`libjack` 链接通过、产物是合法 aarch64 ELF；
   `dlopen("libjack.so.0")` 裸 SONAME **只在 `LD_LIBRARY_PATH` 指向 jack 包 lib 目录时**成功（`:56`），
   空 `LD_LIBRARY_PATH` 的裸 shell 里失败（`:25`）⇒ 与 test_package 注入 runenv 的做法一致，
   **不是** OHOS 装载面缺陷，但也**不得**写成"任何环境下都能装载"。`jack_client_open` 符号可解析（`:26`/`:56`）。
2. **运行时 JACK server 面：未执行（不是失败）**。`jack_client_open` 以 `JackNoStartServer` 连接返回 NULL、
   errno=ENOENT、`status=0x11`=`JackFailure|JackServerFailed`，语义就是"没有 server 在跑/起不来"。
   因此 `jack_activate` 之后的白噪/粉噪输出分支**未执行**，按"未执行 + 证据"申报，不缩分母，
   也**不得**据此写"OHOS 不支持 JACK"。
3. **权限面 vs POSIX shm 面（本条为 r1 修正项）**：`/dev/shm`、`/tmp`、`/data/local/tmp` 三个**目录**
   本身对 `open()` 是 **EACCES(13)**（`:14`/`:16`/`:18`），`/mnt/shmem` 不存在（`:17`）；
   **但 `shm_open(O_RDWR|O_CREAT)` 成功**，写读 1024 字节一致，落点就是 `/dev/shm/jnoise-z32-probe`
   （`:21-24`）⇒ **"打不开目录" 与 "创建不了 POSIX shm 对象" 是两件事，本机 shm 对象可创建可用**。
   上一棒因 flags 少写 `O_CREAT` 而读到的 ENOENT（`:19`）是**探针缺陷**，不是系统能力，现已按实跑更正；
   两种 flags 的调用都正常返回、进程存活 ⇒ 与 seccomp/SIGSYS 无关（`:20`/`:22`）。
   本轮仍未出现任何 OHOS 内核缺陷证据，也未出现配方面缺陷。
- 依约束未自造/拉起 JACK server（未启动 jackd），故第 2 层保持"未执行"。
- 探针脚本与输出件都留在设备证据目录，**不属仓内产物、不入 PR**；仓内只引用"路径 + 行号"。

## 门禁读数

| 门禁 | 命令 | 读数 |
|---|---|---|
| W0 依赖预检 | `bash ci/scripts/preflight_check.sh jnoise/0.6.0` | rc=0，`[OK] 已发布: jack/1.9.22`、`[OK] 版本号未被占用` |
| 配方检索 | `python3 scripts/ohc-run.py recipe-search jnoise` | top1 = 本包骨架（catalog 重建 6175 配方） |
| W2/W3 结构+create | `python3 scripts/ohc-run.py conan-verify jnoise 0.6.0` | `G1: PASS`、`G2: PASS`、`G3: PASS`、`G4`、`✅ 配方验证通过: jnoise 0.6.0` |
| test_package | `conan test archives/j/jnoise/0.6.0/test_package jnoise/0.6.0@ohpcd/stable -pr:h -pr:b` | `RESULT: pass=6 fail=0`，rc=0 |
| 知识图谱 | `python3 scripts/ohc-run.py graph validate` | `✅ All checks passed (169 warnings)`，warnings 全为存量条目 C13/C14，与本包无关 |
| W3 本地 CI 模拟 | `python3 scripts/ohc-run.py finish jnoise 0.6.0 built`（step5 build_and_test.sh） | **失败，但不是本包缺陷**：`Junk Files: 2` → `JC1: 3 个运行时状态文件被跟踪` + `JC5: 3 个 archives 下未登记的隐藏文件`，命中对象全为**他人已合并进 origin/main 的归档**：`archives/c/cloog/0.21.1/.build-closed`、`archives/c/cloog/0.21.1/.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`（cloog 那条由已合并提交 `906cc59ae7` 带入）。junk_check 跑 full 模式（整仓 85512 个文件）⇒ 在当前基线上任何包都过不了这一步。本包 `archives/j/jnoise/` 未被 JC 点名。 |
| 静态硬闸 PF1–PF9 | `python3 scripts/ohc/preflight.py . origin/main HEAD` | 见提审前记录（该闸与上面 W0 的 preflight_check.sh 是两个不同的东西，本包两者都跑） |

- 依红线未改 `ci/`、`scripts/`，未删他人归档的标记件，未为凑绿改登记表或表单。
- 槽位与闸：`gate.sh 2500` 通过（`SLOT_OK`，`MemAvailable=9042MB`），构建经
  `build-slot.sh --kind short --mem 2500` 串行执行。

## B 判定初判（四范围同批查重）

查重范围：`knowledge/graph/*.kv`、`knowledge/graph/index.tsv`、`knowledge/drafts/*.kv`、
`archives/**/notes.md`（外加仓外通用池 `经验文档/B草稿库/`）。

读过原文的候选条目：

- `knowledge/graph/E174.kv`（coreutils `install` 缺失，rec=手动 cp+chmod，fallback=Makefile 补丁）
- `knowledge/graph/E053.kv`（configure 期 CXX 环境变量；与本包不同层）
- `knowledge/drafts/DRAFT-cohomcalg-0.32-makefile-gxx-override.kv/.md`（Makefile 硬编码 g++）
- `经验文档/B草稿库/DRAFT-PKG-VER-suckless-baked-paths-makevar-override.md`（M18）
- `经验文档/B草稿库/DRAFT-PKG-VER-makefile-install-cmd-absent-makevar-override.kv`（M13）
- `archives/a/aeolus/0.10.4/notes.md` + `patches/0001-source-Makefile.patch`（同作者同族先例）

初判：

- **hit（E174 + M13）**：install 命令缺失这一面完全命中既有机制，修法与 M13 一致
  （参数化 `INSTALL ?= /bin/install`），**不再为新条目**。
- **hit 家族 + 层次差（cohomcalg 草稿）**：`g++` 硬编码属同一症状家族，但 cohomcalg 是
  **变量赋值型**（`make CC=clang++ LD=clang++` 可解），jnoise 是**命令位置字面量型**
  （命令行与环境变量都覆写不到，只能补丁）。若按层次差算增量，候选新条目
  `DRAFT-jnoise-0.6.0-makefile-linkline-literal-cxx-name`，判据 =
  `grep -nE '^[[:space:]]+(g\+\+|gcc|cc)[[:space:]]' Makefile` 命中（命令位置）。
  ⇒ **本窗倾向 create 这一条，但按红线只给结论，不建 Issue、不写表**，由主窗裁定；
  若主窗判 hit，则本包 B 结论为 `hit(E174, M13, cohomcalg 草稿)`。
- **不命中（主窗预扫需修正）**：预扫把本包归到 **M18（suckless 裸 Makefile 烧路径族）**，
  实测 M18 不适用——M18 的症状是 `CC=cc` 别名不存在 + 聚合变量 `X11INC/X11LIB` 烧死需
  命令行覆写 `INCS/LIBS`；jnoise 既无 X11 也无聚合变量，`PREFIX` 是普通赋值可覆写，
  且 `-DSHARED` 宏在源码中 0 引用 ⇒ **无"烧路径"的运行期后果**。本包真正的机制面是
  "命令位置字面量 g++"+"裸 install"。

## 已知限制与注意事项

- 本包是客户端程序，运行期必须有 JACK server；发布物不含 server 端。
- 上游 0.6.0 无 man page、无示例、无 `--help`；参数只有一个电平（dB，上限 -10 dB）。
- `README`/`INSTALL` 提到的 root `make install` 语义未采用（配方走 conan staging）。
- 未提交任何标记件：`reports/`、`TASK_CARD.md`、`__pycache__/`、`metadata/`、
  test_package 下 conan 生成的 `conan*.sh`/`deactivate_*.sh`/`test_jnoise` 二进制
  （已 mv 至 `~/tmp/uc2/z32-jnoise/tp-products/`，未 rm）。

## 收口修订：PF1–PF9 静态硬闸改前 / 改后

改前（HEAD=35cb4f9664，命令 python3 scripts/ohc/preflight.py . origin/main HEAD）：

- ✗ PF7 源URL闸（R39）命中 2 条：conandata.yml:9 与 manifest.yaml:11 被判 Debian 下游重打包源
- ✗ PF9 分支/路径闸命中 1 条：软件级 README.md / commands.json / manifest.yaml 被判「缺版本目录层」
- PF1–PF6 与 PF8 无命中：补丁新增行不含 __OHOS__，conanfile 不含 -D__OHOS__ 注入与 replace 动态注入，
  test_package 的 test() 有真实 self.run 且执行被测二进制，conandata 不含 file:// 与镜像代理域

改后（HEAD=c96fa122a3）：

- **PF7 归零**：源 URL 换成上游官方站 https://kokkinizita.linuxaudio.org/linuxaudio/downloads/jnoise-0.6.0.tar.bz2
  （实测 HTTP=200、10803 字节、sha256 与 Debian 侧 .orig 逐字同串 ⇒ 构建输入字节未变），
  并用新 URL 重跑 conan-verify 通过（SLOT_OK、配方验证通过 jnoise 0.6.0）。sha256 未做任何迁就性修改。
- **PF9 保留、不整改**：被点名的三个文件正是 G1 结构闸强制要求的软件级三件套（删掉即 G1: FAIL），
  与 PF9 的路径深度判据互斥，属仓库存量的框架面缺陷（与已登记的 preflight.py:570 判据冲突同类），
  只上报不修改，未为凑绿删除任何必需文件。
- W3 本地 CI 模拟（finish step5）仍被基线存量 Junk 卡住，命中对象全为他人已合并进 origin/main 的归档，
  读数见上文门禁表；本包路径未被 JC 点名。

## 收口修订 2（主理-32 执行棒）：W3 junk_check 模式复算 + 错误原文口径 + 路径 B 定案 + 提审声明

### 1. W3 / `JUNK_CHECK_MODE` 复算（**推翻上一棒"基线假红、任何包都过不了"的成因结论**）

复算读数（worktree `~/qzy/主理-32-jnoise-0.6.0`，HEAD=`816c91f224`，工作树对本包路径干净）：

| 探针 | 读数 | 结论 |
|---|---|---|
| `git rev-parse --verify refs/remotes/origin/main` | `48d9cee6844d0fca1f25e86c2df1293b904855d8`，RC=0 | ref 可解析 |
| `git rev-parse --verify origin/main`（`junk_check.sh:52` 用的正是这个形式） | 同上，RC=0 | **未**走 `:58-60` 的"ref 不可解析 ⇒ full" |
| `git rev-parse --short origin/main` | `48d9cee684`，RC=0 | 同上 |
| `git -C ~/build_in_harmonyos rev-parse --verify refs/remotes/origin/main` | `48d9cee684`，RC=0 | 主检出也可解析（worktree 的 `--git-common-dir` = `/storage/Users/currentUser/build_in_harmonyos/.git`） |
| `git merge-base origin/main HEAD` | `48d9cee684`（= origin/main 自身） | main 是 HEAD 的祖先，三点 diff 有基线 |
| `git diff --name-only --diff-filter=ACMR origin/main...HEAD` | **11 行**，全部为本包文件，RC=0 | `:53` 有输出 ⇒ 不进 `:54-56` 的空 diff 回退 |
| `bash ci/scripts/junk_check.sh`（不带参数） | `检查模式: incremental (11 个文件)` + `JC_RESULT=pass` + RC=0 | **W3 的 JC 闸在本包口径下是绿的**（**执行期局部件，非最终 W3 结论**，见下条限定） |

（证据：`~/tmp/uc2/z32-jnoise/junkcheck-incr.log:4` 模式行、`:23` `JC_RESULT=pass`、`:25` `RC_JC=0`。）

- **W3 结论口径限定（W4-r1 P3 第三条，r1 补记）**：上表与本节引用的
  `junkcheck-incr.log`（`incremental (11 个文件)`，跑在 HEAD=`816c91f224` 时）与
  `junkcheck-standalone.log`（在非 git 目录下跑 ⇒ `JC_RESULT=pass: empty`）都是**执行期局部件**，
  **不得充作 W3 结论**。最终绿判据**只认** `archives/j/jnoise/0.6.0/reports/w3-local-ci.log:73`
  的 **`检查模式: incremental (13 个文件)`** 那次（同件 `:92` `JC_RESULT=pass`、`:254`
  `RESULT: pass=6 fail=0`；13 文件集与 `git diff --name-only origin/main...HEAD` 逐字同集，
  由 W4-r1 审计独立复算）。本节的"11 个文件"是当时 HEAD 的真实读数，**保留不删**，
  但结论一律以上述 13 文件那次为准。

- **真实成因 = 时序，不是基线、也不是本包缺陷**：上一棒那次 `finish` 跑在**提交之前**
  （`SLOT_OK 03:29:39` ⇒ `reports/w3-local-ci.log` mtime 03:30，其 `:73` 行印 `检查模式: full (85512 个文件)`；
  而首个提交 `35cb4f9664` 在 03:35、HEAD 提交 `816c91f224` 在 03:38，见 `~/tmp/uc2/z32-jnoise/commit.log`/`commit2.log`）。
  当时 HEAD 仍等于 `origin/main` ⇒ `:53` 的 diff 为空 ⇒ 命中 `:54-56` 的"**空 diff ⇒ full**"回退，
  于是拿整仓 85512 个文件算账，才点到他人已合并进 main 的 `archives/c/cloog/0.21.1/.build-closed`、
  `.staging-verified`、`archives/k/kics/2.1.20/.staging-verified`。**结论：本表上方"门禁读数"节 W3 行写的
  "在当前基线上任何包都过不了这一步"作废**（原文保留不删，以本节为准）。
- 主窗报的"实测矛盾"已定性并**与 ref 无关**：`git rev-parse --short origin/main HEAD` 抛
  `fatal: Needed a single revision`（RC=128）是因为 **`rev-parse --short` 只接受单个修订** ——
  `git rev-parse --short HEAD HEAD` 同样 fatal（RC=128），而 `git rev-parse origin/main HEAD`（不带 `--short`）
  正常输出两个 SHA。旧写法是**用法错误**，不要拿它当"ref 解析不了"的证据。
- 处置纪律：§1① 的 `git fetch origin main` **不需要做**（ref 本来就可解析）；§1② 的 `pr.diff` 通道
  **未使用** —— 实测 `git check-ignore -v pr.diff` 对本 worktree **无匹配**（只 `.ci-result.json` 被
  `.gitignore:238` 覆盖）⇒ 按红线"未被覆盖就不要创建它"，worktree 根**不存在 `pr.diff`**，
  也未做任何 `update-ref` / 未碰他人标记件 / 未改 `ci/`、`scripts/`。

### 2. 错误原文口径修正（新草稿 `error_signature` 的取证依据）

- 上一棒 notes §1 记的症状 `/bin/sh: g++: not found`（Error 127）在本构建机上**无法逐字复现**。
  受控复现（`~/tmp/uc2/z32-jnoise/mkprobe/Makefile`，规则体只有一行 TAB `g++ -v`）
  `make -j1 CXX=clang++` 的实执原文为：

  ```
  g++ -v
  make: g++: No such file or directory
  make: *** [Makefile:2: all] Error 127
  ```

  经 shell 驱动的 `sh -c "g++ --version"` 在 toybox sh 上是 `sh: g++: inaccessible or not found`；
  `command -v g++` 空（RC=1）。⇒ 新草稿的 `error_signature` **只用这几条实测原文**，不沿用旧转述。
- 同一次复现顺带把核心判据钉死：**命令行 `make CXX=clang++` 覆写不到"命令位置字面量"**
  （编译步照常、链接步照旧 exec `g++`），这正是与 cohomcalg"变量赋值型"的处置面差别。

### 3. `install(1)` 判定坑（口径确认，未改判）

- `ls -l /bin/install` 报 `Permission denied`（**stat 假阴性**），而实执 `/bin/install -d <dir>` 与
  `/bin/install -m 755 <f> <dir>/` 两次 rc 均为 **0** 且文件确实落地 ⇒ **按实执读数定性，不按 stat 读数**
  （与 notes §2 已有记录一致；此处收口确认）。同理本节的 JC 结论一律以实执 RC/输出行为准。

### 4. JACK 运行面口径（历史口径 · 其中一条读数已作废）

- 保持"**链接与构建可用已实测；有 server 的运行路径未执行**"。分层证据（现行口径）：`dlopen("libjack.so.0")` OK；
  `jack_client_open(...)` 返回 NULL、errno=2(ENOENT)、`status=0x11`（JackFailure|JackServerFailed）；
  目录级 `/dev/shm` 为 EACCES。
  ⚠ **本小节旧版曾写「`shm_open` ENOENT（无 SIGSYS ⇒ 非 seccomp 拦）」，该 ENOENT 读数由探针自身 flags 缺陷造成（缺 O_CREAT），已在下文「收口修订 3」§4「P2-3：探针原始输出件已实跑落盘」就地作废**：旧探针的 flags 写成
  `O_RDWR|O_EXCL`（**不含 `O_CREAT`**），是测量口径错误；改用 `O_RDWR|O_CREAT` 后 `shm_open` **成功**（`fd=4`、`errno=0`、
  写读 1024 全等，落点 `/dev/shm/…`），且关掉 fd 后**不带 `O_CREAT` 重开仍成功读回同数据**、`shm_unlink` 返回 0
  ⇒ POSIX shm 命名空间**可用**，被挡的只是"以普通文件方式打开/枚举该目录"。现口径分两列：
  ①目录级 `open`/`opendir` `/dev/shm` = `EACCES(13)`；②`shm_open` 按名字使用 = OK。两者不合并成"没有 shm"。
  ⇒ **既不写"JACK 在 OHOS 不可用"，也不写"已验证运行"**。
  ⇒ 作废指针（W4-r2 P2-N1）：本小节标题原标「（不变）」，因上述 shm_open ENOENT 读数已被推翻而一并改掉；本节保留的排他结论只有目录级 /dev/shm 的 open/opendir = EACCES(13) 与「整条探针跑完进程存活、未收 SIGSYS ⇒ 非 seccomp 拦」两条，不再含任何 shm_open 返回 ENOENT 的断言（实测依据与其探针输出件引用见「收口修订 3」§4）。

### 5. 路径 B 定案与提审最小声明（3+2 行）

- **适配路径**：**路径 A（直接适配，含 1 枚可移植性补丁，补丁数 1）＋ 路径 B 判定 = `create`**（本 PR 主张 1 条新知识 = 机制「makefile 规则命令位置字面量」，一 PR 一知识）
- **使用知识库**：是（`knowledge/graph/E174.kv` 的 install 缺失面按 hit 复用；`knowledge/drafts/DRAFT-cohomcalg-0.32-makefile-gxx-override.kv` 同族已读原文；仓外通用池 M13 同法）
- **知识库扩展**：`knowledge/drafts/DRAFT-jnoise-0.6.0-makefile-linkline-literal-cxx-name.kv` + 同名 `.md` —— 机制 = 编译器名写在 makefile 规则的**命令位置字面量**上 ⇒ `make CXX=` 与 env 都覆写不到、必须打补丁（走 `g++` 垫片违背 R33）；与 cohomcalg 的"变量赋值型"同族不同层
- **关联 Issue**：**#3359 已创建** —— https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3359 （标题【知识库扩展】jnoise 0.6.0：上游把编译器名写在 Makefile 规则的命令位置字面量 ⇒ `make CXX=` 与环境变量都覆写不到、必须打 portability 补丁）
  - **勘误（可核证）**：提交 `e41fcef603` 的**提交说明**自称"notes 的关联 Issue 已回填为 3359"，
    但该提交的真实改动经 `git show --numstat e41fcef603` 复算为 **`notes.md` 4 增 0 删**、且全仓只有
    这一个文件——那 4 行是 `finish` 回写的页脚（`--- / 空行 / **编译结束** / **最终状态**`），
    与本行无关。成因：回填动作的目标串与本文件实际写法不匹配（此处是 `- 关联 Issue:` 非加粗、
    ASCII 冒号），替换未命中而调用方未校验。⇒ 本行由**整改棒 r1 真正写入**，**不改写历史提交**，
    归零判据为本文件**已不含上一版那条英文占位标记**（整改前该标记 1 处、整改后 0 处，
    由 `verifyr1.py` 以字节级计数复核）、且 `grep -c 3359` ≥ 1。
    Issue #3359 的创建与编号由主窗执行（本执行窗按红线未调平台 API，故不复核平台侧标题全文）。
- M18（suckless 烧路径族）**判不命中**的结论不变（见上文 B 判定初判节，主窗已认）。

### 6. 软件级三件套与 PF9（不为凑绿删文件）

- `archives/j/jnoise/README.md`、`archives/j/jnoise/manifest.yaml`、`archives/j/jnoise/commands.json`
  三件齐且在 `git ls-files` 内；`commands.json` 的 `versions` 含 `0.6.0`。
- PF9×1（"变更路径缺版本目录层"）点名的正是这三件软件级文件 ⇒ **G1 结构闸要求它们存在、PF9 判据要求它们不存在，
  属框架互斥判据**，只上报不整改，未删除任何必需文件。

## 收口修订 3（主理-32 整改棒 r1）：按 W4-r1 判决逐条落地

判决件：`~/tmp/uc2/z32-jnoise-w4/audit-result-feat-jnoise-0.6.0.json`（23002 B，
`verdict=fail`，P0=0 / P1=1 / P2=3 / P3=4，绑 HEAD=`e41fcef603`）。本棒逐条处置如下；
**本轮未动 `conanfile.py`、`conandata.yml`、补丁、`test_package/` 与任何测试计数**
⇒ W3 证据链（13 文件集、`integrity_hash`、`log_sha256`）与门禁读数不变，**无需重跑 `conan create`**；
判定按新 HEAD 定向重审即可。

### 1. P1-1（阻塞项）：Issue 占位标记归零

见上一节 `- **关联 Issue**` 行与其勘误子行。三条判据实测结果写在提交流水与
`~/tmp/uc2/z32-jnoise-fix1/verify.txt`（占位标记计数 = 0、`grep -c 3359` ≥ 1、
裸 NUL 字节 = 0、`grep -c $'\r'` = 0）。

### 2. P2-1：W0 第二证据形态作废

已删并降级为勘误（见"依赖（W0）"节）：`conan download … -f` 实为 **rc=2 用法错误**（conan 2.29.1 上
`download` 的 `-f` = `--format`），`-f json` 复跑落 `Skip recipe … already in cache` 属假成功 ⇒ 两条都不再
作发布态证据；W0 只保留 `preflight_check.sh` RC=0 + `[OK] 已发布: jack/1.9.22`（本棒未为补证据再跑
`conan download` 任何变体）。整改棒另在 B 机上只读复跑了一次
`bash ci/scripts/preflight_check.sh jnoise/0.6.0` → **PREFLIGHT_RC=0**（15 行输出、5 条 `[OK]`），
原件 `~/tmp/uc2/z32-jnoise-fix1/preflight-r1.log`（`:8` = `grep -n jack/1.9.22` 首中行即
`[OK] 已发布: jack/1.9.22`；`:10` = R37 版本号占用检查行；`:14` = 末条 `[OK]` 即全部依赖已发布），
与审计的 `w0-recheck.log:8,11,14` 同形。

### 3. P2-2：版本级 manifest 未转绿 / 未填字段（逐条披露 + 已改）

`archives/j/jnoise/0.6.0/manifest.yaml` 尾部两块元数据是框架 `scripts/ohc/refresh_patch.py`
**自动写的占位值**，本包从未走过它的生成链，因此与盘面不一致。已按"先读语义、再改值"处理：

| 字段 | 原值（框架占位） | 依据（框架内注释/写法） | 现值 |
|---|---|---|---|
| `patch_generation.method` | `per-file-difflib` | `refresh_patch.py:512` 由该脚本在自动生成补丁时硬写，属**框架生成链专属取值**；本包补丁是手写 | `manual-portability-patch` + `note` 说明成因 |
| `source_orig_hash` / `source_work_hash` | `pending` | `refresh_patch.py:501-502` 的 `_compute_hash(orig_dir/work_dir)`；本包 finish Step1 报 `无法定位源码目录: orig=None, work=None`（`~/tmp/uc2/z32-jnoise/finish.log:12`）⇒ **框架侧目录哈希根本不存在**，本棒不自造假哈希 | `n/a-manual-patch-no-framework-dirs` |
| `patch_classification[].type` | `auto` | 脚本注释 `# AI should classify later`；与 `conandata.yml` 的 `patch_type: portability` 对齐 | `portability` |
| `patch_classification[].platform_only` | `True` | 脚本注释 `# default assumption for OHOS patches`；实测补丁正文与 `patch_description` 中 `__OHOS__` 等平台宏 **0 处**（PF1–PF6/PF8 零命中，审计在 pristine 树正向/反向 `git apply --check` 全 RC=0）⇒ 与 True 矛盾 | `False` + `platform_only_note` |
| `patch_classification[].guard` | `pending` | 脚本注释 `# AI should fill: __OHOS__ / $^O / none`；本补丁无平台条件守卫 | `none` |

- **判级影响核查（改前做的）**：`grep -rn platform_only|source_orig_hash|source_work_hash|patch_classification|per-file-difflib scripts/ ci/ templates/`
  只命中 `scripts/ohc/refresh_patch.py`（**只有写方，无任何读方/门禁判级方**）⇒ 上述取值改动不影响任何闸口，
  未改判据、未改脚本。
- `platform_only` 的语义取舍：缺陷本身（链接行字面量 `g++`、裸 `install`）**跨平台存在**，
  只是暴露形态随 libc / PATH 而异，所以走的是 **portability 补丁**而非平台条件守卫 ——
  故取 `False` 并另附 `platform_only_note` 说明，而不是靠 True 蒙过审计。

### 4. P2-3：探针原始输出件已实跑落盘（本轮唯一需真机执行项）

见"JACK 运行面探针"节：脚本修了 2 个自身缺陷（`sys.argv[1]` 的 `IndexError`、`shm_open` 少了 `O_CREAT`），
输出件 `~/tmp/uc2/z32-jnoise-fix1/probe-out-20260925-045907.txt`（59 行，sha256 前 16 位 `a05bce0748d2bf39`），
notes 里三层的引用已全部改成**该件的路径 + 行号**。**由此更正了一条旧结论**：
`shm_open(O_RDWR|O_CREAT)` 在本机是 **成功**的（fd=4、写读一致、落点 `/dev/shm/jnoise-z32-probe`），
上一棒的 `ENOENT` 出自探针 flags 写法缺陷 ⇒ "无 shm 落点"的说法作废；`jack_client_open` 的
`NULL / errno=2 / status=0x11` 三条**逐字复现**（`:27`、`:57`）。

### 5. P3 四条的处置

- **①（审计 P3-2，A2 描述强于实现）**：notes 侧措辞已降到与实现一致，并写明"补成解析 `DT_NEEDED`
  属测试代码改动"。`test_package/conanfile.py:9-10` 与 `MANIFEST.yml:25` 的同源措辞**未改**
  ⇒ 见下条"需主窗决策"。
- **②（审计 P3-1，A5 是 A4 的前缀子串）**：弱点已在测试账本明写（判别力只来自输入不同）。
  改断言去押"不同输出面/不同退出码组合"属测试代码改动 ⇒ 同上，本轮不动。
- **③（执行期局部件不得充作 W3 结论）**：已在"收口修订 2 §1"就地加了限定——W3 只认
  `reports/w3-local-ci.log:73` 的 `incremental (13 个文件)`，`JC_RESULT=pass: empty`（非 git 目录）与
  `incremental (11 个文件)` 均降为执行期局部件，原文保留不删。
- **④（`conan download -f`）**：与 P2-1 同条，已在 W0 节作废。

### 6. 审计另两条 P3 建议（判决件里有、任务书未列）：一条加注、一条不改

- **P3-3（`ci-metadata.json` 的 `build_trace.commit = unknown`）**：属机器元数据未绑 sha，
  本棒按审计建议改为在 notes 记绑定链，不改 `ci-metadata.json`（改它即动 W3 产物、会触发重跑与
  `result.json` 重生成）：`.ci-result.json.timestamp == 文件 mtime(1790279677) == integrity_hash
  可复算 == log_sha256 == sha256sum(reports/w3-local-ci.log)`，且 13 文件集与
  `git diff --name-only origin/main...HEAD` 逐字相同（W4-r1 独立复算，见判决件 `verified_green` 第 2 条）。
- **P3-4（草稿 `error_signature` 含裸分支 `Error 127`）**：**本轮未改**。理由：`error_signature`
  参与 `draft-review` 的相似度计算（判决件记 `E248 sig=0.34`），改签名会使已登记的预审判据与本包正文
  引用的数字失去同源，属"外观字段动 HEAD"的反面；且审计自列非门禁。**建议主窗决策**：若下一棒要收紧，
  应改成 `Error 127$` 与 `g++` 同行约束，并同批重跑 `draft-review` 与预筛自测。

### 7. 需主窗决策（本棒按红线未动）

1. `test_package/` 的两处措辞（`conanfile.py:9-10` docstring、`MANIFEST.yml:25` description）与
   A2/A5 的实现补强——任何改动都会作废 W3 证据链并白烧一次构建，**整改棒无权自行决定**。
2. 草稿 `error_signature` 是否收紧（上条 P3-4）。
3. 平台侧 Issue #3359 的标题全文与正文是否需按本 notes 的机制表述复核（本棒未调平台 API）。
---

**编译结束**: 2026-09-25 03:54
**最终状态**: built
