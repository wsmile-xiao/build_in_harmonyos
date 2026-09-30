# iroffer 1.4.b03 适配笔记

> **生成物口径（2026-09-29 按审查意见统一）**：本文件所有 `archives/i/iroffer/1.4.b03/reports/*` 引用（`.log` / `*.md` / `*.json` / `.txt`）**均按 §19 不随 PR、磁盘留档**，行号与 sha 指的是**构建主机/工作区留档原件**，PR 内只保留本文件与 PR 正文中的读数。


## 编译环境
- 构建系统: custom（自研 POSIX-sh `Configure` 脚本 + `Makefile.config` 模板，**不是** autoconf/automake）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，Target `aarch64-unknown-linux-ohos`）
- 构建主机: B 机 / HarmonyOS PC（HongMeng Kernel 1.12.0，`uname -s` = `HarmonyOS`，`uname -m` = `aarch64`）
- CONAN_HOME: `~/tmp/ch/home-iroffer`（ohpcd remote enabled，profile `default` 在位）
- 状态: built

## 取源（本包最棘手的一段，务必留证）

任务登记表台账给的址是 `https://deb.debian.org/pool/main/i/iroffer/iroffer_1.4.b03.orig.tar.gz`，
**这个形态实测 404**（缺 `/debian/` 段）：

```
$ curl -sSIL https://deb.debian.org/pool/main/i/iroffer/iroffer_1.4.b03.orig.tar.gz
HTTP/1.1 404 Not Found          Content-Length: 300
$ curl -sSIL https://deb.debian.org/debian/pool/main/i/iroffer/
HTTP/1.1 200 OK                 Content-Length: 5842
```

真实址 = `https://deb.debian.org/debian/pool/main/i/iroffer/iroffer_1.4.b03.orig.tar.gz`
（HTTP 200，`Content-Length: 131571`，`Last-Modified: Mon, 08 May 2006 06:47:02 GMT`）。

**先按优先级①找过上游官方发布位，结论是上游站点已不存在**：

| 候选官方位 | 实测 |
|---|---|
| `http://www.iroffer.org/` | `curl: (6) Could not resolve host` —— DNS 已注销 |
| `https://iroffer.org/` | 同上，DNS 不复存在 |
| `https://sourceforge.net/projects/iroffer/` | HTTP 404 |
| `https://downloads.sourceforge.net/iroffer/iroffer-1.4.b03.tar.gz` | HTTP 404 |
| `https://sourceforge.net/projects/iroffer-dinoex/` | HTTP 404（且 dinoex 是**另一条版本线**，不许拿来冒充 1.4.b03） |
| `http://www.dinoex.org/` | HTTP 200，但 `/src/`、`/prog_iroffer.html` 均 404，无 1.4.b03 发布物 |

最硬的一条证据来自 Debian 自己的 `debian/watch`（取自 `iroffer_1.4.b03-9.debian.tar.xz`）：

```
version=4
opts=dversionmangle=s/.*/0.No-Site/ \
https://people.debian.org/~eriberto/ FakeWatchNoUpstreamSiteForThisPackage-(\d\S+)\.gz
```

即 Debian 官方亦认定**该包无上游站点**（`0.No-Site` + `FakeWatchNoUpstreamSiteForThisPackage`）。
⇒ 落到优先级②：使用 Debian pristine `.orig`，并在此做取源自证。

**三方同哈希自证**（B 机实拍，三个独立来源同值）：

```
03a6ea4e8c7e644d157d0846076d1eb30cc3ef777f9f97a39aaa964df3f2e507  131571
```

1. `deb.debian.org` 下载后本机 `sha256sum`；
2. 同一发布物 `iroffer_1.4.b03-9.dsc` 的 `Checksums-Sha256:` 段原文
   （`03a6ea4e8c7e644d…e507 131571 iroffer_1.4.b03.orig.tar.gz`）；
3. 独立主机 `ftp.debian.org/debian/pool/main/i/iroffer/…orig.tar.gz` 重新下载后 `sha256sum`。

另与 `archive.debian.org` 探针对比：该发行版已离开 archived 区，返回空 ⇒ 未纳入自证（如实记录）。
框架侧第四路：`init-build` 落地的 `~/tmp/builds/iroffer-1.4.b03.tar.gz` 由 `conan` 工具自算
`.tarball-sha256`，与我复算的完全一致。

**pristine（未下游改写）判定**：解包顶层为 `iroffer-1.4.b03.orig/`，内容只有 24 个上游文件
（`Configure` / `Makefile.config` / `README` / `WHATSNEW` / `COPYING` / `sample.config` /
`iroffer.cron` / `dynip.sh` / `.cset_number` / `src/*.c,*.h`），文件 mtime 全是 2005-12-13；
**目录里没有 `debian/`、没有 `*.patch`、没有 quilt 痕迹** ⇒ 这是上游原文件本身，Debian 只做了
顶层目录改名（`dpkg-source` 的 repack 惯例），未注入下游补丁。
`Configure` 第 7 行自证版本：`VERSION=1.4.b03`，与任务版本、Conan 版本、归档目录、分支版本逐字一致。

⚠ 诚实披露：`deb.debian.org/debian/pool` 会被本仓 `scripts/ohc/preflight.py` 的 `_pf7_classify()`
判成「Debian 下游重打包源」（PF7 源URL闸/R39）。上面的证据链说明这是"上游官方位确已消失"后的
唯一可用来源；同型且**已在 origin/main 内**的先例（本棒当场 `git grep -l "deb.debian.org/debian/pool" origin/main -- 'archives/**/conandata.yml'` 命中 304 个归档，此处取三例并给行号）：
`archives/n/netris/0.52/conandata.yml:4`、`archives/a/a52dec/0.7.4/conandata.yml:2`、`archives/a/aalib/1.4p5/conandata.yml:2`——三者都是 `.../debian/pool/main/<字母>/<包>/<包>_<版本>.orig.tar.gz` 形态。

### PF7 源URL闸的例外处置（记为 **P1-已例外处置**，不降为 P3）

- 框架口径（本棒**未重跑门禁**；命中数与位点取第 2 轮独立审计判决件 `archives/i/iroffer/1.4.b03/reports/z75e-audit-result.json`（**按 §19 不随 PR、磁盘留档**） 里 `unchanged_items_for_main_window.Z75KA-08` 的一手复算，同件另记 PF9 一条属工具路径层误报）：`scripts/ohc/preflight.py` 的 PF7 对本包命中 **2 处** —— `conandata.yml:14` 与 `manifest.yaml:11`（同一条 `deb.debian.org/debian/pool` url，`_PF7_DEBIAN_HOSTS` 见 `preflight.py:361`）；`preflight.py:422-:424` 给的处方是「确属官方托管例外须 PR 说明并 `--no-preflight` 显式跳过」（该参数定义在 `scripts/gitcode_pr.py:1130`），而 `preflight.py:598-:621` 的 R52 把「审计判 pass 而硬闸命中」列为审计失真 ⇒ 本条按 **P1-已例外处置** 记并按处方办，不拿 P3 淡化。
- 取源哈希与三向一致（B 机 2026-09-27 本棒一手复算，只读）：`https://deb.debian.org/debian/pool/main/i/iroffer/iroffer_1.4.b03.orig.tar.gz` → `HTTP/1.1 200 OK` + `Content-Length: 131571`，落盘 `wc -c` = `131571`、`sha256sum` = `03a6ea4e8c7e644d157d0846076d1eb30cc3ef777f9f97a39aaa964df3f2e507`，与 `conandata.yml:15`、`manifest.yaml:12` 及上方 .dsc 的 `Checksums-Sha256` 行逐字相等；`tar -tzf` 顶层 `iroffer-1.4.b03.orig/`，其中 `Configure` 实测 1098 行、`sha256` 前缀 `67568ea73310`（与草稿 `.md` 证据三记的 pristine 哈希同一枚）。
- 登记表给的址与池内其它形态：`https://deb.debian.org/pool/main/i/iroffer/iroffer_1.4.b03.orig.tar.gz`（缺 `/debian/` 段）→ `HTTP/1.1 404 Not Found`、`Content-Length: 300`；池目录里的非 orig 名 `…/iroffer/iroffer-1.4.b03.tar.gz` → `404`（300 B 的 404 页）⇒ 池内只有 `.orig` 这一枚可用发布物。
- 官方上游不可得（本棒一手负证据，五种独立端点复测；HTTP 码取不到即记 `000`，含义是 DNS/连接层面就失败，与上方「取源」表里 `curl: (6) Could not resolve host` 同一事实）：`http://www.iroffer.org/`、`https://iroffer.org/`、`https://www.iroffer.org/` 三种写法一律 `000`；`https://sourceforge.net/projects/iroffer/` → `404`；`https://downloads.sourceforge.net/project/iroffer/iroffer/1.4.b03/iroffer-1.4.b03.tar.gz` → `404`；`https://github.com/iroffer/iroffer` → `404`；Debian 维护者站裸域 `http://dinoex.org/` → `000`（DNS 亦不复存在），带 www 的 `http://www.dinoex.org/` → `200`、`Content-Length: 892`、实收 892 B（仅项目主页，无 1.4.b03 发布物），其 `http://www.dinoex.org/download/iroffer-1.4.b03.tar.gz` → `404`（158 B 的 404 页），`/src/` 与 `/prog_iroffer.html` 亦 `404`；维护者上传位 `https://people.debian.org/~eriberto/` → `200`（14615 B 的目录索引页）。
- Debian 侧的自证与上方 `debian/watch` 原文一致：版本被 mangle 成 `0.No-Site` 并挂 `FakeWatchNoUpstreamSiteForThisPackage` ⇒ Debian 官方亦认定该包**无上游站点**，池内 `.orig` 就是上游原文件的托管副本。
- ⇒ 判定与处置：没有任何可核验的上游发布位可以替代 Debian 池件，按**官方托管例外**处理 —— 保留 `conandata.yml:14` 与 `manifest.yaml:11` 的池 url（⛔ 未改 url、⛔ 未因该闸改动上游源码/补丁/版本串、⛔ 未手写任何 `_PF7_MIRROR_HOSTS` 点名的镜像前缀，镜像回退由框架自行处理），交付路径按 `preflight.py:424` 的处方以 `--no-preflight` 显式跳过 PF7，例外理由即本小节，PR 正文同步摘录本节事实段。

## 编译步骤

```bash
export CC=/data/service/hnp/bin/clang          # 配方里由 conf 提供，见 conanfile.build()
sh ./Configure                                 # 生成 src/iroffer_config.h + Makefile
make all CC="$CC" -j1                          # R9
```

`Configure` 的探测结论（原文摘录，构成本次的"基线读数"）：

