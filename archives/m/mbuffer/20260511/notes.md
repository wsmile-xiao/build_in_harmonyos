# mbuffer 20260511 — HarmonyOS PC 适配笔记

- 上游：Thomas Maier-Komor，`https://www.maier-komor.de/mbuffer.html`
- 源码：`https://www.maier-komor.de/software/mbuffer/mbuffer-20260511.tgz`
  sha256 `13bab36f39408f7a08fb368913290ad0f117c934bab602094e18fcc123ec5783`，156683 B
- 归档：`archives/m/mbuffer/20260511/`，分支 `feat/mbuffer-20260511`
- 构建主机：B 机（HarmonyOS aarch64，HongMeng Kernel 1.12.0，clang 15.0.4，conan 2.29.1）
  —— 2026-09-30 链主在 B 机续跑；B 机缺 `~/usr/local/bin/perl` 链且真实 automake 的
  内联 `@INC` 指向不存在的 `automake-1.17`（装机树为 `automake-1.16`），用
  `~/tmp/uc2/主理-1-mbuffer/bin/{automake,aclocal}` PATH wrapper（`PERL5LIB` +
  `AUTOMAKE_UNINSTALLED=1` + hnp perl）后 `automake --version` 回 `1.16.5` rc=0。
- 语言预检（R47）：`task=cpp, detected=c` → 匹配（c↔cpp 同族）
  证据：`源文件 12 个（c:12, bash:9），主体占比 100%`，manifest=`CMakeLists.txt project(mbuffer C)`，
  构建系统判定 cmake（`make` 与 `cmake` 两条并存，见下节）

## 1. 构建系统选型：两套并存，取 autotools

上游同一份 tarball 里同时给了 `configure`（由 `configure.in` 生成，随包发布）+ 手维护的
`Makefile.in`，以及一份 `CMakeLists.txt`（配 `config.h.cm`）。登记表档位记的是
"autotools + CMake 双构建系统"，实物核对后**取 autotools**，理由全部来自盘上原文：

| 依据 | autotools | CMake |
|---|---|---|
| 上游自述流程（`INSTALL`） | `./configure` → `make` → `make install` → `make check` | 未提 |
| 测试注册 | `Makefile.in:99` `check: $(TARGET) test0 … test7`（8 个） | `add_test` 8 个，但整段被 `if (ENABLE_TESTING)` 圈住（非标准开关，默认不开） |
| 安装规则 | `install:` 装 `bin/mbuffer` + `man1/mbuffer.1` + `etc/mbuffer.rc` | `install(FILES mbuffer DESTINATION bin)` —— 归档里**没有名为 `mbuffer` 的源文件**（只有 `mbuffer.c`），该规则装的是源码树路径而不是构建产物 target |
| 测试工作目录 | 与构建目录一致，脚本里的 `../mbuffer`、`-i INSTALL`、`cat mbuffer` 全部成立 | `WORKING_DIRECTORY tests` 是相对**构建**目录的路径，而 `tests/` 只存在于源码目录 |

⚠ 结论：**这不是"两个都能用，随便挑"**，而是 CMake 那条路的安装与测试步骤在本包上按原文跑不通。
本 PR 不改框架、不动上游 CMakeLists.txt，只走 autotools。

## 2. 适配点逐条（症状 → 根因 → 最小复现 → 失败方案 → 最终方案 → 边界）

### 2.1 `./configure` 猜不出平台（补丁 0002 / 0003）

