# tiger 3.2.4 适配笔记（A 类 · 本机前置阶段）

## 1. 状态

| 项 | 值 |
|----|----|
| 库 / 版本 | tiger / 3.2.4 |
| 任务类型 | A 类（前置适配） |
| 任务 ID | 11141 |
| 分支 | `feat/tiger-3.2.4` |
| worktree | `D:\harmonyos\worktrees\tiger` |
| 包路径 | `archives/t/tiger/3.2.4` |
| 本轮状态 | pending —— 配方、补丁、test_package 已就绪，等待真机 `conan create` + shadow CI |
| 上游测试 | 无测试套件（Makefile/Makefile.in 无 `check` 目标） |

## 2. 源码与身份确认

- 上游项目：Tiger —— UNIX/Linux 安全审计与入侵检测工具集
  （<https://savannah.nongnu.org/projects/tiger/>）。
- 任务页给出的版本号 `3.2.4`，对应上游唯一发布制品
  `tiger_3.2.4rc1.tar.gz`：Savannah 发布目录里 3.2.4 系列只有 rc1，
  上游 git 标签为 `version_3_2` / `version_3_2_1` / `version_3_2_2` /
  `version_3_2_3`，**没有** `version_3_2_4`，也从未打过正式 3.2.4 包。
- 下载与校验（本机实测）：

  | 项 | 值 |
  |----|----|
  | URL | `https://download.savannah.nongnu.org/releases/tiger/tiger_3.2.4rc1.tar.gz` |
  | sha256 | `91b259da8f0d3f6244f815c2b067ea4433b9ae378308ce63c2eb60b93efe7f96` |
  | md5 | `169207ac9c211983a7ef9d19c1e5b3cb` |

  md5 与 Debian 源码包 `tiger_3.2.4~rc1.orig.tar.gz` 完全一致，
  证明官方 tarball 与发行版 orig 源码包同源（R39：使用官方源）。
- 包内 `version` 文件内容为 `3.2.4rc1`，`version.h` 为
  `3.2.4rc1, 2018.02.10.20.30`。

## 3. 构建系统分析

| 项 | 结论 |
|----|------|
| 构建系统 | Autotools 变体：预生成 `configure`（GNU Autoconf 2.69）+ 手写 `Makefile.in`，**没有 automake / libtool / CMake / meson** |
| 顶层 Makefile | `all:` = `cd c && make` + `cd doc && make`；`install:` 依赖 `installdirs installbinaries installconfig installmanpages` |
| C 程序 | `c/` 下 5 个：`getpermit` `snefru` `md5` `testsuid` `realpath`，用 `% : %.c` 模式规则单独编译，无 `configure` 探测 |
| 文档目标 | `doc/`：`*.txt` → `*.html`（`sh ../util/doc2html`）+ `explain.idx`（`util/genmsgidx`） |
| VPATH | **不支持**。`c/Makefile` 与 `doc/Makefile` 都直接在当前目录编译/生成，必须 in-source 构建 |
| `config.sub/guess` | `configure.in` 没有 `AC_CANONICAL_*`，不涉及 OHOS 三元组识别（无需 E007 类修复） |
| 上游测试 | 无。`Makefile.in` / `c/Makefile.in` / `doc/Makefile.in` 均无 `check` 目标 |
| install 依赖 | `AC_PROG_INSTALL`，但 tarball 自带 `install.sh`（shtool install），因此没有 GNU `install` 时 configure 仍有回退（不会触发 `cannot find install-sh` 致命错误） |

安装路径由 `configure.in` 的 `--with-*` 选项决定，配方里显式指定为包内布局：

```
<pkg>/bin/{tiger,tigexp,tigercron}          # 3 个命令入口
<pkg>/share/tiger/{config,initdefs,syslist,tigerrc 模板,scripts/,systems/,util/,doc/,bin/}
                                            # tiger home；bin/ 内是 5 个 C 辅助程序
<pkg>/etc/tiger/{tigerrc,cronrc}            # 配置模板
<pkg>/var/tiger/{run,log}                   # 运行/日志目录（空目录）
<pkg>/share/man/man8/{tiger,tigexp,tigercron}.8
```