```
Determining OS... HarmonyOS
Checking for gcc/cc... using CC=clang (from environment)
Seeing if clang works... yes
Seeing if clang accepts '-Wall'... yes
Seeing if clang accepts '-Werror'...  no          ← 因此上游没把 -Werror 带进 CFLAGS
Creating src/iroffer_config.h... Done
Creating Makefile... Done
```

生成的 Makefile 头部（`CONFIG_*` 全部由 Configure 写出，`Makefile.config` 是其静态尾巴）：

```
VERSION=1.4.b03
CC=clang
CONFIG_EXE=
CONFIG_LDLIBS=
CONFIG_LDFLAGS= -O2
CONFIG_CFLAGS= -Wall -O2
CONFIG_CPPFLAGS=
CONFIG_CHROOT=
CONFIG_TARGETS=
```

生成的 `src/iroffer_config.h` 关键行（`_OS_Linux` 是映射 HarmonyOS 的结果）：

```c
#define VERSIONLONG "1.4.b03 [20051213024435]"
#define _OS_Linux
#define HAVE_LINUX_SENDFILE
#define HAVE_MMAP
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sh Configure` 只打印 `***ERROR***: This OS is not supported` 就结束，**退出码仍是 0**，既不生成 config.h 也不生成 Makefile | 上游 `Configure` 用 `case $(uname)` 白名单判 OS，白名单是 2005 年的 Linux/BSD/SunOS/HP-UX/IRIX/OSF1/Darwin/AIX/CYGWIN；鸿蒙 PC 的 `uname -s` = `HarmonyOS` 落入 `*)` 分支 | 补丁 0001：新增 `HarmonyOS )` 分支，把 `ostype` 映射到既有 `Linux`。映射依据是 `iroffer_defines.h:197` —— `_OS_Linux` 是 `#define _GNU_SOURCE` 的唯一开关，其余分支在 OHOS（musl + Linux 兼容 socket/file API）上都不对；`#else` 分支本身是 `#error`，所以不做平台映射连编译都进不去 |
| 2 | 探测阶段全部失败：`Checking for gcc/cc...` 之后 `Couldn't find gcc or cc`，config.h 只剩两行、Makefile 里 `CC=`（空），make 随即去找不存在的 `cc` | 鸿蒙 PC 只有 `clang`，`gcc`/`cc` 均不在 PATH（`command -v gcc`/`cc` 皆空）；`Configure` 硬编码只会 `type gcc`/`type cc` | 补丁 0001（同一文件第二个 hunk）：让 `Configure` 优先采用环境变量 `CC`。配方侧按 **R33** 从 `tools.build:compiler_executables` 取 `c` 后显式传入 `CC="…"`，不吃调用方 shell 环境 |
| 3 | `make` 起手 `make: jobserver mkfifo: /storage/…/tmp/GMfifo15116: Operation not permitted` | HMDFS 不允许创建 FIFO；GNU Make 4.4.1 的 `-j` jobserver 依赖 mkfifo | 非致命：make 自动降级继续。**配方一律 `-j1`（R9）**，从根上绕开 jobserver；不改源码 |
| 4 | 不能用 `make install` | 三重阻塞：上游 `install` 目标写死 `install -o root -g root -m 0755`（无根沙箱必失败）、`INSDIR` 硬编码 `/usr/local/bin`（R49/PF6 禁注入共享系统前缀），且本机根本没有 `install` 命令（toybox，E098） | 按 E098 处方在 `package()` 里用 `copy()` 落 `bin/`；不把 `/usr/local` 写进配方 |
| 5 | `init-build` 在 Step 8 之后崩、拿不到 `.build-context`（详见「框架/环境侧发现」） | 机器上 `~/usr/local/bin/automake` 的 shebang 指向不存在的 `~/usr/local/bin/perl` ⇒ `subprocess` 抛 `FileNotFoundError`，而 `scripts/ohc/check_env.py:33` 的 `except Exception:` 里引用了未绑定的 `e` ⇒ `NameError` 直接把 init-build 打断在写 context 之前 | 本轮**未改框架**：在同一条命令里把 `~/usr/local/bin` 从 PATH 暂时摘掉（`shutil.which("automake")` 返回 None 就不走崩溃分支），用 `init-build --no-download` 正常拿回 `.build-context-iroffer-1.4.b03`，`.work` 里的改动未被覆盖（复核 `grep -c HarmonyOS` = 2） |

## 源码修改

只有一个补丁文件，改的是 `Configure`（**上游构建脚本，不是生成文件**；R1：探索阶段直改源码 +
记笔记，补丁由 `refresh-patch --auto` 生成）。

| 补丁 | 目标文件 | 增删 | 内容 |
|---|---|---|---|
| `patches/0001-…patch` | `Configure` | +11 / -1，净 +10（2 处 hunk：`@@ -58,20 +58,27 @@` 与 `@@ -166,21 +173,24 @@`；见下方口径说明） | hunk1：`case "$ostype" in` 后插入 `HarmonyOS ) ostype=Linux ;;` 分支（含 4 行注释）；hunk2：`Checking for gcc/cc` 后插入 `if [ -n "$CC" ]; then cctype="$CC"; …`，原 gcc/cc 探测降级为 `elif` |

⚠ 口径如实说明：这两处**都是"给上游加分支"，没有删除任何上游逻辑**（diff 里的 `-1` 是
`if [ -f … ]` 那一行被改写成 `elif [ -f … ]`，属改写而非删功能）。
**没有补 `extern` 声明、没有加 `#ifdef __OHOS__`、没有放宽任何源码语义**；
`src/*.c` 与 `src/*.h` 一个字节都没动（`git status` 只出现 `Configure` 一份）。

## 上游既有 vs OHOS 特有（不许把告警清零当成绩）

编译产生 0 个 error、若干 warning，**全部是上游 2005 年代码既有问题，不是 OHOS 特有缺陷**，
未做清零处理（上游 `Configure` 自己因 `-Werror` 探测失败而没有启用 `-Werror`）：

| warning 类别 | 出处（原文抽样） | 定性 |
|---|---|---|
| `-Wsizeof-pointer-memaccess` | `src/iroffer_md5.c:142: memset(ctx, 0, sizeof(ctx))` | 上游既有（对 `MD5_CTX` 指针用了 `sizeof(ptr)`，真 bug，上游未修） |
| `-Wpointer-sign` | `src/iroffer_statefile.c:256/383/435/443`、`src/iroffer_transfer.c:138/172/179`、`src/iroffer_upload.c:145` 等 | 上游既有（`unsigned char*` ↔ `char*`，与 libc 无冲突） |
| `-Wformat` | `src/iroffer_transfer.c:489: "%d" 对上 ssize_t` | 上游既有（64 位平台上 ssize_t 是 long，非 OHOS 特有） |

值得记录的**正面结论**：本包在 clang 15 上**没有**撞到 `implicit-function-declaration`、
`implicit int`、K&R 原型、`gets` 这类"老 C 在新 clang 上直接变 error"的坑——
`iroffer_headers.h` 把头文件收得很齐，而本设备 clang 把隐式声明仍判 warning。
所以本轮**不需要** `-fcommon`、不需要 `-std=gnu89`、不需要额外 `conf` 编译选项
（R1 参数最少化：`CONFIG_CFLAGS` 保持上游自己算出来的 `-Wall -O2`）。

## 依赖版本

**无 Conan 依赖**。上游只链 `libc.so`：

```
$ readelf -d iroffer | grep NEEDED
 (NEEDED) Shared library: [libc.so]
```

`Configure` 探测出的 `CONFIG_LDLIBS` 为空（非 SunOS 分支不需要 `-lsocket -lnsl`），
`HAVE_MMAP` / `HAVE_LINUX_SENDFILE` 均命中，`NSS` 缺失 ⇒ `CONFIG_TARGETS` 为空 ⇒
`iroffer_chroot` 不构建（上游逻辑，不是我们关掉的）。

## 上游行为基线（test_package 期望值的来源，全部实测于 B 机）

| 命令 | 实测退出码 | 关键输出 |
|---|---|---|
| `iroffer -v` | 0 | `iroffer v1.4.b03 [20051213024435] by PMG, see http://iroffer.org/` |
| `iroffer`（无参） | 0 | `no configuration file specifed`（上游原拼写）+ usage |
| `iroffer -h` | 0 | `unrecognized option: h` + usage（上游对未知选项不报错） |
| `iroffer -d -n -s bad.cfg` | 1 | 打出 `Version 1.4.b03` / `Starting up...` 后因配置错误失败 |
| `iroffer -c`（喂 stdin） | **不稳定：有 tty=1，无 tty（管道 / `< /dev/null`）= timeout 124** | `Configuration File Password Generator`；它经 getpass 类例程读口令 ⇒ **不写进断言** |
| `convertxdccfile -x empty.xdcc -s conv.state` | 0 | `Empty XDCC File, Starting With No Packs Offered` + 生成 252 B `.state`，头 4 字节 `IRFR`，内嵌 `iroffer v1.4.b03 [20051213024435]` |
| `convertxdccfile -x bad.xdcc -s …` | 1 | `XDCC file syntax error (missing/extra line)` |
| `iroffer -d -n -s min.cfg`（只有 admin_nick） | 1 | `Starting up...` → `Ignored invalid line in config file: admin_nick` → `Config File Missing Necessary Information` |
| `convertxdccfile`（无参） | 1 | `Usage: ./convertxdccfile [-v] -x mybot.xdcc -s mybot.state` |
| `make check` | 2 | 无该目标（上游确实无测试） |

## 测试账本（rule4：声明数 ≤ 实测数）

| 维度 | 值 | 依据 |
|---|---|---|
| `N_static`（上游测试资产静态清点） | **0** | 本棒独立复算（pristine 源 find 全量 24 个文件；名字含 test/check/spec/expected 的命中 0；Makefile.config 的目标全集 = all/src-doc/tar/winbin/clean/install；check、test、tests、installcheck 四类目标计数 0）。原依据：24 个文件全列举，无 `tests/`、无 `check`/`test` 目标、无 ctest/pytest/TAP 注册 |
| `N_registered`（`test_package/MANIFEST.yml` 注册项） | **0 条上游 + 1 个自写测试脚本（`test.sh`，16 条断言）** | 见 MANIFEST.yml |
| `N_executed`（真跑过的） | **16/16**，本轮 3 次真跑全过（04:36 verify 的 create、04:38 finish 内嵌 verify 的 create、04:39 W3 的 create），`PASS[1]…PASS[16]` 逐条可数 | test_package 在 conan create 之后真执行 |
| `skips` | **0 条**（无一条断言带条件跳过） | 但**撤下过 1 条**：`iroffer -c` 分支的退出码随有无控制终端变化（有 tty=1、无 tty=timeout 124），不可复现 ⇒ 不写成断言，在 MANIFEST.yml/test.sh 头部留痕 |
| `N_consumer`（消费者断言数） | **16** | iroffer 四条分支(9) + convertxdccfile 无参(2) + 真转换往返(3) + 坏输入(2) |
| `N_runner`（执行位点数） | **2** | ①`conan-verify` 的 test_package 阶段；②`finish` 的 W3 `conan create`；本轮实测真跑 3 次，全部 `PASS 16/16` |