**症状**
```
checking build system type... ./config.guess[1680]: can't create /storage/Users/currentUser/cgBblIt7/dummy.c: Permission denied
./config.guess: unable to guess system type
This script (version 2022-01-09), has failed to recognize the operating system you are using.
configure: error: cannot guess build type; you must specify one
```
打完 config.guess 补丁后的第二条症状：
```
checking build system type... Invalid configuration `aarch64-unknown-linux-ohos':
Kernel `linux' not known to work with OS `ohos'.
configure: error: /bin/sh ./config.sub aarch64-unknown-linux-ohos failed
```

**根因**（两处，都是既有条目）
1. `config.guess` 2022-01-09 版没有 `HarmonyOS` 分支（**E007**）；
2. `config.sub` 缺 **E072 的三处改动中的第三处** —— `case $kernel-$os` 白名单里没有 `linux-ohos*`。

**最小复现**（不涉及 mbuffer 逻辑）
```sh
sh ./config.guess                              # 打补丁前：unable to guess system type
sh ./config.sub aarch64-unknown-linux-ohos     # 只打 1、2 处时：Kernel `linux' not known to work with OS `ohos'
```

**已试过的失败方案**
- 框架自带的一键工具 `perl scripts/patch-autotools-ohos.pl config.guess config.sub`
  **不能用**。它输出 `[skip] linux-ohos already present`，于是**漏掉 E072 的第三处**：
  它的存在性检查命中的是它自己刚写进 `basic_os` 映射里的那行 `basic_os=linux-ohos`
  （`config.sub:158`），而不是 `case $kernel-$os` 白名单（`config.sub:1779`）。
  打完它 `./config.guess` 能出三元组，但 `config.sub` 仍拒绝该三元组 → configure 照旧失败。
  ⇒ 本包在工具产物之上再补第三处，合进 `0003-config.sub.patch`（工具是框架文件，本 PR 不改）。

**最终方案**：`0002` 加 HarmonyOS 机器名分支 → `aarch64-unknown-linux-ohos`；
`0003` 一次给齐 E072 三处（`ohos-linux` 映射、`ohos*` OS 白名单、`linux-ohos*` kernel-OS 白名单）。
两者都是**纯增量**，不影响既有平台分支。

**边界**：凡是随包发布 2022 年及更早 `config.guess`、且 `config.sub` 未含 `linux-ohos*` 的
autotools 包都适用；**用工具打完补丁不等于过检**，判据是 `sh config.sub $(sh config.guess)` 必须原样回显三元组。

### 2.2 `config.status` 建不出临时目录（补丁 0004，E011/E129/E543）

**症状**
```
config.status: executing default commands
./config.status[704]: can't create ./confNoD0ZU/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```
**根因**：autoconf 模板用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录；HMDFS 会对新建目录强加
setgid，`077` 掩码下落成 `drwx--S---`，属主自己反而写不进去（**E011 / E129 / E543** 同一族）。
**最小复现**：`(umask 077 && mktemp -d ./confXXXXXX)` 后往里 `cat > file` → `Permission denied`；
去掉 `umask 077 &&` 后同一操作成功。
**失败方案**：只改 `config.status`。它是 configure 生成的，`conan create` 每次从干净源码重跑
configure，改动当场丢（且 `sed -i` 在 HMDFS 上会把生成的 config.status 打成 000）。必须改 `configure` 里那一行。
**最终方案**：`0004` 删掉 `configure` 里这两处的 `umask 077 &&`（与已合入的 `archives/a/abook/0.6.1/patches/0006-configure.patch` 同形）。
E011 的 `077→022` 写法在本机实测也够（A 机 toybox `mktemp` 认 umask），但 E543 记录过"022 仍拿到不可写目录"的环境，
删除该子句对两个环境都成立，故取删除形。
**边界**：仅影响 autoconf 自建临时目录的两行；不改任何编译/链接参数。

### 2.3 `make -j2` 起不来（配方内 `-j1`，E074/E525）

**症状**：`make: jobserver mkfifo: /storage/Users/currentUser/GMfifo10782: Operation not permitted`
**根因**：鸿蒙 SELinux 策略禁止用户进程创建 FIFO，GNU make 的 jobserver 依赖它（**E074 / E525**）。
**最小复现**：`make -j2` 立即报该行；`make -j1` 正常。
**失败方案**：`MAKEFLAGS=-j1`（外层仍会尝试 jobserver）；把并行度写进 `config.h`。
**最终方案**：配方内所有 make 调用一律显式 `-j1`。本包只有 9 个 C 文件，串行成本可忽略。
**边界**：任何用 GNU make 且需要并行的包都受此限；OOM 防线另算（走 gate/slot）。

### 2.4 链接期缺 `pthread_cancel`（补丁 0005，E085）

**症状（第一条真实错误）**
```
mbuffer.c:177:10: warning: call to undeclared function 'pthread_cancel'
ld.lld: error: undefined symbol: pthread_cancel
>>> referenced by mbuffer.c:177 (.../mbuffer.c:177)  >>> build/mbuffer.o:(main)
```
**根因**：本平台 libc（musl 变体）**既不声明也不导出** POSIX 线程取消三件套（**E085 / E127**）。
`knowledge/musl-glibc-full-comparison-iso-posix.md:1747` 把 `pthread_cancel` 标为 OHOS ✅，
与本条实测冲突（同一份对照表在 2563 行对 `RTLD_NEXT` 的 ✅ 是准的）—— 以实测为准。
**最小复现**：`clang -o t t.c -lpthread`，`t.c` 里 `#include <pthread.h>` 后调 `pthread_cancel(0)` → 同上两条。
**失败方案**
1. 直接 `if (0)` 短路掉取消调用 → 违反 R6"守卫必须有实质逻辑"，且在 glibc 上静默丢掉行为；
2. 只加 `#pragma weak pthread_cancel` 不写声明 → musl 没有原型，clang 仍报
   `call to undeclared function`，弱声明也没建立起来（**E321** 记的正是这个失败面）。