## 4. W0 依赖检查

- `requirements()` 为空：tiger 只链接 libc；运行期通过 shell 调用平台工具
  （sh/awk/sed/grep/ls/...），没有 Conan 级依赖。
- 制品仓占用检查（R37）：

  ```text
  conan download tiger/3.2.4 -r=ohpcd --only-recipe
    -> exit 1, "error:system acceleration policy not enabled"（未发布）
  conan download zlib/1.3.1 -r=ohpcd --only-recipe
    -> exit 0（对照组：远端与命令本身可用）
  ```

  结论：`tiger/3.2.4` 版本号未被占用，无依赖需要先发布，可以直接进入构建验证。

## 5. 本轮补丁

### 0001-use-32bit-hash-word-types.patch（正确性，必须）

`c/md5.c` 与 `c/snefru.c` 都是 1990 年代的参考实现，把 32 位字长声明成
`unsigned long int`：

```c
typedef unsigned long int UINT4;    /* c/md5.c  */
typedef unsigned long int word32;   /* c/snefru.c，注释明确写 "word32 MUST be 32 bits" */
```

aarch64 / HarmonyOS 是 LP64，`unsigned long int` 是 **64 位**，加法不再按
2^32 回绕，摘要会静默算错。补丁把两者固定为 `uint32_t`。

本机对照实验（MinGW gcc 12.2，同一份源码只改这一个 typedef）：

| 二进制 | `md5 -x` 的 `MD5("abc")` | `snefru` 对 `123456789\n` |
|--------|--------------------------|---------------------------|
| 32 位字长（正确） | `900150983cd24fb0d6963f7d28e17f72` ✅ RFC 1321 | `4ca72639 e40e9ab9 c0c3f523 c4449b39 ...` ✅ c/snefru.c 内注释向量 |
| 64 位字长（LP64 实况） | `7999dc75e8da648c6727e137c5b77803` ❌ | `ffffff0a ffffff8d ffffff1c ffffff80 ...` ❌ |

7 组 RFC 1321 MD5 测试向量与 c/snefru.c 头部自带的 Snefru 向量在补丁后全部
匹配（见第 7 节证据）。不打这个补丁，`tiger -G` 生成的签名、
`check_signatures` 的比对在 OHOS 上全是错的。

### 0002-find-posix-tools-in-system-bin.patch（构建 + 运行，必须）

`tigexp` 与 `util/genmsgidx` 各有一个自带 `findcmd()`，搜索路径写死：

```sh
srch=/usr/ucb:/usr/bin:/bin:/etc:/usr/etc      # tigexp
SRCH=/usr/ucb:/usr/bin:/bin:/etc:/usr/etc      # util/genmsgidx
```

OHOS 没有 `/bin`（E165），因此：

- `make` 阶段 `doc/Makefile` 的 `explain.idx` 目标会因
  `haveallof commands AWK LS BASENAME || exit 1` 直接失败 → **整个 `make` 失败**；
- `bin/tigexp` 会因找不到 `grep` 直接退出 1。

补丁在这两个搜索路径末尾追加 `/system/bin`（追加而非替换，Linux 侧行为不变）。

## 6. 配方内的 OHOS 适配点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `configure` 首行 `#! /bin/sh`，OHOS 无 `/bin/sh`（E165） | `build()` 中按本机探测结果改写为 `/system/bin/sh` |
| 2 | `Makefile.in` 写死 `SHELL = /bin/sh`，而 make 忽略环境变量 SHELL | `autotools.make(args=["-j1", "SHELL=/system/bin/sh"])` |
| 3 | 安装出的 300+ 个脚本仍是 `#!/bin/sh`，无法直接执行 | `package()` 中按 E165 统一改写已安装脚本首行的解释器；同时把 `/usr/bin/perl`、`/usr/local/bin/perl` 映射到实际存在的 perl |
| 4 | `configure` 通过 `$SHELL`（= profile 的 `CONFIG_SHELL=/data/service/hnp/bin/bash`）运行 `config.status` | **本轮不改**：该变量由 profile 的 `conanbuildenv-*.sh` 导出，晚于 recipe 的 toolchain 脚本，recipe 内 define 不生效；真机首轮若报 hnp bash 不可执行，再按 libunistring 的做法显式覆盖（见第 8/9 节） |
| 5 | `configure`/`config.status` 的 `umask 077` 在 HMDFS 上产生 `drwx--S---`（E129） | 两处都改写为 `umask 022`（`config.status` 在 configure 之后处理） |
| 6 | Makefile 不支持 VPATH | `basic_layout(self, src_folder=".", build_folder=".")`，in-source 构建 |
| 7 | 上游 `install.sh`（shtool）无 shebang，靠 shell 的 ENOEXEC 回退执行 | 不改动；真机首轮确认 `install`/`ginstall` 是否在 PATH（有则走 GNU install，避免该回退路径） |