**断言调用点独立复算（本棒）**：`grep -c "^ok " test_package/test.sh` = **16**；调用点行号 = 47 49 54 56 61 63 69 71 73 78 80 86 90 93 102 104；`N_ASSERT=16`（test.sh:19）与收尾核对 `[ "$N_PASS" -eq "$N_ASSERT" ]`（test.sh:110）⇒ 声明数 == 实测数。

诚实声明：**"上游 iroffer 1.4.b03 的测试从未以 make 目标形式跑过，因为它没有测试目标"**
——`make check` 报 `No rule to make target 'check'`（rc=2），这是实测，不是推断。
本包交付的 16 条断言全部是**消费者侧新写**，不冒充上游测试通过率。

## 验证结果

本轮（续做棒 **主理-75**，2026-09-27 04:36–04:39，仓库 HEAD `5cf15540b2`）四步门禁全部**重跑**；
报告件均为本轮重新生成（旧件指纹一并列出，不拿上一棒 04:28/04:29 的日志充数）。

### 门禁 1：preflight_check.sh（W0 精确依赖发布态）
- 命令：`bash ci/scripts/preflight_check.sh iroffer/1.4.b03` → **rc=0**
- 读数原文：`[OK] 预检通过（无依赖需要检查）`；上一行 `[INFO] 未找到依赖声明（conanfile.py 尚未生成或无依赖）。`
- 本包无 Conan 依赖（`readelf -d` 只有 `libc.so`），W0 无精确依赖可核；**未**用通配 `conan list` 判二进制。

### 门禁 2：recipe-search
- 命令：`python3 scripts/ohc-run.py recipe-search iroffer` → **rc=0**
- 读数原文：`1. iroffer/1.4.b03  [unknown]  score=0.5 +补丁`，骨架 = 本归档 `archives/i/iroffer/1.4.b03/conanfile.py`
  ⇒ 检索语料已含本包（与 finish 的「配方已并入检索语料 (recipe-search 可见)」一致），无他人同包骨架竞争。

### 门禁 3：conan-verify（G0–G4 / L2 / L4 / L5）
- 命令：`python3 scripts/ohc-run.py conan-verify iroffer 1.4.b03`（经 `~/tmp/uc2/build-slot.sh --kind short`，`SLOT_OK 04:36:08`）→ **rc=0**
- **三一致**（判绿口径，不采信图标单独成立）：终端正文 `✅ 配方验证通过: iroffer 1.4.b03` + 报告 `**Verdict**: PASS` + rc=0。
- 本轮新件自证（**该报告件按 §19 不随 PR、磁盘留档**，原文 sha 见下表）：`archives/i/iroffer/1.4.b03/reports/conan-verify-report.md`
  现存件 44 行 / 1089 B / md5 `c6dae291112db1a6578e401b3fd91cc1` / sha256 `d512cbbfa3f30e077a4457c08717f303a129c224965048ebb63b4930e81ae8df`，其第 6 行
  `**Date**: 2026-09-27T04:38:18.016312` ⇒ 取的是 04:38 门禁 4 内嵌那一次 verify 覆盖后的版本。
  本件本轮被写出三次：04:28（上一棒，md5 `73e2dc45122456a0875b05eab86ea9da`）、04:36:18.446026
 （门禁 3，md5 `4123dd6c693e42538b47dc6213eb7367`）、04:38:18.016312（门禁 4，即现值）；前两版的件已被覆盖、
 盘上不再存在 ⇒ 那两个 md5 只作流水记录、不可再核（上一版 notes 把 04:36 的值当成现值，独立审计 Z75KA-03 已纠）。
- **实际覆盖面（照实写，不照抄图标）**：

  | 门 | 图标 | 原文读数 | 采信结论 |
  |---|---|---|---|
  | G0 | PASS | `构建系统: unknown` / `无法识别构建系统，跳过预查询` | 未做预查询（手写 `Configure` 识别不出） |
  | G1 | PASS | 12 项结构检查 = 11 项 ✅ + 1 项 ℹ️（件内第 13–24 行，第 21 行 `R26: 未检测到静态链接配置` 是非阻塞提示）；✅ 项含 `export_sources`、补丁应用调用、`test_package/MANIFEST.yml` | **真判定** |
  | G2 | PASS | `conan create 成功` | 真判定，但本轮 create 是**缓存命中**（create 日志 `Already installed! (1 of 1)`、无 `Calling build()`）⇒ 编译证据不在此处 |
  | G3 | PASS | `无 lib/ 目录（纯可执行包）` / `无系统同名库冲突（R26 通过）` | 真判定 |
  | G4 | PASS | `⚠️ 无法找到程序包 ID` | **跳过**——产物完整性检查未覆盖 |
  | L2 / L4 / L5 | PASS | `⏭️ 跳过（无 cache 路径）` | **跳过**——未覆盖 |

  ⇒ **本阶段真实覆盖仅 G1–G3**（G0 是"识别不了所以不查"，G4/L2/L4/L5 直接跳过）；判决图标为 ✅ 不等于跑过。
  运行期与产物证据全部来自门禁 4 的 W3，见下。

### 门禁 4：finish（内含一次 conan-verify + W3 本地 CI 模拟）
- 命令：`python3 scripts/ohc-run.py finish iroffer 1.4.b03 built`（同走 short 槽，04:37:55 → 04:39:25）→ **外层 rc=2**
- 本包判据三条同判：① `EXIT_REASON: finish_success`；② `EXIT_CODE: 0 (知识整理已完成)`；③ 失败步骤 = `step5b, step8`（**不是 Step5 编译类**；`STEP_FAILED: Step6` 属知识整理段）。
  ⇒ rc=2 是仓库级/工具噪声，不是本包失败；噪声内容逐条见「框架/环境侧发现」(e)。
- W3 判决原文：`✅ 本地 CI 模拟通过 (日志: archives/i/iroffer/1.4.b03/reports/w3-local-ci.log)` + `✅ W3 本地 CI 模拟通过`，
  汇总 `Success: 1 / Failed: 0 / Pass rate: 100.0% (1/1)`。
- W3 结果件按「字段值 + 复算式」给（`.ci-result.json` 是框架状态件：`scripts/ohc/finish.py:245-266` 的
  `_write_ci_result()` 写出、`scripts/ohc/submission.py:1006-1013` 的 Gate 2/4 校验，**不随本 PR 提交**）：
  字段原文 `step: W3_local_ci`、`timestamp: 2026-09-27T04:39:13.245021`、`exit_code: 0`、
  `software: iroffer`、`version: 1.4.b03`、`integrity_hash: c4d2d93068e4eca2`、
  `log_sha256: be86aeddeb36f02fab48a86d4843fd6362d3af6c9ed1b2d8ba792f5fa9c623ea`。
  复算式一：`sha256sum archives/i/iroffer/1.4.b03/reports/w3-local-ci.log` 应逐字等于上面的 `log_sha256`（该日志已
  **按 §19 不随 PR、磁盘留档**，531 行 / 34321 B / sha256 `be86aeddeb36f02fab48a86d4843fd6362d3af6c9ed1b2d8ba792f5fa9c623ea`）。
  复算式二：`raw = timestamp + ":" + software + ":" + version + ":" + str(exit_code)`，取
  `sha256(raw).hexdigest()[:16]` 即得 `c4d2d93068e4eca2`；同一式子把 `exit_code` 换成 1 得 `09d36605545ecf6c`
 （本棒实测两值，式子可判别、不是事后凑数）。旧版此处另引的 04:29 轮 `log_sha256` 因件已被覆盖而不可再核，删除。
- **真实编译落在本轮 W3**（补上 G2 缓存命中的缺口）：W3 日志原文 `iroffer/1.4.b03: Building from source`、`Calling build()`、
  `Apply patch (portability): Teach the 2005 hand-written Configure about HarmonyOS …`、
  `RUN: CC="/data/service/hnp/bin/clang" sh ./Configure`、`RUN: make all CC="/data/service/hnp/bin/clang" -j1`，逐文件 clang 命令行可见。
- W3 功能矩阵原文读数：`L0_RESULT=pass: all checks passed`；`L1_RESULT=pass: test_package executed`
  （`[ok] L1a` / `[ok] L1b` / `[step] L1c: No upstream make check/ctest in log (may be in test_package only)`）；
  `[ok] L1e: Negative test confirmed — test genuinely depends on iroffer`（把 `bin/` 移走后测试确实失败 ⇒ 断言真的依赖被测包）；
  `L2_RESULT=pass: convertxdccfile version/help failed, iroffer --version OK`；`L4_RESULT=pass: patches clean`；`L5_RESULT=pass: bin/ has content`。
- ⚠ **L2 的 pass 要打折**：两个交付二进制只有 1 个通过 smoke，且 `iroffer --version` 之所以"OK"是因为上游对未知长选项**只告警、返回 0**
  （见「上游行为基线」的 `iroffer -h` 行）⇒ L2 不构成版本输出证据；版本实证是 test.sh 断言 1–2 与 `.state` 内嵌串（断言 14）。
- test.sh 本轮真跑 **3 次**：04:36（verify 的 create）、04:38（finish 内嵌 verify 的 create）、04:39（W3 的 create），三处均 `PASS 16/16`，`PASS[1]…PASS[16]` 逐条可数。
- 收口前 CONAN_HOME 自证：`conan list "iroffer/*"` 在 `~/tmp/ch/home-iroffer` 下 `Found 2 pkg/version recipes matching iroffer/*`：
  `iroffer/1.4.b03` 与 `iroffer/1.4.b03@ohpcd/stable` ⇒ 制品确实落在本任务 home（没有漏进默认 `~/.conan2`）。

## 交付物

| 文件 | 大小 | 说明 |
|---|---|---|
| `bin/iroffer` | 248256 B（探索构建实测） | 主程序：IRC/XDCC 守护进程，PIE、AArch64、dynamic（`/lib/ld-musl-aarch64.so.1`），NEEDED 仅 `libc.so`，not stripped |
| `bin/convertxdccfile` | 92544 B（探索构建实测） | 旧 `.xdcc` 列表 → `.state` 文件转换器 |
| `res/iroffer/sample.config` | 23331 B | 上游完整配置样例（200+ 条配置项的带注释模板，运行必需参考） |
| `res/iroffer/README` `WHATSNEW` `iroffer.cron` `dynip.sh` | 5172 / 24286 / 857 / 942 B | 文档与配套脚本（`dynip.sh` 供 no-ip 类动态域名，`iroffer.cron` 是重启样例） |
| `licenses/COPYING` | 15957 B | GPL-2.0-or-later + md5.[ch] 公有领域例外声明 |