**最终方案**：`#pragma weak` **配显式 extern 原型**，调用点改成 `if (pthread_cancel) pthread_cancel(...)`。
验证不是"rc=0"而是符号表：
```
$ objdump -T mbuffer | grep pthread_cancel
0000000000000000  w   D  *UND*  0000000000000000 pthread_cancel
```
`w` = 弱未定义解析为 0；同表里 `pthread_join` 是强 `DF *UND*`，作正向对照。
语义上不丢东西：`cancelAll()` 只在 `joinSenders()` 里、且**仅在 `Terminate` 已置位后**调用，
各工作线程本来就靠 `Terminate` 协作退出，随后每个 `pthread_join()` 照旧回收。
**边界**：适用"libc 不导出取消 API 但线程有协作退出标志"的包；若某包的线程**必须**靠取消点才能退出，
本方案只会把"链接失败"变成"挂住"，那类包必须改走 E513 的 `pthread_kill + pthread_join` 形态。

### 2.5 默认 make / make install 缺两条生成物依赖边（合进补丁 0001；W3 已实证）

**症状（两条，同一族）**
1. 干净源码 `./configure && make` 编 settings.c 报 `fatal error: version.h file not found`；
2. 干净源码 `make && make install` 报 `ginstall: cannot stat 'mbuffer.1': No such file or directory`。

**根因**：上游 `Makefile.in` 里 `version.h: always` 会跑 `bash mkversion.sh`，而该脚本**同时**产出
`version.h` 与 `mbuffer.1`。但 `version.h` 不在任何目标的依赖链上（`all:` 只依赖
`$(TARGET) idev.so tapetest.so have-af`），`mbuffer.1` 更是**只作为 `version.h` 规则的副产物**存在、
本身没有规则、也没有任何目标依赖它（`install:` 只依赖 `$(TARGET)` 与 `mbuffer.rc`，却在配方里
`$(INSTALL) -m 644 mbuffer.1 …`）。⇒ 上游文档的 `make && make install` 在干净树上必失败。

**最终方案（两条边都补，缺一不可）**：`0001-Makefile.in.patch` 里
- `$(OBJECTS): config.h Makefile` → `… Makefile version.h`；
- `install: $(TARGET) $(DESTDIR)$(etcdir)/mbuffer.rc` → `… /mbuffer.rc mbuffer.1`。

只补第一条边时首次 `make` 能连带产出 man 页（`mkversion.sh` 走 `[ ! -f version.h ]` 分支时会顺带 `$SED … > mbuffer.1`），
但 `version.h` 已是最新时脚本直接 `rm $NEWFILE; exit`、**不碰 mbuffer.1** ⇒ 增量重放或有人删过 man 页时
`make install` 照旧 `cannot stat`。补上第二条边后 `make && make install` 在任何起点都成立。

**最小复现（干净树，逐条可跑）**
```sh
tar xzf mbuffer-20260511.tgz && cd mbuffer-20260511
for p in patches/0001…0005; do patch -p1 -i $p; done
./configure --prefix=$PWD/../inst && make -j1
rm -f mbuffer.1 && make install DESTDIR=$PWD/../d    # 补第二条边前：cannot stat 'mbuffer.1'
                                                     # 补上后：重生成 man 页并安装成功
```

**边界**：修的是 autotools `Makefile.in` 的依赖声明；不改编译/链接参数、不删 man 页、不吞 install 错误、
不改任何判据。§8 记录的 CMake 安装/测试路径缺陷不在本次选择路径内。

**证据**：`conan-verify` G0（clean-build-verify，含 `make install DESTDIR=`）**PASS**；
G2 `conan create` 8 项上游测试 `test0..test7` 全 rc=0；`.ci-result.json exit_code=0`。

### 2.6 `mkversion.sh` 需要 bash，`/bin/bash` 不存在

**症状**：`sh` 下跑 `mkversion.sh` 会走到 `[ "$?" == "0" ]`（bashism），且脚本 shebang 是 `#!/bin/bash`。
**根因**：鸿蒙只有 `/bin/sh`（toybox ash），bash 在 `~/.harmonybrew/bin/bash`（`/data/service/hnp/bin/bash` 也有）。
**最终方案**：不改脚本。`configure` 的 `AC_PATH_PROG(SH, bash sh)` 会把 `SHELL=@SH@` 解析成真实存在的
bash（本机为 `/storage/Users/currentUser/.harmonybrew/bin/bash`），`make` 用的是 `@SH@` 而不是硬写
`/bin/bash`，所以配方侧零补丁。
**边界**：只有当包把 `/bin/bash` **硬编码进产物**（脚本安装件）时才需要额外处理，本包没有。