## 7. 本机验证（Windows 主机，无 OHOS aarch64 环境）

| 验证项 | 方法 | 结果 |
|--------|------|------|
| 源码 URL + sha256 | `conan source .`（独立 CONAN_HOME） | `Sources correctly downloaded`，解包成功 |
| 补丁严格性 | 用 Conan 同一路径复现 `patch_ng.fromfile().apply(strip=0, fuzz=False)` | 两个补丁均 apply 成功，补丁后关键内容断言全部命中 |
| 补丁未破坏 shell 语法 | `sh -n tigexp` / `sh -n util/genmsgidx` | exit 0 |
| md5 摘要正确性 | 编译补丁后的 `c/md5.c`，跑 `-x` 全部 RFC 1321 向量 | 7/7 匹配 |
| snefru 摘要正确性 | 编译补丁后的 `c/snefru.c`，输入 `123456789\n` | 与 c/snefru.c 自带向量一致 |
| LP64 根因复现 | 同一源码把字长 typedef 改成 64 位再编译 | md5 / snefru 摘要全部错误（见第 5 节表格） |
| `explain.idx` 生成 | 在 MSYS POSIX 环境下执行补丁后的 `util/genmsgidx` | exit 0，生成 433 条索引 |
| `tigexp` 解释查询 | `TIGERHOMEDIR=<tree> sh tigexp init001e` | 输出 doc/config.txt 中 `%init001e` 的正文，exit 0 |
| test_package 演练 | 用真实 md5/snefru（补丁后编译）+ 真实 tiger/tigexp 脚本搭假包，跑完整 `test_tiger.sh` | 11/11 断言通过（`realpath`/`getpermit`/`testsuid` 因 MinGW 缺 POSIX 头文件用替身） |
| 配方可导出 | `conan export . --user=ohpcd --channel=stable` + `conan inspect` | 导出 conanfile/conandata/2 个 patch，`package_type=application` |

> 说明：Windows 上无法编译 `getpermit.c`（缺 `pwd.h`）、`realpath.c`（缺 `readlink`）、
> `testsuid.c`（缺 `setuid`），这三项的真实验证必须在真机完成。MD5/Snefru
> 两项恰好是补丁 0001 的核心，已经用真实二进制验证。

## 8. 已知限制 / 真机待确认项

1. **check 逻辑仍无法在 OHOS 上真正跑完整**：`tiger` 主流程在
   `config` 里把 `PATH` 重置为 `/sbin:/usr/sbin:/bin:/usr/bin`，平台配置
   （`systems/Linux/*/config`、`systems/default/config`）与
   `util/gethostinfo`、`syslist` 的 `findcmd()` 也全部写死传统 FHS 路径；
   再加上 `/etc/passwd`、`/var/log`、`ps aux` 等 Linux 专有数据源在 OHOS
   不存在。本轮只保证**构建、打包、命令入口、辅助二进制和数据索引**可用，
   真正的检查流程需要后续为 OHOS 增加平台配置（见"下一步"）。
2. `tiger -v` 在 OHOS 上会打印 `tiger, version undetermined`：`config` 用
   `/bin/cat $TIGERHOMEDIR/version.h` 读取版本，而 OHOS 没有 `/bin/cat`；
   另外上游 `make install` 本身并不安装 `version.h`（Debian 是在
   `debian/rules` 里手工补装的）。若要显示真实版本，需要同时处理这两点。