## 注意事项

1. **版本串不得归一化**：`1.4.b03` 逐字用于任务版本、Conan 版本、归档目录、分支名与
   `commands.json` 的 `versions` 键。`iroffer-dinoex`（SourceForge/GitHub 上的后继）是
   **另一条版本线**，本包与它无关。
2. `iroffer` 是守护进程：`test_package` 不联网、不 daemon 化（只用 `-d -n -s` 前台无色彩模式
   跑确定性分支），CI 无 IRC 服务器。
3. 上游 `Configure` 不认 `--prefix`（只认 `-h/-e/-d/-p/-w`），因此**不要**给它加参数；
   安装路径由 `package()` 的 `copy()` 决定。
4. `iroffer_chroot` 目标在本机不生成（`NSS` 探测缺失 ⇒ `CONFIG_TARGETS` 空），属上游既有逻辑。
   如实记录：交付的可执行文件是 2 个，不是 3 个。
5. 本包**没有**用到 `-fcommon`、`-std=gnu89`、`tool_requires(diffutils)`；
   若后续 CI 环境差异导致需要，请连同本笔记第「上游既有 vs OHOS 特有」节一起复核，不要静默加。
## 框架/环境侧发现（本包不改框架；给下一棒省时间）

(a) **`ohc-run.py build iroffer 1.4.b03` 对本包是码路错配，不要跑。** 上一棒 04:16 实测原文：
    `❌ 源码目录不存在: /storage/Users/currentUser/qzy/主理-75-iroffer-1.4.b03/archives/i/iroffer-1.4.b03/src`
    （同轮还记 `⚠️ 0001-Configure.patch (所有 strip level 均失败，需手动应用)`）。
    本棒**没有重跑** `build`、**没有**重跑 `init-build`（会覆盖手写配方）、**没有**伪造那个目录、**没有**换源。
    真实构建证据由 `conan-verify` 的 G2 与 `finish` 的 W3 `conan create` 承担——本轮 W3 确实从源码编译（见「验证结果」门禁 4）。

(b) `init-build` 的 Step8 崩溃链（机器上 `~/usr/local/bin/automake` 的 shebang 指向不存在的 perl ⇒ `FileNotFoundError`，
    而 `scripts/ohc/check_env.py:33` 的 `except Exception:` 引用未绑定的 `e` ⇒ `NameError` 打断在写 context 之前）
    已记在「遇到的问题与解决方案」表第 5 行；本轮未复跑 init-build，`.build-context-iroffer-1.4.b03` 仍在位、`.work` 未被覆盖。

(c) **finish 的 `Step 3/10: G0 干净构建验证` 本轮红，且红得不是本包的账**：终端原文
    `✅ G0: 1 个补丁全部应用成功` → `❌ G0: configure 失败 (exit 1)` → `⚠️ G0 干净构建验证失败，请手动检查构建结果`（**非阻塞**，Step4 继续并 PASS）。
    它自己的日志（**按 §19 不随 PR、磁盘留档**：`archives/i/iroffer/1.4.b03/reports/g0-configure.log`，12 行 / 647 B /
    sha256 `5a0f609a515e36006762264906ee13a535f08549d79e71c5d3f4b56444d37648`，本轮 04:38 实拍；原件在临时目录 `$HOME/tmp/ohc-verify-iroffer-6965g_fq/`）
    第 5–12 行原文即第一条真实错误：

    ```
    Configure for iroffer 1.4.b03 [20051213024435]
    ./configure: illegal option -- -
    Usage: Configure [ options ]
       -h           This help
       -e           Print errors while running Configure
       -d           Compile with debug symbols
       -p           Compile with profiling flags
       -w           Compile with extra warning flags
    ```

    根因：这段按 autoconf 形态直接跑 `./configure` 并传标准长选项；本包顶层只有手写的 `Configure`，
    **大小写不敏感的文件系统把 `./configure` 解析到了 `Configure`**，而它只认 `-h/-e/-d/-p/-w` ⇒ `illegal option` 退出 1。
    配方侧不经 `AutotoolsToolchain`（`generate()` 是 `pass`，见 `conanfile.py:57-58`），所以没有任何"注入参数"可由配方剪除。
    定性：**框架探测码路错配，不是包不可构建**——同一份源在同一轮 W3 里 `conan create` 真编译并 16/16 通过。
    日志开头的 `shell-init/job-working-directory: error retrieving current directory: getcwd` 是临时目录被回收后的 cwd 读取失败，属另一件事，不写成本包根因。

(d) **上游构建入口"报错却 rc=0"**（本棒在 B 机用**未打补丁**的 pristine 源亲测）：
    `sh ./Configure` → `Determining OS... HarmonyOS` → `***ERROR***: This OS is not supported` → **rc=0**，
    且 `src/iroffer_config.h` 与 `Makefile` 都没生成（本棒实测 `config.h=no Makefile=no`）。
    源码位置 `Configure:105-106`：`echo "***ERROR***: This OS is not supported"` 紧跟**裸 `exit`**（不带状态码）。
    ⇒ 任何"跑一下 configure 看退出码"的探测对这类 2005 年脚本都会假绿；判据必须再加**生成物存在性**（本包 = `Makefile` + `src/iroffer_config.h`）。
    补丁生效的直接证据是 W3 日志里的 `Checking for gcc/cc... using CC=/data/service/hnp/bin/clang (from environment)`。

(e) `finish` 的两类噪声逐条（都不构成本包失败）：
    * `失败步骤: step5b`：`❌ test-report.md — 需创建 reports/test-report.md`、`❌ packaging/ — 需创建 packaging/ 目录并打包`、
      `❌ .staging-verified — 需创建 .staging-verified 空文件`（外加 `⚠️ 3 项未就绪，submit 前需修复`）。
      `packaging/` 与 `.staging-verified` 由**收口打包步骤**在设备上生成（工作区侧 `pipeline.py` 的 `[3/8]`），归档内不手写；
      `test-report.md` 那一项的注释口径是「若缺需人工补」⇒ 由主窗（主理-75）在建 PR 前处置；B 交付棒不建 PR、不改门禁判定。
    * `step8`：`gen_summary 失败: 'str' object has no attribute 'append'`（工具侧异常）与
      `❌ 知识图谱完整性检查发现 1 类问题`（仓库存量 1396 条草稿的级别问题）；同段其余为绿：
      `✅ doc↔kv 配套完整 (540 对)`、`✅ graph validate 通过`、`✅ 仅含配方变更 (9 文件)，无框架文件`。
    * 归档报告里 `打包产物: 0 个`、`缺失项: 2`、`一致性问题: 1` 与上面同源，均为收口前置清单，不是构建结论。

## B 机制证据（流水账；终判已由主窗下达：**create 1 条 = M3**，M4 入通用池，知识库扩展 Issue #3506；下面 M1–M8 是判据流水，各条「倾向」保留当棒口径）

每条给：症状原文 / 根因 / 最小复现 / 已试过的失败方案 / 最终方案 / 适用边界 / 仓内既有条目（**根因段与推荐段行号都给**）/ 本棒倾向。
检索面：`knowledge/doc/E*.md`、`knowledge/drafts/`、`knowledge/` 根下的 DRAFT；关键词取**机制特征词**，不取包名。

### M1 手写 `case "$ostype"` 白名单不含 HarmonyOS ⇒ 映射到既有 Linux 分支
- 症状原文：`***ERROR***: This OS is not supported`（退出码仍是 0，见 M5）。
- 根因：`Configure` 的 OS 白名单是 2005 年的 Linux/BSD/SunOS/HP-UX/IRIX/OSF1/Darwin/AIX/CYGWIN；`uname -s` = `HarmonyOS` 落 `*)`；
  而 `iroffer_defines.h:197` 里 `_OS_Linux` 是 `_GNU_SOURCE` 的唯一开关，`#else` 分支本身是 `#error` ⇒ 不映射连编译都进不去。
- 最小复现：解包 pristine `.orig` 后 `sh ./Configure`（本棒 04:3x 实拍，见「框架/环境侧发现」(d)）。
- 已试过的失败方案：无（本轮直接按家族处方加 `HarmonyOS )` 分支）。
- 最终方案：补丁 hunk1 加 `HarmonyOS ) ostype=Linux ;;`，不删任何上游逻辑。
- 适用边界：一切自带 `uname` 白名单的手写构建脚本；autoconf/config.guess 家族走另一载体。
- 既有条目：`knowledge/doc/E160.md` 根因分析 **:15**、推荐方案 **:18–:25**（**:20** 处方 = 给 `config/config.guess` 加 HarmonyOS→Linux/LIBC=musl 分支，**:24** 给 sed 命令）；
  `knowledge/drafts/DRAFT-E2167-handwritten-configure-conan-injected-args.md` **:23** 明文把"手写 configure 的 `uname -s` 白名单无 HarmonyOS"归为"**E160 类**平台补丁"。
- 倾向：**hit**（KB 自己把手写脚本归进 E160 家族）。若主窗按"处方载体必须同为 config.guess"从严，则 E160 不覆盖 ⇒ 需 create。两个口径都摆出来。

### M2 设备只有 clang、无 gcc/cc ⇒ 上游编译器探测全瞎
- 症状原文：`Checking for gcc/cc... not found. ***ERROR***: Couldn't find gcc or cc`，随后 `Makefile` 的 `CC=` 为空、config.h 只剩两行。
- 根因：`Configure` 硬编码 `type gcc` / `type cc`；OHOS PC 上两者都不在 PATH（只有 `/data/service/hnp/bin/clang`）。
- 最小复现：`command -v gcc; command -v cc` 皆空，再用未打补丁的源跑 `Configure`。
- 已试过的失败方案：靠调用方 shell 环境隐式提供 `CC`（R33 禁止、CI 里不可复现）；给配方加 `tool_requires` 造 cc（不需要，且会引入新依赖）。
- 最终方案：补丁 hunk2 让 `$CC` 优先，配方从 `tools.build:compiler_executables` 整键取 `c` 后显式 `CC="…"` 同时传给 `Configure` 与 `make`（`conanfile.py:60-76`）。
- 适用边界：手写构建脚本 + 设备无 gcc 的家族；autoconf 家族原生吃 `CC`，不需要这类补丁。
- 既有条目：只找到**方向相反**的 `knowledge/drafts/DRAFT-9639-minibwa-profile-cc-path-fallback.md`（根因 **:14**、处理方法 **:23–:37**、适用范围 **:46**：profile 里 compiler_executables 路径失效时回退 PATH）；
  `knowledge/doc/E074.md`（根因 :15、推荐 :20–:27）是 make FIFO，不是本条。