## 3. 测试账本（R51 / 手册04 §10.1 五维）

上游测试取证按"实物清单 + 跨框架六类标记"手工扫描，**没有使用**
`ci/tools/extract_upstream_tests.sh`（该脚本硬编码 `/tmp`，设备 `/tmp` 只读 ⇒ 其日志只有失败记录，
不得当证据）。原始输出在 `~/tmp/uc2/z41-mbuffer/`。

| 维度 | 数 | 取证入口 |
|---|---|---|
| `N_static`（上游静态声明） | **8** | `tests/test0.sh … test7.sh` 共 8 个脚本（`tar tzvf` 全清单） |
| `N_registered`（构建系统注册） | **8** | `Makefile.in:99` `check: $(TARGET) test0 … test7`；`CMakeLists.txt:177-184` 8 个 `add_test` |
| `N_executed`（本配方实际执行） | **8** | 配方 `build()` 逐 target 跑 `make -j1 test0 … test7`，每项一个退出码 |
| 未执行 / 跳过 | **0** | 见下"条件分支" |
| `N_consumer`（新增消费者测试） | **9** | `test_package/conanfile.py` 5 条 + `test_package/mbuffer_probe.sh` 4 条 |

**条件分支必须单独交代**（不得静默并入"通过"）：`test2`/`test3` 上游自带
`have-af inet` / `have-af inet6` 门禁，探测失败时脚本会 `echo SKIPPING` 走本地拷贝路径并**仍然返回成功**。
本机实测两个探测都返回 0（IPv4/IPv6 均可用）：
```
./have-af inet   rc=0
./have-af inet6  rc=0
```
⇒ 网络分支**真的执行了**，不是上游那层假通过。

**为什么逐 target 而不是 `make -j1 check`**：`check` 这个目标本身没有退出码可谈，
它在**第一个失败的前置项**处整体中止，且 `test0…test5` 是 `touch` 生成的文件目标，
跑完再跑第二个 `check` 会是空操作 ⇒ 拿不到逐项判决。逐项调用跑的就是 `check` 的 8 个前置项本体。

**探索阶段判决行**（`~/tmp/uc2/z41-mbuffer/13-build.txt`，此时**尚未**接入 OpenSSL）：
```
RESULT test0 rc=0     RESULT test4 rc=2
RESULT test1 rc=2     RESULT test5 rc=2
RESULT test2 rc=0     RESULT test6 rc=0
RESULT test3 rc=0     RESULT test7 rc=2
```
四个失败**同一条根因**，不是四个缺陷：
```
mbuffer: error: invalid or unsupported hash function MD5
```
即 §4 的哈希后端缺失；接入 OpenSSL 后由 `conan create` 复跑取终态数字
（终态判决行见 `reports/` 与 `~/tmp/uc2/z41-mbuffer/` 的 W3 日志）。

## 4. 依赖与哈希后端（W0）

**本配方 `requires()` = `openssl/3.5.6.1`**（第 1 轮曾为空，靠探测宿主；CI 判红后改为 conan 依赖，见 §4.1）。

`hashing.c` 有三条哈希供给路径：

1. **编译期内置**：`configure` 的 `AC_SEARCH_LIBS(MD5_Init, crypto)` 命中则
   `HAVE_LIBCRYPTO` → `WITH_SSLMD5` → `--md5` 可用；
2. **运行期 dlopen**（可选，不是构建依赖）：`dlopen("libmhash.so")`、
   `dlopen("librhash.so.0")`、`dlopen("libgcrypt.so.20")`；
3. 都没有时 `listHashAlgos()` 直接 `fatal("no hash calculation libraries could be found!")`。

本机 dlopen 面实测（独立探针，见 §5）：三条 soname **全部加载失败**，
`errno=2 (ENOENT)`、`dlerror()` 原文 `Error loading shared library <name>: No such file or directory`
⇒ 设备上没有这三枚库，第 2 条路在本平台为空。

第 1 条路必须给上，否则 test1/test4/test5/test7 全红。取**已发布的 conan 依赖**
`openssl/3.5.6.1`：`generate()` 从 `self.dependencies["openssl"].cpp_info` 取绝对
`includedirs` / `libdirs` / `bindirs`，把 `-I<inc>` 加进 **CFLAGS**、`-L<lib>` 加进 LDFLAGS，
并把这三个目录落盘（`mbuffer_openssl_dirs.txt`）供 `build()` 回读，全流程只解析一次。