3. `scripts/check_network` 缺 `/usr/bin/perl`（已在 package() 里映射）；
   `systems/Linux/2/*` 中的 bash 脚本依赖 `/bin/bash` → 映射到 hnp bash。
4. `.so`/ELF 签名、`chmod +x` 在 HMDFS 上是否生效（E087）需要真机确认；
   `run_script()` 会拒绝执行没有执行位的检查脚本。
5. 上游 tarball 里 `systems/Linux/3`、`systems/Linux/4` 是指向 `2` 的相对
   软链接，`make install` 用 `tar` 复制；真机上若软链接受限（E018），
   install 可能报错，需要在首轮日志中确认。
6. `configure` 用 `$SHELL` 运行 `config.status`，该值来自 profile 的
   `CONFIG_SHELL=/data/service/hnp/bin/bash`。本轮未覆盖 recipe 侧（会被
   `conanbuildenv-*.sh` 覆盖回去）。若首轮报该 bash 不可执行，按 libunistring
   的做法显式覆盖：不走 `Autotools.configure()`，改为

   ```python
   with env.vars(self).apply():
       self.run(f'SHELL={shell} CONFIG_SHELL={shell} "{shell}" "{configure}" ...')
   ```

## 10. 真机验证记录（第一轮，2026-09-29）

真机：`HarmonyOS / HongMeng Kernel 1.12.0 / aarch64 / Toybox`，登录用户 `currentUser`，
Conan 2.31.1（`$HOME/.local/bin/conan`）。

隔离 job（沿用设备既有约定，参考 medusa 任务）：

```text
$HOME/ohos-users/tiger/tiger-3.2.4-build/
  conan-home/            # 独立 CONAN_HOME（copy 自 $HOME/.conan2 的 settings.yml/global.conf/remotes.json/profiles）
  repo/build_in_harmonyos/   # 最小仓：ci/ + archives/t/tiger/
  env.sh  run-tiger.sh
```

执行入口：`sh run-tiger.sh` → `$HOME/bin/ohos-test-runner.sh --mode smoke --try-lock
--workdir <repo> -- zsh ci/conan/build_and_test.sh archives/t/tiger/3.2.4`。

### 10.1 现场环境（与仓库 profile 的差异，重要）

| 项 | 实测 | 影响 |
|----|------|------|
| `ci/conan/profiles/ohos-aarch64` 的编译器 | `/data/service/hnp/bin/clang` **不存在** | 该 profile 在本机不可直接使用 |
| `ohos-aarch64-localdevice` | `/storage/Users/currentUser/usr/local/bin/clang`（clang-15 wrapper，带 sysroot/lld/code-sign） | 本机可用的 profile；必须 `CONAN_PROFILE=ohos-aarch64-localdevice` |
| `/bin/sh` | **存在**，`/bin -> /system/bin` | E165 前提在本机版本不成立；配方按探测结果仍写 `/system/bin/sh`，两者同文件，无副作用 |
| `install` / `ginstall` | `/bin/install`（toybox，不可读）与 `$HOME/usr/local/bin/ginstall`（GNU） | configure 走 `ginstall`；上游 `install.sh` 回退未触发 |
| `install.sh`（shtool） | 未使用 | — |
| 资源 | `Mem: 25 GB total / 0.8 GB free`，`load average ≈ 21`（20 核），无 swap | 见 10.3 |

### 10.2 第一轮故障 1：`make install` 并行竞态（已修复）

`RUN_DIR=…/tiger-3.2.4-tiger-3.2.4-build-conan-20260929-192833-11889`（exit 1）：

```text
/bin/sh: can't create …/p/bin/./tigexp: No such file or directory
ginstall: cannot create regular file '…/p/etc/tiger/./tigerrc': No such file or directory
make: *** [Makefile:237: installbinaries] Error 1
make: *** Waiting for unfinished jobs....
```