- 倾向：**不单独升 B**（该机制在老代码家族里过于常见，且处方就是 R33 的常规动作）。

### M3 框架/工具按 autoconf 形态跑 `./configure`，被大小写不敏感 FS 落到手写 `Configure`
- 症状原文：`❌ G0: configure 失败 (exit 1)` + `./configure: illegal option -- -`。
- 根因：见「框架/环境侧发现」(c)——`clean-build-verify` 假设存在可吃长选项的 `configure`；HMDFS 大小写不敏感使 `./configure` 命中 `Configure`；配方不生成 toolchain，没有注入参数面可剪。
- 最小复现：`python3 scripts/ohc-run.py finish iroffer 1.4.b03 built` 看 `Step 3/10`（本棒 04:38 实拍），或把 `./configure --prefix=/x` 指到只有 `Configure` 的目录。
- 已试过的失败方案：无（不为本包改框架、不加第二枚补丁、不伪造 `configure` 文件、不改 `generate()` 去引入 AutotoolsToolchain）。
- 最终方案：**不改上游/不改框架**；以 W3 的 `conan create` 真编译 + 生成物存在性作为构建判据，并把这条红定性为框架码路错配写进 notes。
- 适用边界：一切"手写 `Configure` / 自研 sh 构建入口 + 不经 AutotoolsToolchain"的包；autoconf 包不受影响。
- 既有条目：`knowledge/drafts/DRAFT-E2167-handwritten-configure-conan-injected-args.md` 根因 **:9–:10**、解决方案 **:14–:21**（处方 = `tc.update_configure_args({"--oldincludedir": None})`）、风险与边界 **:36–:39**——
  **同一物理事实（手写 configure 拒长选项）但处方在另一操作面**（Conan 的 AutotoolsToolchain 注入），本包没有 toolchain 可剪；且 E2167 未含"大小写不敏感 FS 把 `./configure` 命中 `Configure`"这一半。
  另 `knowledge/doc/E346.md:15` 记的是 make 默认 shell 被沙盒拒（另一码事，不构成覆盖）。
- 倾向：**create 候选 #1**。判 create 前主窗仍需手工 grep `knowledge/drafts/`（draft-review 的相似面不扫该目录）。

### M4 无测试老 CLI 的**负向分支可达性**必须先实测
- 症状原文：只给一行残缺 offer 的 `.xdcc` 时 `convertxdccfile` **成功**产出空表（rc=0）；想断言 `XDCC file syntax error (missing/extra line)` 时拿不到 rc=1。
- 根因：上游解析器把"首行三元组无效"当作"空表"继续处理 ⇒ 失败分支不可达；必须**首行三元组有效 + 次行残缺**才进 syntax error。
- **复算更正（B 交付棒 2026-09-27 05:1x 实拍，用 conan 缓存内已构建的 `convertxdccfile`：`~/tmp/ch/home-iroffer/p/b/irofff8f9f7eb95007/b/convertxdccfile`）：判别式在测到的范围内是**行数**而非首行有效性。①单行残缺（`1: test file /tmp/f 10 50`）→ rc=**0**、写出 252 B 表、仍打 `** WARNING: Invalid First Line, Reverting Values to 0`；②上面那两行原字节 → rc=**1** + `** ERROR: XDCC file syntax error (missing/extra line)`（两臂都带 Invalid First Line 告警）；③把次行引用的文件换成真实存在的文件（`192.168.1.1 6667 testnick` + `1: two.xdcc 10 50`）→ 仍 rc=1、仍打 Invalid First Line。⇒ 本窗**未测出任何被上游接受的首行写法**，故「首行三元组有效」这句只能记为**未证实**（⛔ 不得写成「上游不支持该语法」）；M4 的机制句以「单行被当空表成功、两行才进失败分支」为准。
- 最小复现（B 机实拍）：
  `convertxdccfile -x one.xdcc -s a.state; echo $?` → **0**（单行残缺）；
  `printf '192.168.1.1 6667 testnick\n1: test file /tmp/f 10 50\n' > bad.xdcc; convertxdccfile -x bad.xdcc -s b.state; echo $?` → **1**
  （即 `test_package/test.sh:99-104` 的断言 15–16）。
- 已试过的失败方案：①单行残缺输入（实拍 rc=0，分支不可达 ⇒ 断言永远不命中，提交 7df7b4e6e2 已改）；②把期望放宽成"0 或 1"（等于没有断言，弃）；
  ③上一棒用 `iroffer -c` 分支做断言（退出码随 tty 变化，见 M7，撤下）。
- 最终方案：两行输入；正向三条（rc=0 + `IRFR` 魔数 + `.state` 内嵌 `iroffer v1.4.b03`）+ 负向两条，逐条计数并核对 `PASS n == N_ASSERT`。
- 适用边界：任何"上游无测试套件 ⇒ 断言全靠自己写"的老 CLI；负向断言必须先证明失败分支可达。
- 既有条目：`knowledge/drafts/DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation.md` 问题 **:6**、根因 **:12**、可复用方案 **:18–:42**（统计口径 **:38**）、查重差异 **:64**；
  `knowledge/drafts/DRAFT-cuba-4.2.2-no-testsuite-demo-as-l1.md`；`knowledge/doc/E363.md`（harness 面）。
  这些都是"**零测试怎么记账 + 用什么替代验证**"，**没有**"失败分支可达性要先实测（老代码常把无效输入当空表成功）"这一条。
- 倾向：**create 候选 #2**；若主窗认为泛化度不足，就降 hit 并把"两行输入"的具体形态留在本归档 notes 即可。

### M5 构建入口"报错但 rc=0"的静默失败 ⇒ 生成物存在性判据
- 症状 / 复现 / 根因见「框架/环境侧发现」(d)（`Configure:105-106` 的裸 `exit`）。
- 已试过的失败方案：只看 `sh Configure` 的退出码判成败（**假绿**，本棒实拍 rc=0 而零生成物）。
- 最终方案：判据 = 退出码 + `Makefile`/`src/iroffer_config.h` 存在性；补丁后 W3 日志同时出现 `Determining OS... HarmonyOS` 与 `Creating Makefile... Done`。
- 既有条目：`knowledge/doc/E363.md` 根因分析 **:15**（原文含 "If setup and phase errors use bare exit … the harness can exit 0 with no test case executed"）、
  推荐方案 **:18–:20**（**:20** 原文含 "require a non-empty structured summary plus a generated artifact before declaring success"）、关键词 **:28**（"bare exit, exit code 0"）。
- 差异：E363 的载体是**上游 bash 测试 harness**（要求把它修成 fail-fast）；本包载体是**上游构建入口脚本**，我们不改它的 exit 语义，只把生成物存在性用作自证判据。
- 倾向：**hit 倾向**（"裸 exit ⇒ rc 0"这一物理事实与"要有 generated artifact 才算成功"的判据都已在 E363 的根因与处方里）；从严按载体不同则另说。

### M6 mkfifo jobserver 非致命 ⇒ `-j1`
- 症状原文：`make: jobserver mkfifo: /storage/…/GMfifo…: Operation not permitted`。
- 既有条目：`knowledge/doc/E074.md` 根因 **:15**、推荐 **:20–:27**（`make -j1`）；`knowledge/drafts/DRAFT-eigen-3.4.1-make-jobserver-mkfifo-nonfatal.md` Problem **:6**、Recommended triage **:19**、Relation **:43**。
- 倾向：**hit**，无新机制；配方按 R9 恒 `-j1`。

### M7 `iroffer -c` 的退出码随有无控制终端变化 ⇒ 撤下不当断言（不是 skip）
- 症状：有 tty 时 rc=1，无 tty（管道或 `</dev/null`）阻塞至 timeout 124。
- 既有条目：`knowledge/doc/E214.md:20`（非阻塞 read / `[ -t 0 ]` 终端检测等三方案）、`knowledge/drafts/DRAFT-E568-ohos-ci-open-pipe-stdin-test-hang.md`。
- 倾向：**hit**；处置是"整条撤下 + 在 `test_package/test.sh:9-11` 与 `test_package/MANIFEST.yml:48-51` 留痕"，
  因此 `skips` 仍记 **0**（没有条件跳过型断言，撤下的分支根本没进分母）。

### M8 取源自证与 `conandata.yml:21` 第二个 sha256 的来历（**不是第二个源件**）
- `:21` 的 `da68036fcc1dc02d1195bf02b6ada5e9a7865e946f95d29e43ddc5192f9ca0ed` 位于 `patches:` 块内，是 **`patches/0001-Configure.patch` 自身的 sha256**
  （`apply_conandata_patches` 的补丁完整性字段），与取源哈希（`:15` 的 `03a6ea4e…e507`）无关。
- 本棒自证：`sha256sum patches/0001-Configure.patch` = 上述值（逐字相等）；文件 1521 B、2 个 hunk ⇒ 无害、不是第二个下载件。
- 既有条目：`knowledge/doc/E425.md` 根因 **:14**、推荐 **:17**（Debian orig 的外部 submodule 面）。
- 倾向：不构成新机制（none 倾向）；取源链与 PF7 分类风险已在「取源」节披露。

## 独立审计第 1 轮整改（B 交付棒 主理-75，2026-09-27 06:54；不动构建输入、不重跑门禁）

本轮闭环独立审计第 1 轮的 2 条 P1 + 4 条 P2 + 2 条 P3，另有 3 条 P3 按指令**只留说明不改动**（见本节末）。
全部改动落在 `notes.md` / `manifest.yaml` / 两份草稿 / **新增随 PR 的证据件**：构建输入四件
（`conanfile.py`、`conandata.yml`、`test_package/**`、`patches/**`）本轮一件未动 ⇒ `.ci-result.json` 绑定的
`5cf15540b2` 轮构建输入未变，W3 证据继续有效（是否仍要按四件套④在新 HEAD 上重跑一次，判定由主窗作出）。