⚠ 为什么进 CFLAGS 而不是 CPPFLAGS：`Makefile.in:22` 是
`CFLAGS = @CFLAGS@ $(DEFS) -I@srcdir@ -I.`，编译命令只有 `$(CC) $(CFLAGS) -c` ——
**CPPFLAGS 根本不上编译行**，走 `AutotoolsToolchain` 默认的 `CPPFLAGS` 注入会静默失效。

补丁 `0001-Makefile.in.patch` 把两处写死的依赖工具变成可覆盖变量（默认值保持上游原样）：
- `TARGFLAGS = --ignore-failed-read`：`test.tar` 前置项用 `$(TAR) cf test.tar --ignore-failed-read /bin /usr/bin`；
  设备 `tar` 是 **toybox 0.8.12**，实测 `tar: Unknown option 'ignore-failed-read'`，且 `/usr/bin` 不存在。
  配方调用时覆盖为 `TARGFLAGS=` + `TESTTREE="*.c *.h"`（用本包源码当测试载荷，实测 173568 B）。
- `OPENSSL = openssl`：10 处写死的 `openssl md5` 改成 `$(OPENSSL) md5`，由配方传
  **依赖包内 `bin/openssl` 的绝对路径**（同一依赖、不依赖构建环境 PATH）。

**W0 结论**：`openssl/3.5.6.1` 已发布（`conan download --only-recipe` rc=0；
`conan install --requires=openssl/3.5.6.1 --build=never` 用 ohos-aarch64 profile 命中远端
binary，非本地构建产物）。该版本 recipe 硬写 `no-shared`、只有 `fPIC` 选项 ⇒ `-lcrypto`
解析到静态 `libcrypto.a`，装出的 `bin/mbuffer` 不带运行期 `libcrypto` 依赖。
`preflight_check.sh` 复跑判决行见 `reports/`。

### 4.1 为什么不是"探测宿主"（第 1 轮 CI 判红复盘）

第 1 轮配方 `requires()` 为空，`generate()` 按候选前缀探测宿主
（`~/.harmonybrew/opt/openssl@3`、`~/.harmonybrew`、`/usr/local`、`/usr`）。
本机（B 机）命中 `~/.harmonybrew/opt/openssl@3`，本地 W3 8/8 绿；
**CI worker 四个前缀全无该头**，探测落空后 configure 原文判负：

```
checking for library containing MD5Init... no
checking for md5.h... no
checking for library containing MD5_Init... no
```

⇒ `HAVE_LIBCRYPTO` 未定义 ⇒ `--md5` 运行期报
`mbuffer: error: invalid or unsupported hash function MD5` ⇒
`UPSTREAM_TEST_VERDICTS test0=0 test1=2 test2=0 test3=0 test4=2 test5=2 test6=0 test7=2`。
**教训**：宿主探测失败是静默降级（configure 只是"没找到"），本地绿完全不能推出 CI 绿；
构建输入必须来自 conan 图。本轮改为显式依赖，并把 `md5.h` 的存在性做成 `generate()` 里的
fail-closed 断言（缺头直接抛 `ConanException`，而不是编译出一个没有哈希后端的二进制）。

### 4.2 第 2 轮一手取证（conan 依赖版，全部取自本轮归档日志/产物）

| # | 读数 | 出处（可复跑） |
|---|---|---|
| ① | `checking for library containing MD5_Init... -lcrypto` | `reports/w3-local-ci.log:258` |
| ① | `#define HAVE_LIBCRYPTO 1` | 本轮 W3 构建目录 `config.h:40`（`/* #undef HAVE_MD5_H */`、`/* #undef HAVE_LIBMD5 */` 同屏） |
| ② | `openssl:md5 hash: 0e36e7f911aea95e2603c2beee205e7a` | 包内 `bin/mbuffer -q --md5 -i <262144B 载荷> -o /dev/null`（与独立 `md5sum` 同值） |
| ③ | `(NEEDED) Shared library: [libc.so]`（**无** `libcrypto`，无 `RPATH`/`RUNPATH`） | `llvm-readelf -d <pkg>/bin/mbuffer` |
| ④ | `UPSTREAM_TEST_VERDICTS test0=0 test1=0 … test7=0` = **8/8** | `reports/w3-local-ci.log:546` |
| ⑤ | G0–G3 全 PASS；`.ci-result.json` `exit_code=0`、`log_sha256=a3f30ab9…` | `reports/conan-verify-report.md`、`.ci-result.json`（与 `reports/w3-local-ci.log` 实测 sha256 一致） |