根因：`Autotools.install()` 不会继承 `build()` 里传的 `-j1`，于是 `make install` 以
默认并行度（本机 20 核）执行；上游 `install: installdirs installbinaries installconfig
installmanpages` 依赖前置目标先建目录，并行下 `installdirs` 还没跑完
`installbinaries/installconfig` 就开始写文件。

修复：新增 `_make_args()`，`make` 与 `make install` 都传 `-j1`（`Autotools.install(args=…)`
会自行在最前面插入 `DESTDIR=`）。这也是通用问题——任何平台上并行 `make install` 都会踩。

### 10.3 第一轮故障 2：doc HTML 生成的 fork 耗尽（设备资源，非配方问题）

`RUN_DIR=…/tiger-3.2.4-tiger-3.2.4-build-conan-20260929-193307-28623`（exit 1）：

```text
tiger/3.2.4: RUN: make -j1 SHELL=/system/bin/sh
cd doc && make
sh ../util/doc2html
../util/convert2html[33]: can't fork - try again
../util/doc2html[50]: /storage/Users/currentUser/usr/local/bin/sed: Out of memory
make[1]: *** [Makefile:33: accounts.html] Error 1
```

进展：补丁应用、`./configure`（含 shebang 改写与 umask 放宽）、`c/` 5 个辅助程序编译、
`doc/` 前 25 个 txt 转换均已通过；失败点是 `util/doc2html`/`convert2html` 的逐行
`echo|grep`、`printf|sed` 造成的上万次 fork，在设备 fork 耗尽时中断。

同一时刻设备状态：`free` 仅剩 0.8 GB（25 GB 总量、无 swap），`load average 20.85/22.18/23.26`；
随后连 `sh script.sh`、`ps | sort | head` 都报 `sh: can't fork - try again`。
按避坑指南口径，这属于**真机资源状态 blocker**，不是 tiger 源码或配方缺陷：
19:28 那一轮（同一份源码、同样 `-j1`）doc 构建是完整通过的，19:33 之后设备才进入 fork 耗尽状态。

处置：本轮不为此改上游转换脚本；等设备恢复后重跑。若长期复现，再评估把
`util/convert2html` 的逐行 fork 改为单次 `sed`/`awk`（需对 35 个 txt 的产物做逐字节等价验证）。

### 10.4 最终轮：全链路通过（2026-09-30）

第一轮的 `-j1` 修复上机后，L4 报 `warn: dangerous functions in patches`；核对扫描规则
`grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/` 后确认是误报——命中的是补丁注释里
"LP64 tar**gets**" 的 `gets`。把措辞改为 "LP64 platforms"（仅注释，补丁语义不变）后重跑：

```text
RUN_DIR=…/tiger-3.2.4-tiger-3.2.4-build-conan-20260930-161758-52502
start 2026-09-30 16:17:59 +0800   end 16:21:35 +0800 (3m36s)   exit_code=0

tiger/3.2.4: RUN: make -j1 SHELL=/system/bin/sh
tiger/3.2.4: RUN: make install DESTDIR=… -j1 SHELL=/system/bin/sh    # 第一轮修复生效
tiger/3.2.4 (test package): RUN: "/system/bin/sh" …/test_tiger.sh <pkg>
PASS ×11 → All 11 assertions passed.

L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=pass: getpermit/md5/realpath/snefru/testsuid --version OK
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
L1e: Negative test confirmed — test genuinely depends on tiger
Build Summary: Total 1 / Success 1 / Failed 0
```

真机侧关键实测（`<pkg>` = conan 包目录）：

| 项 | 结果 |
|----|------|
| `bin/` | `tiger` `tigercron` `tigexp`（可执行） |
| `share/tiger/bin/` | `getpermit` `md5` `realpath` `snefru` `testsuid` |
| 安装布局 | `share/tiger/{config,initdefs,syslist,scripts,systems,util,doc,html,check.d}` + `etc/tiger/{tigerrc,cronrc}` + `var/tiger/{run,log}` + `licenses/COPYING` |
| `bin/tiger` 首行 | `#!/system/bin/sh`（E165 改写生效） |
| `share/tiger/bin/md5 -x` | 7/7 RFC 1321 向量正确（补丁 0001 在 aarch64 真机生效） |
| `printf '123456789\n' \| snefru` | `4ca72639 e40e9ab9 c0c3f523 c4449b39 …`（与 `c/snefru.c` 自带向量一致） |
| `TIGERHOMEDIR=… tigexp init001e` | 输出 `doc/config.txt` 中 `%init001e` 正文（补丁 0002 生效） |
| `ci-metadata.json` | L0/L1/L2/L4/L5 = pass/pass/pass/pass/pass |