| 编号 | 问题（一句话） | 本轮处置 | 读者复核式（当场可跑） |
|---|---|---|---|
| Z75KA-01 **P1** | 草稿 `.kv` 的 `verification_cmd` 写成 `key: 竖线` 块标量，按字段取出的串 28 行、首字符是竖线、`sh -n` 报语法错 ⇒ 同 stem `.md` 的「原样执行 VC_RC=0」按字段**不可复现** | 字段只留**一行可执行命令**；期望读数 / 判读 / 非判别噪声三段迁到 `.md`「证据一」；顺带把 A3 取源臂收紧（排除 `$W/*`、要求文件内容含 `iroffer`）并把工作目录从 `z75k-verify` 换成本棒自有目录 `z75w-iroffer-fix/kc-pc-alias` | `parse_kv_file` 仍解得 **42 键**、`_REQUIRED_FIELDS` 16 项全部非空；取出的串落 `.sh` 后 `sh -n` RC=0；真跑 `VC_RC=0`，A1–A4 与审计复算**逐字相同**（实跑件 `reports/verification-cmd-run.log`） |
| Z75KA-02 **P1** | PR 可见文本按设备绝对路径 / 行数 / sha 指针引用了 5 件读者拿不到的件 | 取改法①：**探针与取证日志复制入仓** `archives/i/iroffer/1.4.b03/reports/` 并 `git add -f`，正文一律改仓内相对路径 + 真实行号；其中 `.ci-result.json`（框架状态件）与 `test-report.md`（finish 未就绪项）**不入提交**，改成「字段值 + 复算式」 | 见下「新增随 PR 的证据件」表；每条行号引用在 `git show HEAD:<件>` 态可数 |
| Z75KA-03 P2 | 本文件旧 221–222 行的 `conan-verify-report.md` md5/Date 是 04:36 那一版，已被 04:38 覆盖 | 改现值，并把本轮三次写出（04:28 / 04:36:18.446026 / 04:38:18.016312）写成流水，前两版标注「件已不在盘上、不可再核」 | `md5sum archives/i/iroffer/1.4.b03/reports/conan-verify-report.md` = `c6dae291112db1a6578e401b3fd91cc1`；`**Date**` 在该件第 6 行 = `2026-09-27T04:38:18.016312` |
| Z75KA-04 P2 | `manifest.yaml` 注释「本表 12 条」与同文件 `total: 16`/`passed: 16` 打架 | 注释改 16 并给三条复算式（机器可读字段本来就对，错的是随行说明） | `grep -c "^ok " test_package/test.sh` = 16；`test.sh:19` `N_ASSERT=16`；`test_package/MANIFEST.yml:52` `assertion_count: 16` |
| Z75KA-05 P2 | `patches_applied: []` 少报实存 1 枚补丁；行尾注释承诺 `refresh-patch --auto` 回填，但该脚本根本不写这个键 | 填真值 `0001-Configure.patch`（与 `conandata.yml:17-21` 的 `patches:` 一一对应），删掉未落实的承诺注释 | `ls archives/i/iroffer/1.4.b03/patches/` = 1 枚；`sha256sum patches/0001-Configure.patch` = `conandata.yml:21` 的 `da68036f…ca0ed` |
| Z75KA-06 P2 | 本文件旧 72 行引 `archives/m/metar/20190227.1` 作为「已合入同型归档」，但该目录在 HEAD 与 origin/main 里都不存在 ⇒ 引用指向空对象 | 删该例，改引三例**当场 grep 出来、且确在 origin/main 内**的同型件（`netris/0.52`、`a52dec/0.7.4`、`aalib/1.4p5`，含 conandata 行号） | `git grep -l "deb.debian.org/debian/pool" origin/main -- 'archives/**/conandata.yml'` = 304 条；`git cat-file -e origin/main:archives/m/metar/20190227.1/manifest.yaml` 失败（metar 那单尚未合入，故本棒不按其 PR 号引用） |
| Z75KA-07 P3 | 「必填 14 字段零缺失」的 14 在仓内没有出处 | 改指权威表与其真实项数（实质结论「零缺失」不变） | `scripts/ohc/graph.py:27-32` 的 `_REQUIRED_FIELDS` 数得 **16 项**，本稿 16 项全部存在且非空 |
| Z75KA-11 P3 | 「G1 12 条结构项逐条 ✅」与报告形状差一项 | 改 11 项 ✅ + 1 项 ℹ️（非阻塞提示） | `reports/conan-verify-report.md` 第 13–24 行共 12 项，其中第 21 行是 ℹ️ `R26: 未检测到静态链接配置`（✅ 计数 11） |

### 新增随 PR 的证据件

`reports/` 被 `.gitignore:96` 整目录忽略，故**八件**一律 `git add -f`（第 1 轮 6 件 + 第 2 轮随判决件补装 2 件，见下表末两行）；仓内该目录已有 1783 件先例（`git ls-tree -r --name-only origin/main` 口径），其中 `conan-verify-report.md` 167 件、`w3-local-ci.log` 17 件。

| 件（仓内相对路径） | 行数 | 字节 | sha256（全值） |
|---|---|---|---|
| `archives/i/iroffer/1.4.b03/reports/g0-configure.log` | 12 | 647 | 5a0f609a515e36006762264906ee13a535f08549d79e71c5d3f4b56444d37648 |
| `archives/i/iroffer/1.4.b03/reports/verification-cmd-run.log` | 20 | 960 | e429952088dea742e0748ff23a3bcd0e1fbf032267c6f1817c3cf8897de83da0 |
| `archives/i/iroffer/1.4.b03/reports/casefold-verify.log` | 19 | 952 | f3166a43d3802b5420bd377a0cb0b0e74824849655809e5b5e759ea972a0b1e5 |
| `archives/i/iroffer/1.4.b03/reports/casefold-probe.log` | 57 | 2748 | d838e5876ad5bf868c6f134f93ad5ee2a2c7b58e317c8e2e2db7ee9f3fe41515 |
| `archives/i/iroffer/1.4.b03/reports/conan-verify-report.md` | 44 | 1089 | d512cbbfa3f30e077a4457c08717f303a129c224965048ebb63b4930e81ae8df |
| `archives/i/iroffer/1.4.b03/reports/w3-local-ci.log` | 531 | 34321 | be86aeddeb36f02fab48a86d4843fd6362d3af6c9ed1b2d8ba792f5fa9c623ea |
| `archives/i/iroffer/1.4.b03/reports/z75e-audit-result.json` | 91 | 13978 | 15fad547efdb666f089d1db546c81515418a307328d2b06f7c1a2555f9679866 |
| `archives/i/iroffer/1.4.b03/reports/z75e-w4-report.log` | 45 | 4905 | 1dba03771b83a06253895ebb02e0ee5e9cf69e8d5b560ab79b154c0ddf426c69 |

| 件 | 来源 | 被谁引用 |
|---|---|---|
| `g0-configure.log` | 临时目录 `$HOME/tmp/ohc-verify-iroffer-6965g_fq/` 按字节复制 | 本文件 (c) 段、草稿 `.md` 证据二、草稿 `.kv` 的 source_event |
| `verification-cmd-run.log` | 本棒实跑整改后 `verification_cmd` 的原始输出 + harness 补 `VC_RC=0` | 草稿 `.md` 证据一、草稿 `.kv` 的 source_event |
| `casefold-verify.log` | 上一棒 05:0x 同族命令的原始输出（`~/tmp/uc2/z75k-iroffer-b/` 复制） | 草稿 `.md` 证据一的 A3 对照说明 |
| `casefold-probe.log` | 上一棒分臂长版流水（同上目录复制） | 草稿 `.kv` 的 source_event 留存备查 |
| `conan-verify-report.md` | 04:38 门禁 4 内嵌 verify 写出的现存件 | 本文件门禁 3 段（G1 图标计数亦出自该件） |
| `w3-local-ci.log` | 04:39 W3 本地 CI 模拟日志 | 本文件门禁 4 段：它是 `.ci-result.json` 的 `log_sha256` 的被哈希对象 |
| `z75e-audit-result.json` | 第 2 轮独立审计棒 z75e 的判决件（母本 `$HOME/tmp/uc2/z75e-iroffer-audit2/`，按字节原样复制入仓） | 本文件「独立审计第 2 轮整改」节、「取源」节的 PF7 小节 |
| `z75e-w4-report.log` | 同棒的 W4 阶段流水（同上母本复制） | 本文件同节的 W4 三段 rc |

### 三条 P3 本轮**不改动**、只如实留说明（判定由主窗作出）

- **Z75KA-08**：`scripts/ohc/preflight.py:570` 的 PF9 把**软件级** `archives/i/iroffer/commands.json`（4 段路径）判成「缺版本目录层」，而 PF8 又要求 CLI 包必须有软件级 `commands.json` ⇒ 两条闸对本包互斥，是工具的路径层误报、不是本包缺陷（`commands.json` 与包内文件均**未改**，`preflight` 也不在建 PR 通路上）。
- **Z75KA-13**：草稿 `.kv` 不是严格 YAML，`yaml.safe_load` 在第 74 行 column 37 抛 `ScannerError`（因 `error_signature` 里含冒号加空格），**同形是仓内常态、不是本稿的缺陷**——本棒当场复算（口径：集合 = `git ls-files -- knowledge` 里的 `.kv`，**不含** `archives/**`；「失败」= `yaml.safe_load` 抛异常；「同形」= 按 `scripts/ohc/models.py:parse_kv_file` 取串后**任一字段值含 `": "`**）：`.kv` 共 **2021** 份，失败 **1280** 份（63.3%），同形 **1332** 份；同一集合里异常消息逐字含 `mapping values are not allowed here` 的 **1042** 份（51.6%，这是更窄的口径）⇒ 未为此改写签名行。分集合读数（总数/失败/mapping-values/同形）：`knowledge/drafts` 1469/862/772/1035、`knowledge/graph` 542/411/264/290；把 `archives/**` 的 13 份并进来是 2034/1286/1048/1339 ⇒ 本条取**不含 archives** 那组。复算式与整改记录见「独立审计第 2 轮整改」节（第 2 轮判决件按上一版的行号把这句写作第 478 行，实际是本节 `Z75KA-13` 那一条，定位请用 `grep -n Z75KA-13`）；复核请按 `scripts/ohc/models.py:parse_kv_file` 取串（本棒即该口径，42 键全部解出）。
- **Z75KA-10**：`.ci-result.json` 的绑定 HEAD 是 `5cf15540b2`（04:39:13），其后的提交（含本轮）只动 notes/草稿/manifest 与新增证据件，构建输入未变 ⇒ 本轮**未重跑** `finish`/W3；`log_sha256` 与被哈希件 `reports/w3-local-ci.log` 现值仍逐字一致（复算式一）。「是否仍必须按四件套④在新 HEAD 上重新生成 `.ci-result.json`」由主窗定，本交付棒不下结论。

## 独立审计第 2 轮整改（B 交付棒 主理-75，2026-09-27 08:00；同样不动构建输入、不重跑门禁）

第 2 轮判决（z75e，第三方独立棒，**判决件按 §19 不随 PR、磁盘留档**）：`P0=0 P1=0 P2=2 P3=3`、`verdict=pass`。本轮只清该判决的 2 条 P2 + 2 条 P3；第 5 条 P3（`safety_boundary` 不在 `scripts/ohc/graph.py` 的 `_TEMPLATE_FIELDS` 白名单，白名单实测 64 项）按指令**不改动**，留待 promote 前处置。构建输入四件（`conanfile.py`、`conandata.yml`、`test_package/**`、`patches/**`）本轮仍一件未动 ⇒ `.ci-result.json` 那轮 W3 证据继续有效（是否按四件套④重生成由主窗定）。