配置注入原文（本轮日志）：编译行 `-I<conan pkg>/include`、链接行 `-L<conan pkg>/lib … -lcrypto -lpthread`、
测试驱动 `OPENSSL='<conan pkg>/bin/openssl'` —— 三处都是 conan 包内绝对路径，无宿主前缀参与。

**本地发布件（packaging/）口径**：`packaging/mbuffer-20260511-ohos-aarch64.tar.gz` 由 W3 验证过的
conan 包目录（`.../p/b/mbuff806ccb6b3ddad/p`）直接重打包，其 `bin/mbuffer` sha256
`f112adcf21f2dcd8fc027e68d21c19d199e2f00c50e84398c30c0fbda70c200c` 与被验证包内件**逐字相同**，
`--md5` 冒烟同样输出 `openssl:md5`。刻意不经 `ohc package` 的 `patchelf` 改 RPATH 与重新签名两步——
那两步会改变字节（静态包已无外部 `.so` 需要 RPATH），从而与被验证件不同 sha256。`packaging/` 已由
`.gitignore:2` 忽略、不进 PR。

## 5. 探针 #11 读数：`dlopen` / `dlsym(RTLD_NEXT)`（OHOS行为探针清单 #11）

**独立性**：`~/tmp/uc2/z41-mbuffer/probe2/{interp.c,cons.c,run.sh}`，30 行级、不含任何 mbuffer 代码。
原始日志 `~/tmp/uc2/z41-mbuffer/12-probe2.txt`。

| 臂 | 读数 |
|---|---|
| A `dlsym(RTLD_NEXT,"write")` 在**主可执行文件**里（无预载件） | 返回非空 `0x59f927d004`，`dlerror()=none` |
| B `LD_PRELOAD=<用户目录下自编译 .so>` 拦 `open`/`read`/`write` | **拦截生效**：`HIT open=2 HIT read=2 HIT write=1`，三行 `RESOLVE … -> 非空 err=(none)` |
| C 正向对照（比基线臂更早） | 装载器在进入 main 之前就命中 `HIT open /proc/self/unexpected_die_catch` ⇒ 从进程启动即在位 |
| D `hashing.c` 式裸 soname dlopen | 三枚全 `handle=0`，`errno=2`，`dlerror: Error loading shared library …: No such file or directory` |
| E 绝对路径 dlopen 本机组件 | `handle=0x9ab5b598e39be570` 非空，`dlsym(handle,"open")` 解析成功 |
| F `RTLD_NOLOAD` 复查 | 与 E 同一 handle ⇒ 预载件确在进程映像内 |
| 对照臂（无 `LD_PRELOAD`） | `HIT=0 RESOLVE=0` ⇒ B 的命中不是噪声 |

**与 mbuffer 的相关性**：本包 `idev.so`（test6）/ `tapetest.so`（test4、test5）就是这套机制的
上游生产件。三臂在盘上原样跑通，判决行（`~/tmp/uc2/z41-mbuffer/13-test4.log`）：
```
[INTERCEPT] write(block 5): ENOSPC (early)
[INTERCEPT] open: output-test4, intercepted and writing as output-test4.003
```
`RESULT test6 rc=0`。⇒ **RTLD_NEXT 拦截链在本平台功能可用**（本交互构建主机）。

**读数落在既有条目覆盖范围内**（宽口径检索，逐词单查，命令与命中数见下）：
- `knowledge/operations/ptrace-alternatives.md:91/137/155/265` —— 已把
  "LD_PRELOAD + `dlsym(RTLD_NEXT,"open"/"read")`"标为 **✅ 已验证可用**，连函数名都对得上；
- `knowledge/musl-glibc-full-comparison-iso-posix.md:2563` —— `<dlfcn.h>` 对照表 `RTLD_NEXT` OHOS ✅（本次实测复核为真）；
- `knowledge/drafts/DRAFT-purelibc-1.0.8-ohos-musl-fopencookie-deviation.kv:40` —— 已在 musl 上用
  `dlsym(RTLD_NEXT,…)` 作惰性回退并交付通过；
- `knowledge/doc/E502.md` / `E212.md` —— 划的是"**CI worker** 拒绝用户目录 dlopen/LD_PRELOAD"这条界，
  与本读数（设备可用）不冲突；`knowledge/doc/E543.md` 是 HMDFS 文件模式 660，属另一条链；
- `DRAFT-libmongocrypt-…-dlinfo-absent-ohos-dladdr` —— 本读数里 dlopen handle 是
  `0x9ab5…be570` 这种脱敏指针，与该条目一致，无新增。