结论：`tiger/3.2.4` 在 HarmonyOS aarch64 上**构建、安装、打包、命令入口与辅助工具全部验证通过**；
受限项仍为第 8 节列出的「检查流程平台配置」（需后续单独处理，不与本 PR 混做）。

### 10.5 真机环境备注（供后续会话复用）

- 仓库 `ci/conan/profiles/ohos-aarch64` 指向 `/data/service/hnp/bin/{clang,clang++,bash}`，**本机不存在**；
  设备实际可用的是 `CONAN_PROFILE=ohos-aarch64-localdevice`
  （`/storage/Users/currentUser/usr/local/bin/clang`，自带 sysroot/lld/code-sign wrapper）。
- 本机 `/bin -> /system/bin`（`/bin/sh` 存在），`install` 解析到 `$HOME/usr/local/bin/ginstall`。
- `load average` 长期 ≈ 20（20 核），不能用它判断忙闲；真机资源偶发在 HiShell cgroup 内枯竭，
  表现为 `sh: can't fork - try again` / `/bin/sh: Out of memory`，此时任何命令（含 `rm`）都无法执行。
- 全局锁 `$HOME/ohos-test-locks/device-global.lock`：并发时 runner 返回 **75 = 锁忙**，
  错峰重试即可（本次 16:16:59 一次 75，16:17:59 重试成功）。
- 隔离 job 复用：`$HOME/ohos-users/tiger/tiger-3.2.4-build/{env.sh,run-tiger.sh,conan-home,repo}`。


## 9. 下一步：真机 / shadow CI 命令

```sh
# 0) 真机环境（隔离 job 由 runner 分配 RUN_DIR）
export TMPDIR="$RUN_DIR/tmp"; export TMPPREFIX="$RUN_DIR/tmp/zsh"

# 1) 单包构建 + test_package（使用本机可用的 CONAN_PROFILE）
cd <repo>/archives/t/tiger/3.2.4
CONAN_PROFILE=ohos-aarch64-localdevice conan create . --user=ohpcd --channel=stable \
  -pr:h=ohos-aarch64-localdevice -pr:b=ohos-aarch64-localdevice --build=missing

# 2) shadow CI 单包门禁
CI_PACKAGES="archives/t/tiger/3.2.4" zsh ci/conan/build_and_test.sh

# 3) 首轮需要重点确认的现场信息
command -v install ginstall sh awk sed grep ls basename   # install 来源 / 工具可用性
ls -l /system/bin/sh /bin/sh                              # E165 前提
ls -l <pkg>/bin <pkg>/share/tiger/bin                     # 执行位是否保留（E087）
head -1 <pkg>/bin/tiger                                   # shebang 是否为 /system/bin/sh
<...>/share/tiger/bin/md5 -x                              # 补丁 0001 在真机上的实测
```

后续（下一个 PR / 版本后缀）建议按此顺序推进，且不与本 PR 混做：

1. 为 OHOS 增加平台配置：新增 `systems/OHOS/config`，或在
   `util/gethostinfo`、`syslist`、`systems/*/config` 的 `findcmd()` 中统一追加
   `/system/bin`（并处理 `config` 末尾写死的 `PATH=/sbin:/usr/sbin:/bin:/usr/bin`）。
2. 处理 `config` 里的 `/bin/cat` 与 `version.h` 安装，使 `tiger -v` 显示真实版本。
3. 若真机确认 `/bin` 不存在且 `install`/`ginstall` 都缺失，再评估是否需要
   为 `AC_PROG_INSTALL` 增加 shim（当前依赖上游自带 `install.sh` 回退）。