| 编号 | 问题（一句话） | 本轮处置 | 读者复核式（当场可跑） |
|---|---|---|---|
| Z75E-01 **P2** | 整改后的 `verification_cmd` 只剩一行，但工作目录仍硬编码他棒暂存目录 `$HOME/tmp/uc2/z75w-iroffer-fix/kc-pc-alias`（命令自带 `rm -rf`），A3 判别臂又靠 `find $HOME/tmp/uc2 $HOME/tmp` 捞带外 pristine `Configure` ⇒ 同机可复现、**跨机不可复现**，换台机器静默退化成 `A3_skipped` | ①工作目录改本命令自建：`W=$(mktemp -d 2>/dev/null)`，为空回退 `$HOME/tmp/uc2/iroffer-kc-$$` 并 `mkdir -p`；`rm -rf` 整条删除（全新目录无需清，也不再写他棒目录）。②A3 臂改**自带取源**：按 `conandata.yml:14-:15` 的 url 下载 `.orig`、先核 `sha256` 逐字等于 `03a6ea4e…e507` 才 `tar -xzf … iroffer-1.4.b03.orig/Configure` 取用；下载失败或哈希不符显式打 `A3_skipped=download-or-sha-mismatch got=[…]`（可判别）。③同 stem `.md` 的取串口径与 A3 说明同步改写；字段仍**单行**（1876 字符，第 1 轮 Z75KA-01 的块标量 P1 不复发） | `parse_kv_file` 取串后 `sh -n` RC=0、干净环境 `VC_RC=0`；`A1_ls`/`A1_unique_inodes=1`/`A2_rc=127`/`A3_rc=1`/`A3_hits`/`A3_Makefile=no A3_config_h=no`/`A4_*` 全部逐字复现随 PR 的 `reports/verification-cmd-run.log`，`A3_skipped` **消失**；键数仍 **42** |
| Z75E-02 **P2** | 本文件 `Z75KA-13` 那一条写「仓内 1193 份 `.kv` 有 696 份同形」——出自第 1 轮判决件正文被逐字抄进 PR 可见文本，**不可复算** | 换成本棒当场复算的数与口径（见上一条同节的 Z75KA-13 行）：集合 `git ls-files -- knowledge` 内 `.kv` **2021** 份、`yaml.safe_load` 失败 **1280** 份、同形（任一字段值含 `": "`）**1332** 份、窄口径 mapping-values 同形 **1042** 份 ⇒ 结论（不为此改写 `error_signature`）不变 | 复算式见本节末围栏，仓根执行，输出即 `2021 1280 1042 1332` |
| Z75E-03 P3 | 草稿 `.md` 的「证据二」标题写「非 PR 内文件，随临时目录留存」，与同节正文（该件已 `git add -f` 入仓、读者可在 PR 内数行）自相矛盾 | 标题统一为「框架自己那一次真实运行的日志（随 PR 于 `reports/`，即 `archives/i/iroffer/1.4.b03/reports/g0-configure.log`）」 | `grep -n "^### 证据二" knowledge/drafts/DRAFT-iroffer-1.4.b03-hmdfs-case-fold-configure-dispatch.md` 读回的标题与同节正文同一口径 |
| Z75E-04 P3 | 同节正文有乱码词「按字节**擫身**入仓」（第 1 轮整改引入的单点文字缺陷） | 改「按字节**原样复制**入仓」，与 `casefold-verify.log` 等其余各处用词一致 | `grep -c 原样复制 knowledge/drafts/DRAFT-iroffer-1.4.b03-hmdfs-case-fold-configure-dispatch.md` = 1，且同一文件内那处乱码词已计数 0（复核式：把上面 `grep -c` 的关键词换成它） |
| PF7（第 1 轮遗留，本轮落 notes） | `scripts/ohc/preflight.py` 的 PF7 对本包命中 **2 处**（`conandata.yml:14`、`manifest.yaml:11`），处方是「确属官方托管例外须 PR 说明并 `--no-preflight` 显式跳过」，此前只在「取源」段的 ⚠ 披露里带过一句 | 在「取源」节新增 `### PF7 源URL闸的例外处置` 小节：落本棒一手复算的池件 `200` / `Content-Length: 131571` / `sha256 03a6ea4e…e507` 三向一致、登记表址缺 `/debian/` 段 `404`、官方上游与维护者站 5 组负证据、`preflight.py:422-:424` 与 `scripts/gitcode_pr.py:1130` 的处方行号；PF7 记为 **P1-已例外处置**（不写 P3），⛔ 未改 `conandata.yml`/`manifest.yaml` 的 url | `curl -s -o /dev/null -w "%{http_code}" 逐一取上列各候选址` 与 `sha256sum` 池件；命中位点与 rc 另见随 PR 的 `reports/z75e-audit-result.json` 的 `Z75KA-08` 段 |

### Z75E-02 复算式（仓根执行，只读；48 秒量级）

```
python3 - <<'PY'
import subprocess, sys, yaml
sys.path.insert(0, "scripts")
from ohc.models import parse_kv_file
fs=[f for f in subprocess.run(["git","ls-files","--","knowledge"],
        capture_output=True, text=True).stdout.split() if f.endswith(".kv")]
fail=morph=colon=0
for f in fs:
    try: yaml.safe_load(open(f, encoding="utf-8").read())
    except Exception as e:
        fail += 1
        if "mapping values are not allowed here" in str(e): morph += 1
    if any(": " in (v or "") for v in parse_kv_file(f).values()): colon += 1
print("total=%d safeload_fail=%d mapping_values=%d colon_space_value=%d"
      % (len(fs), fail, morph, colon))
PY
```

输出（2026-09-27 08:00 本棒仓根实跑，`48` 秒）：total=2021 safeload_fail=1280 mapping_values=1042 colon_space_value=1332
把 pathspec 换成 `knowledge/drafts`、`knowledge/graph`、`knowledge archives` 即得上文三组分集合读数（1469/862/772/1035、542/411/264/290、2034/1286/1048/1339）。

## 路径 B 声明（3+2；B 判定 = **create**，本 PR 只带 1 条知识）

- **适配路径**：路径 A（1 枚补丁 `patches/0001-Configure.patch`：2 hunk、`+11 -1`、净 +10、1521 B，其 `sha256sum` 逐字等于 `conandata.yml:21` 的 `da68036f…ca0ed` ⇒ 那是补丁完整性字段而非第二个源件）+ 配方 + `test_package/test.sh` 的 16 条消费者断言；**路径 B（create，1 条）**，落 `knowledge/drafts/DRAFT-iroffer-1.4.b03-hmdfs-case-fold-configure-dispatch.kv` 与同 stem `.md`（`.kv` 用仓内 `scripts/ohc/models.py` 的 `parse_kv_file` 解得 **42 键**、`scripts/ohc/graph.py:27-32` 的 `_REQUIRED_FIELDS` **16 项全部存在且非空**）。
- **使用知识库**：逐条给面与行号（⛔ 不写成「参考了若干条目」）——
  · `DRAFT-E2167-handwritten-configure-conan-injected-args`：`.kv:2` 签名 `Unknown option --oldincludedir`（**参数被拒**）、`.kv:6` 根因＝手写脚本校验注入参数白名单、`.kv:7` 与 `.md:19` 处方＝`generate()` 里 `tc.update_configure_args({"--oldincludedir": None})`、`.kv:18` 的 `applies_to` 含 `any-handwritten-configure-upstream`。**取的是对照面**：本包 `conanfile.py:57-58` 的 `generate()` 是 `pass`、不经 `AutotoolsToolchain` ⇒ 剪参数面不存在、该处方在本包字面不可执行；且 E2167 不含「框架调用的 `./configure` 被大小写折叠换成另一个脚本」这一半 ⇒ 由此升 create。
  · E160（`knowledge/doc/E160.md:15` 根因、`:18` 方法 `config-guess-harmonyos-patch`、`:20` 说明给 `config/config.guess` 加 HarmonyOS→Linux/LIBC=musl 分支、`:24` 给 sed）：M1 的 OS 白名单映射按该家族口径处理，但**载体不同**——本包无 config.guess，落点是 `Configure:104` 的 `case "$ostype"`（补丁 hunk1）。
  · E363（`knowledge/doc/E363.md:15` 根因含 "bare exit … the harness can exit 0 with no test case executed"、`:18` 方法、`:20` 要求 "a generated artifact before declaring success"、`:28` 关键词 "bare exit, exit code 0"）：M5 的「入口报错却 rc=0 ⇒ 判据加生成物存在性」承接其判据，载体由测试 harness 换成构建入口脚本。
  · E074（`knowledge/doc/E074.md:15` 根因 SELinux 禁 FIFO、`:20` 方法 `env-var-override`、`:26` 命令 `make -j1`）：配方 `conanfile.py:76` 恒 `-j1`。
  · E214（`knowledge/doc/E214.md:15` 根因交互 `read` 阻塞、`:18` 方法 `non-blocking-read`、`:20` 三方案）：M7 的 `iroffer -c` 分支按「不可复现即整条撤下」处置，留痕在 `test_package/test.sh:9-11` 与 `test_package/MANIFEST.yml:48-51`；撤下项不进分母 ⇒ `skips` 记 **0**。
  · E098（`knowledge/graph/E098.kv:19` 根因 toybox 无 `install`、`:25` 方法 `cp-chmod-replace`）：`package()` 用 `copy()` 落盘（`conanfile.py:78-:92`）。
  · 通用池姊妹草稿 `DRAFT-vor-0.5.8-hmdfs-case-insensitive-pc-alias-self-reference`：同根（HMDFS 大小写折叠）不同面（它是 pkg-config 的 `.pc` 别名自引用，本条是构建入口派发）。该件在分支 `feat/vor-0.5.8`，本 PR 基线 `origin/main` 内尚无该文件 ⇒ 按名引用、不给行号；引它只为说明本条不是「大小写折叠族」的重复申报。