检索命令（每条单独跑，不用"两词同行"正则判"没人写过"）：
```
grep -rniI -- "RTLD_NEXT"   knowledge/  → 11
grep -rniI -- "dlsym"       knowledge/  → 82
grep -rniI -- "dlopen"      knowledge/  → 679
grep -rniI -- "interpose"   knowledge/  → 3
grep -rniI -- "LD_PRELOAD"  knowledge/  → 160
grep -rniI -- "preload"     knowledge/  → 187
```

**结论建议：`B判定=none`（不建 DRAFT、不建 Issue）**。理由：探针 #11 的读数与
`ptrace-alternatives.md` 已验证结论同形；且本包全部障碍逐条命中既有条目
（E007 / E072 / E011 / E129 / E543 / E074 / E525 / E085 / E127 / E321 / E002 / E010 族 / E502）。
"没有新增可跨库复用机制"是本包判 none 的依据，不是"懒得判"。

**唯一带走的残险（交主代理定夺，不构成本包缺陷）**：E502 记的"CI worker 拒绝用户目录
LD_PRELOAD"若在本 PR 的远端 CI 上成立，test4/5/6 会在 CI 侧红而本地绿。
处置权在 CIW：既不许为此放宽断言，也不许把 `check` 摘掉，先按 CI 判决取证再分类。

## 6. 其它平台细节（都已在实现里落实）

- `/tmp` 只读（**E002**）：`mkversion.sh` 会 `mktemp -t version.h.XXXXXXXXXX` 落到 `/tmp`。
  配方 `generate()` 用 `Environment` 把 `TMPDIR/TMP/TEMP` 指向构建目录（不裸读 shell 变量，合 R33）。
- 安全弹窗（**R7 / E054**）：新编译产物首跑可能弹确认框。本机本次未弹（`./mbuffer --version`、
  8 项测试、探针二进制均直接执行成功）；远端 worker 若命中需按 E543 处理。
- 未做 ELF 自签：本包归档不含任何预编译 ELF（`make install` 在构建期产出），
  且本机执行链未因缺签名失败；SKILL §Step5 表明签名在 release 流水线的 `ci/artifacts/sign.sh`。
- `mt` 不存在：`configure` 只用 `AC_PATH_PROG(MT, …)` 出告警（自动装载器支持），不阻塞。
- `TAR=@TAR@` 解析到 `/usr/bin/tar`（toybox），已由 `TARGFLAGS` 化解（见 §4）。

## 7. 验证命令（复现口径）

```bash
export PATH="$HOME/usr/local/bin:$HOME/.local/bin:$PATH"
export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem"
export CONAN_HOME="$HOME/tmp/ch/home-mbuffer"
cd ~/qzy/主理-41-mbuffer-20260511
bash ci/scripts/preflight_check.sh mbuffer/20260511
python3 scripts/ohc-run.py recipe-search mbuffer
python3 scripts/ohc-run.py build mbuffer 20260511
python3 scripts/ohc-run.py conan-verify mbuffer 20260511
python3 scripts/ohc-run.py finish mbuffer 20260511 built
python3 scripts/ohc-run.py graph validate
# 手工等价扫描（替代不可用的 extract_upstream_tests.sh）
tar tzvf ~/tmp/uc2/z41-mbuffer/src/mbuffer-20260511.tgz | grep -E 'tests/|\.sh$'
grep -rnE 'Test::More|use_ok|def test_|TEST_CASE|add_test|enable_testing' mbuffer-20260511/
find mbuffer-20260511 -maxdepth 2 -type d \( -name t -o -name tests -o -name test -o -name spec \)
```

## 8. 已知限制（对外披露口径）

1. `--md5` 走 OpenSSL 3.x 的**已废弃低位 API**（`MD5_Init/Update/Final`），本平台
   OpenSSL 由 `requires` 的 `openssl/3.5.6.1` 静态提供（不依赖宿主）。上游未迁 EVP，
   本包不改上游。libmd5 / mhash / rhash / gcrypt 四种后端在本设备均不可得（§4/§5 实测）。
2. POSIX 线程取消在本平台不存在，取消调用被弱符号短路（§2.4）；协作退出路径未改，
   `pthread_join` 回收链完整。
3. `test2/test3` 依赖 IPv4/IPv6 环回与 TCP 监听；本机 `have-af` 双 0，故真跑。
   无网环境会退回上游自带的 SKIPPING 分支并返回 0（上游行为，未改动）。
4. 上游 CMake 路径的 `install(FILES mbuffer …)` 与 `WORKING_DIRECTORY tests` 缺陷**未修**，
   本 PR 只走 autotools（§1）。
5. `mbuffer --version` 打印的是上游 hg 标签 `R20260511`（由 `mkversion.sh` 从
   `.hg_archival.txt` 取），与 Conan 版本串 `20260511` 是两个层面的标识，未做"归一化"。

## 9. G0: default make path must generate version.h and mbuffer.1

**Symptom:** 干净源码走上游文档的 `make && make install`，install 时报
`ginstall: cannot stat 'mbuffer.1': No such file or directory`；只跑 `make` 时先在
settings.c 报 `fatal error: version.h file not found`。

**Cause:** `version.h: always` 会跑 `bash mkversion.sh`，该脚本**同时**产出 `version.h`
与 `mbuffer.1`；但 `version.h` 不在任何目标的依赖链上，`mbuffer.1` 更是只作为该规则的副产物
存在（自己没规则、也没目标依赖它），而 `install:` 的配方里却要装它。

**Fix:** 两条缺失的依赖边都补在 `patches/0001-Makefile.in.patch` 里（见 §2.5 与下表）：
`$(OBJECTS): config.h Makefile version.h` 与
`install: $(TARGET) $(DESTDIR)$(etcdir)/mbuffer.rc mbuffer.1`。

> **为什么合进 0001 而不是独立成 0006/0007**：`finish` 的 step [1/10] `refresh-patch --auto`
> 是**按被改源文件逐文件重生成补丁**（本包 5 个被追踪文件 ⇒ 5 枚补丁，一文件一枚）。
> 同一文件的第二、三枚补丁会被它吸收进该文件那枚、随后从 `patches/` 里删除 ——
> 独立编号对同一文件**不稳定**。⇒ 本包的依赖修复以 0001 的一个 hunk 形式承载，
> 语义在 `conandata.yml` 的 `patch_description`、`manifest.yaml` 的 `knowledge_gained`
> 与本文件里写清。

### 9.1 ★补丁行号必须按"打完前面补丁之后"的文件算（本包真实红点，已修）

`0001-Makefile.in.patch` 往 Makefile.in 顶部加了 3 行（`TARGFLAGS` / `OPENSSL` + 一行注释），
因此**同一枚补丁的后续 hunk、以及其后任何补丁**里 `$(OBJECTS)` / `install:` 的行号都要 **+3**：

| 目标行 | 干净源码 | 打完 0001 的前半段后 |
|---|---|---|
| `$(OBJECTS): config.h Makefile` | 54 | **57** |
| `install: $(TARGET) $(DESTDIR)$(etcdir)/mbuffer.rc` | 87 | **90** |

历史形态（主理-46 的 0006）沿用干净源码的 `@@ -51,7 +51,7 @@`，两次假绿/真红都由此而来：

- 平台 `patch`（toybox 0.8.12）**静默放过**（rc=0 且文件真被改）⇒"补丁全 rc=0"给出**假绿**；
- conan 的 `apply_conandata_patches`（python `patch_ng`，严格行号匹配）在 G2 **直接拒收**：

```
WARN: 0006-...patch: hunk no.1 doesn't match source file at line 51
WARN:   expected: b''
WARN:   actual  : b'TESTTREE\t= /bin /usr/bin'
ERROR: ... Error in build() method, line 147 apply_conandata_patches(self)
```

⇒ **判据不能只看"平台 patch rc=0"**。两种解析器都要过：平台 `patch`（G0 clean-verify 用）
与 python `patch_ng`（conan G2 用）。本包复用的校验片段：

```python
from patch_ng import fromfile          # conan 侧同款解析器
for p in sorted(glob.glob("patches/0*.patch")):
    assert fromfile(p).apply(root="."), p     # 必须按补丁顺序
```

### 9.2 两条实测更正（避免后来者重复摸索）

1. **toybox `patch` 能吃多 hunk**：本平台 `/usr/bin/patch` 是 toybox 0.8.12，但重生成后的
   0001 含 **2 个 hunk**，toybox 与 `patch_ng` 双双 rc=0/apply=True。之前"toybox 不支持多 hunk"
   的观察是**误判** —— 那次失败的真正原因是 `diff -u` 头部的 `--- /+++ ` 文件名不匹配
   （toybox 会按 `+++` 里的文件名去找目标文件，报 `patch: <那个名字>: No such file or directory`）。
   ⇒ 生成的补丁头必须是 `--- a/<file>` / `+++ b/<file>` 且 `-p1` 可用。
2. **`refresh-patch` 会重算 `source_work_hash` 与 `patches_count`**（本包 6→5），但**不会**同步
   `conandata.yml` 的 `sha256`/`patch_file` 列表。⇒ 每次 `finish` 后必须回读
   `patches/` 实际清单并同步 `conandata.yml`，否则 W3 会以
   `patch 文件路径或格式错误` 直接红（本包实测过一次）。

**编译结束**: 2026-09-30 01:50
**最终状态**: built