- **知识库扩展**：**1 条** = 本文件 M3 一节（起于第 383 行）所记机制——HMDFS 大小写折叠使调用方写下的 `./configure` 解析到上游手写的 `Configure`（`Configure:45` 的 `while getopts 'hedpw'` 只认 `-h/-e/-d/-p/-w`），框架注入的 GNU 长选项因此被 getopts 判 `illegal option`；`scripts/ohc/clean_verify.py:130-132` 的小写存在性检查因折叠恒真、`:69` 与 `:138` 拼出的 `./configure --prefix=…` 触发 `:181` 的 G0 红（同族第二调用点 `scripts/ohc/driver.py:830`）。配方侧无注入面（`conanfile.py:57-58`），正解是绕开框架 configure 步骤、按 `conanfile.py:72` 与 `:76` 直接驱动并复核生成物。载体：`knowledge/drafts/DRAFT-iroffer-1.4.b03-hmdfs-case-fold-configure-dispatch.kv` 的 `root_cause`（单行）与 `verification_cmd`（四臂实拍读数 `A1_unique_inodes=1`｜`A2_rc=127`｜`A3_rc=1` 且 `A3_Makefile=no A3_config_h=no`｜`A4` 小写桩覆盖真身），draft-review 预审 `DR_RC=0`、`signature/root_cause/rec` 三项 ✅、建议 create（TOP1 E232 score=0.19，全部低于灰区阈值 0.30）。同 run 的 M4（无测试老 CLI 的负向分支可达性）**不随本 PR 申报**，按 AGENTS §9「一 PR 一知识」入通用池 `经验文档/B草稿库/DRAFT-iroffer-1.4.b03-neg-branch-reachability-zero-test-cli.{kv,md}`。
- **关联 Issue**：#3506（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3506）
- **PR 前缀**：`【知识库扩展】`（标题结构 `【知识库扩展】feat(iroffer): 1.4.b03 适配 HarmonyOS PC`）
## CI 复现与断言形态整改（2026-09-27，CIW-S4k2 棒，B 机）

**现象**：CI 2026-09-27 08:59:58 的 `conan-build-test` 判红，唯一失败点是旧 `test_package/test.sh:91-92`
的 `grep -a -q "iroffer v1\.4\.b03" conv.state`；日志里 1-13 条全 PASS、第 14 条 FAIL，
`conv.txt` 五行与本机逐字一致（`** growing meminfo from 0 to 1` / `** Converting empty.xdcc ... ` /
`** WARNING: Empty XDCC File, Starting With No Packs Offered` / `** Saving State File... ` / `** Done`）。

**两侧身份（先对身份再谈复现）**：CI 现场 recipe rev `4bb6ff5647b10d5db012134107ddd99d`、
package id `6b129b068851896169fae42d399fa922d239ce8a`、package rev `c6b5061c143d5febeb015a05ac2edd5d`，
CONAN_HOME `/storage/Users/currentUser/.cache/conan2`，包目录短哈希 `iroffeb19b2f016957`。
本棒 15:26 在 B 机 `conan-verify` 的依赖图读数 `#4bb6ff…:6b129b06…#c6b5061c…` —— **recipe rev /
package id / package rev 三项与 CI 逐字相同**，`conaninfo.txt` 的 settings 八项也逐字相同
（arch=armv8 build_type=Release compiler=clang cppstd=17 libcxx=libc++ compiler.version=15
os=OHOS os.version=6.0）。唯一不同的是 conan 的**包目录短哈希**（本机 `irofff8f9f7eb95007`，
CI `iroffeb19b2f016957`），它不携带 settings/options 维度（package_id 才是那些维度的哈希，且相同），
⇒ **两侧跑的是同一枚二进制**，"本地 PASS 不能否证 CI"这条不成立，反过来也意味着差异只能在**测试脚本
用到的工具**那一侧。

**定性（一手实测，同一枚 `convertxdccfile` 产出的同一份 252 B 产物）**：

| 工具 | 命令 | rc |
|---|---|---|
| `/data/service/hnp/bin/grep`（GNU grep 3.12） | `grep -a -q "iroffer v1\.4\.b03"` | **0**（命中） |
| `/usr/bin/grep`＝`/system/bin/grep`＝`/bin/grep`（toybox 0.8.12） | 同上 | **1**（不命中，stderr 为空、不报未知选项） |
| toybox grep | `-a -q "iroffer"`、`-a -q "1\.4\.b03"` | 1 / 1（GNU 同两条为 0 / 0） |
| toybox grep | `cat conv.state \| grep -a -q "iroffer v1\.4\.b03"` | 1（管道也不命中） |

⇒ 旧断言把结论押在"PATH 上恰好是 GNU grep 且 `-a` 认二进制文件"这一**环境属性**上。CI 的 `test()` 走
`env="conanrun"`（VirtualRunEnv 只把包目录加进 PATH；profile 里的 `/data/service/hnp/bin` 属 `[buildenv]`），
`grep` 落回 toybox；本机 agent 的登录 PATH 含 `/data/service/hnp/bin`，所以 W3 一直 16/16。
**复现成对读数（断点件在 `~/tmp/uc2/ciw-s4-iroffer-b2/`）**：
`env -i PATH=/system/bin:/vendor/bin:/usr/bin:/bin … bash <HEAD 版 test.sh>` ⇒ PASS[13] 后
`FAIL: .state 未内嵌本包版本串`、rc=1（`toybox-old-test.log`，与 CI 日志同形）；
同一路径跑整改后的 `test.sh` ⇒ `PASS 16/16`、rc=0（`toybox-new-test.log`）。

**上游契约（回答"版本串是无条件写入还是条件写入"）**：落点 `src/iroffer_statefile.c:179` `write_statefile()`，
`convertxdccfile.c:302` 直接调用。逐行：

```c
  :93   #define STATEFILE_MAGIC (('I' << 24) | ('R' << 16) | ('F' << 8) | 'R')
  :94   #define STATEFILE_VERSION 1
  :49   STATEFILE_TAG_IROFFER_VERSION      =  1 << 8,
  :223-224  ir_uint32 magic = htonl(STATEFILE_MAGIC);   ir_boutput_write(&bout, &magic, …);   // off 0..3
  :233-234  ir_uint32 version = htonl(STATEFILE_VERSION); ir_boutput_write(&bout, &version,…); // off 4..7
  :252    hdr->tag = STATEFILE_TAG_IROFFER_VERSION;
  :253    hdr->length = sizeof(statefile_hdr_t);
  :256-257 length = snprintf(next, maxtextlength-1,
                             "iroffer v" VERSIONLONG ", %s", gdata.osstring);   // off 16 起
  :259-263 if ((length < 0) || (length >= maxtextlength)) { outerror(... "Version too long! %d" ...) }  // 唯一跳过分支
  :266-267 else { hdr->length += ceiling(length+1, 4); write_statefile_item(&bout, data); }
```

结论：**版本串是无条件写入的**，且是头部 8 字节之后的第一个条目；唯一不写的分支是 `:259`
（串长 ≥ `maxtextlength=512`，`iroffer_defines.h:128`），触发时 `:261` 必打 `Version too long!` 告警
——CI 与本机的 `conv.txt` 里都没有那条告警 ⇒ 条目必然已写。`VERSIONLONG` 由 `Configure` 生成
（`Configure:8` `VERSION=1.4.b03`、`Configure:21` `VERSIONLONG="$VERSION [$CSET]"`、`Configure:120` 写进
`src/iroffer_config.h`；`$CSET` 取 tarball 里的 `.cset_number`，缺失则为 `Unknown`），CI 日志
`Configure for iroffer 1.4.b03 [20051213024435]` 与本机 `iroffer_config.h:3` 完全一致 ⇒
**偏移 16 起的 18 个字节恒为 `"iroffer v1.4.b03 ["`，与 `$CSET` 取值无关**；随环境变的只有
`", %s"` 尾巴 —— `gdata.osstring` 在本工具里是 NULL（`convertxdccfile.c:252` 只 `memset` 过 `gdata`，
唯一赋值点是 `iroffer_utilities.c:186-188` 的 uname 分支，`convertxdccfile` 不调用），打印形态由 libc 决定，
故新判据**刻意只校验到偏移 33**、不碰尾巴。本机该产物头部 34 字节逐字节读数：
`4952465200000001000001000000003469726f666665722076312e342e623033205b`
（= `"IRFR"` | htonl(1) | tag=htonl(1<<8) | len=htonl(52) | `"iroffer v1.4.b03 ["`）。

**整改内容（改形态、不改判据强度）**：断言 13、14 换成偏移级逐字节校验，只用
`od -An -tx1/-tu1`（toybox 与 GNU od 读数逐字一致）与 `head -c … | tail -c …` 切片，**不再对二进制文件用 grep**；
13 校验头 8 字节 == `4952465200000001`；14 校验 tag == `00000100`、条目长度高 3 字节为 0、低字节 ∈[28,252]
且为 4 的倍数（即 `8 + ceiling(len+1,4)`）、偏移 16 起 == `"iroffer v1.4.b03 ["`。
条数不变：`grep -c "^ok " test_package/test.sh` = 16、`test.sh:31` `N_ASSERT=16`、
`test_package/MANIFEST.yml` `assertion_count: 16` 三处复算式仍互相成立。
⛔ 未删除任何断言、未把判据放宽成恒真、未加 `|| true` 之类掩盖；`test_package/MANIFEST.yml` 与
`test_package/conanfile.py` 的描述同步改写并记下这条工具依赖。附带修正：`MANIFEST.yml` 的
`command` 字段原写 `sh test.sh`，与 `conanfile.py` 实际用的 `bash` 不符，已改为 `bash test.sh`。

**复跑记录（B 机，CIW-S4k2，CONAN_HOME=`~/tmp/ch/home-iroffer`）**：
先 `sh ~/tmp/uc2/gate.sh 4000` ⇒ `GATE_PASS`（MemAvailable 19297MB、编译器进程 0），再
`sh ~/tmp/uc2/build-slot.sh --kind short` 取机动槽；
- `python3 scripts/ohc-run.py conan-verify iroffer 1.4.b03` ⇒ rc=0，G1/G2/G3/G4 全 PASS，
  G2 内 `conan create` 的 test_package 打印 `PASS[13]`/`PASS[14]`（新文案）至 `PASS 16/16`
  （`reports/conan-create.log:94-111`）。
- `python3 scripts/ohc-run.py finish iroffer 1.4.b03 built` ⇒ [5/10] 打印「✅ W3 本地 CI 模拟通过」，
  `.ci-result.json` `exit_code=0`、`log_sha256=9a9e7fb81e719bfbc13320b62dec5cfd9939547d35d97bbdccecdea55af16420`
  （15:28:01 落盘，`reports/w3-local-ci.log` mtime 15:28 且 `^PASS[` 计 16 条 —— 是本轮新日志而非旧件复用）。
  finish 整体 rc=2 的两处 HANDOFF（[3/10] G0 的 `FAILED_STEP: configure`、Step6 知识整理）与本包既有记录
  同形同位（对照前一窗口 04:29 的 `fin.out` 第 39/83/141/143 行），非本轮引入。

**遗留风险（供后续巡检参考）**：toybox 与 GNU 工具对**二进制文件**的行为差是家族性的，不止本包 ——
任何归档里"`grep -a` 打二进制产物"的断言都可能同样红在 CI 而不红在本地。本棒不改框架、不代改他人归档，
只把本包的这两条改成偏移级判据。

---

**编译结束**: 2026-09-27 15:27
**最终状态**: built
