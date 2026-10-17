# mpdas 0.4.5 适配笔记（HarmonyOS PC / B 机真机）

## 编译环境
- 构建系统: makefile（上游只有 Makefile，无 configure / 无自动工具）
- 语言: C++（8 个 `.cpp` + 8 个头文件；`compiler.cppstd=17`、`libc++`）
- 编译器: `/data/service/hnp/bin/clang++`（取自 profile 的
  `tools.build:compiler_executables={'c': '/data/service/hnp/bin/clang', 'cpp': '/data/service/hnp/bin/clang++'}`，R33）
- 构建机: B 机（HarmonyOS aarch64，os.version=6.0），worktree `~/qzy/主理-32-mpdas-0.4.5`
- CONAN_HOME: `~/tmp/ch/home-mpdas`
- 状态: built（`conan create` rc=0，test_package 5/5 PASS，见 `reports/create-r2.log`）

## 编译步骤

1. `get()` 解包 Debian pristine `.orig.tar.gz`（`strip_root=True`）；
2. `apply_conandata_patches()` 打 `0001-makefile-dependency-flags.patch`；
3. `make -j1 CXX=<conf cpp> DEPS_CFLAGS=<依赖 -I> DEPS_LIBS=<依赖 -L/-Wl,-rpath/-l>`（cwd=source_folder，R9）；
4. `package()` 用 `copy()` 手工摆放 `bin/mpdas`、`man/man1/mpdas.1`、`conf/mpdasrc.example`。

## 依赖（W0 判据原文）

`bash ci/scripts/preflight_check.sh mpdas/0.4.5` → rc=0，日志第 8/9/15 行：

```
[OK] 已发布: libcurl/8.5.0
[OK] 已发布: libmpdclient/2.23
[OK] 所有依赖均已发布到制品仓，可以安全开始适配 mpdas/0.4.5
```

选型理由：
- `mpd.cpp:56` 只用 `mpd_connection_new/…`，属 libmpdclient；`audioscrobbler.cpp` 走 HTTPS，属 libcurl。上游 Makefile 的 `pkg-config` 名字就是 `libmpdclient libcurl`，与两个包的 `pkg_config_name` 属性一致。
- 仓内 libcurl 只有 `8.5.0` 一个版本目录，`archives/c/curl` 是另一条产品线（curl 命令行工具），不是库的 conan 引用名；`archives/l/libcurl/8.5.0` 才是被 7101 处 `self.requires("libcurl/8.5.0")` 使用的库包。

### ★ 推翻一条先验：`@ohpcd/stable` 后缀在本仓不可用（第一轮 create 真实失败）

任务书与 `templates/conanfile-makefile.py.tmpl` 注释都写「依赖一律 `@ohpcd/stable`」（R27）。实测：

```
create-r1.log:63  ERROR: Package 'libmpdclient/2.23@ohpcd/stable' not resolved:
                  Unable to find 'libmpdclient/2.23@ohpcd/stable' in remotes.
                  Required by 'mpdas/0.4.5@ohpcd/stable'
```

反证与普查（同一 CONAN_HOME、同一 remote）：
- `conan graph info --requires=libmpdclient/2.23 -r ohpcd --build=never` → 正常出图；
- `conan graph info --requires=libcurl/8.5.0 -r ohpcd --build=never` → 正常出图；
- 仓内写法统计：`self.requires("...@ohpcd/stable")` **5** 处，plain `name/version` **7101** 处。

⇒ 本配方改用 plain `libmpdclient/2.23` / `libcurl/8.5.0`，第二轮 create rc=0。

### ★ 框架侧假绿灯披露（只披露，不改判据）

`ci/scripts/preflight_check.sh:127` 用 `conan download "$dep" -r ohpcd --only-recipe` 判发布态，
但它传给 conan 的 `dep` 串已把 user/channel 剥掉（日志第 8/9 行印的就是剥后形态
`已发布: libcurl/8.5.0`），因此**配方里写 `@ohpcd/stable` 时 W0 照样报 `[OK] 已发布`**，
真正的解析失败只在 `conan create` 阶段暴露。本包第一轮就是被这一层放过来的。
另：`conan download … --only-recipe -r ohpcd` 在本机对本包一律报
`ERROR: error:system acceleration policy not enabled.`（已发布的 `libjpeg-turbo/3.2.0` 同样报），
不具判别力；`-f` 在 conan 2.29.1 是用法错误。以上均不改判据，仅披露。

## 源码 URL 与 PF7 的判定（2026-09-25 第二轮：换源为上游官方件）

上一轮把取源定在 Debian 权威存档的 pristine `.orig`，并因两端字节不等而选择「维持 + 披露」。
本轮按棒次要求先把事实测清楚再决定，**测完判定为「可换」⇒ 已换源并全套重跑门禁**。
换源不是顺手一换：224 字节的差必须先定位，否则补丁可能打不上、或换进去的不是同一份发布件。
以下全部实测在 B 机真机完成，原始日志 `~/tmp/uc2/z32-mpdas-srcrep/out0.txt`、`out1.txt`（不进仓）。

### 两端取回实测（同一版本 0.4.5，两份都现场重下，未拿台账数字代替）

| 端 | URL | HTTP | 字节 | sha256 | tar 条目 |
|---|---|---|---|---|---|
| 上游官方 | `https://50hz.ws/mpdas/mpdas-0.4.5.tar.gz` | 200 OK；`Content-Length: 19108`；`Last-Modified: Thu, 05 Dec 2024 18:18:35 GMT` | 19108 | `c9103d7b897e76cd11a669e1c062d74cb73574efc7ba87de3b04304464e8a9ca` | 25 |
| Debian 存档 | `https://deb.debian.org/debian/pool/main/m/mpdas/mpdas_0.4.5.orig.tar.gz` | 200 OK；`Content-Length: 18884`；`Last-Modified: Tue, 27 Nov 2018 15:40:04 GMT` | 18884 | `b52ac99a66bf54318fc98fe09ba81f527906e28e93fba616f905f4c05b0296e1` | 24 |

两次 `curl` 下载 rc 均为 0；两份都是合法 gzip（magic `1f 8b 08 00`）；`tar tvzf` rc 均 0；
`tar xzf` 解包 rc 均 0；解包后顶层目录名同为 `mpdas-0.4.5`，与配方 `strip_root=True` 的期望一致。
（附带观察：官方件的 gzip 头 MTIME 字段为 0、Debian 件为 `70 f5 fc 5b` ⇒ 官方站这份是 2024-12-05
被作者重新打包过一次的同版本发布件，但**内容仍是 2017-11-12 21:27 那一批文件**，见下。）

### 差异定位（判「能不能换」的决定性一步）

- `diff -r --brief 官方树 Debian树` 只输出一行：`Only in <官方树>: .gitignore`（rc=1 只由这条存在性差异造成）。
- 逐文件 `sha256sum` 对撞（官方 24 个常规文件、Debian 23 个，`sort -k2` 后 `diff`）：
  唯一差异 `1d0 > 7bc15a2320b345f273e1929b982b2ea2be6fa3069b751192df8ef2d3aea596c4  ./.gitignore`。
  即 **23 个共有文件字节全等、无一处内容差异、mtime 同为 2017-11-12 21:27**；
  `.gitignore` 242 字节，正文是 `*.o *.lo *.la *.so *.gch *.mod` 一类编译产物忽略表，不参与构建。
- 结论：224 字节之差 = `.gitignore` + gzip 头/压缩差异，**不是源码内容分叉**；
  Debian `.orig` 只是把 VCS 元数据文件从上游发布件里剥掉，源码本体与作者官方件完全一致
  ⇒ 「哪个才是上游正式发布件」有明确答案：作者官方站直链件；`.orig` 只是它的剥壳副本。

### 补丁试打（本包**不是零补丁**，换源后必须重新验证打得上）

`conandata.yml` 的 `patches:` 现值是一条：`patches/0001-makefile-dependency-flags.patch`
（`patch_type: portability`、`strip: 1`；patch 自身 sha256 `098f1597119e402b5b341a3183155fdc7ee112cbfc4e1144c6e50d9133c8fd1f`；
作用是把上游 `Makefile` 里用反引号内嵌的 `pkg-config --cflags/--libs libmpdclient libcurl` 参数化成可覆盖的 `DEPS_CFLAGS ?=` / `DEPS_LIBS ?=`）。

两份树的 `Makefile` sha256 相同：`9478056306d0da62db4c86dbf48d699d9f2fa984b5faaa228a968449afca7963`。逐条试打 rc：

| 树 | `patch -p1 --dry-run` | `patch -p1 -R --dry-run` | `git apply --check -p1` |
|---|---|---|---|
| 官方件 | rc=0（`patching Makefile`，无 fuzz/offset） | rc=1（`Hunk 1 FAILED 7/7` ⇒ 未打过的树反向必失败，符合预期） | rc=0 |
| Debian `.orig` | rc=0（同上） | rc=1（同上） | rc=0 |

另外在官方树的副本上**真打**一次：`rc_APPLY_UP=0`，打完 `Makefile` 第 8-12 行确实为
`DEPS_CFLAGS ?=` / `DEPS_LIBS ?=` / `CXXFLAGS += $(DEPS_CFLAGS)` 形态。
⇒ 补丁在官方件上与在 `.orig` 上逐字节等价地打得开，换源不引入「补丁失效」风险。

### 选型依据与红线自证

- 上游作者官方站 `https://50hz.ws/mpdas/` 的同版本 https 直链 = 一手权威源，且实测与 `.orig` 内容等价
  ⇒ 按 R39/PF7 口径改取官方直链，两条红从根上消除，而不是绕过它。
- 哈希改动 = 换源的必然结果，**两端字节/sha 都留了实测原值**（上表），未做任何"凑绿"式改写；
  换源前的旧值本身也是被 `conan create` 实际下载校验过的可用值。
- 未使用 `--no-preflight`；未改 `scripts/`、`ci/`、`templates/` 任何判据；未走 `file://`、
  未走任何镜像/代理域；`conandata.yml` 与版本级 `manifest.yaml` 内已不含被 PF7 扫的下游存档域名
  （下游件仅作为旁证留在 `README.md`/本节，`.md` 不在 PF7 扫描面内——上一轮 `README.md:9` 就带同一条 URL 而未被计入红）。
- 同版本上游 GitHub 镜像无与两枚 sha 同时吻合的 release tag 可作二次佐证，且 `http://` 本身过不了 R39 ⇒ 不引用。

### 对测试账与 rule4 同源数字的影响（不换口径，只核是否仍同源）

- `test_package/MANIFEST.yml` 的 `assertion_count: 5` 与 `test.sh` 里的 `PASS` 计数 **一律未动**。
- 上游 0 测试的六条自数中只有第 1 条的归档文件名从 `mpdas_0.4.5.orig.tar.gz` 改为 `mpdas-0.4.5.tar.gz`；
  对官方件的 `tar tvzf` 清单跑 `grep -ciE 'test|spec|check'` 实测仍为 0（见「换源后门禁复跑」）。
- 其余五条判据落在 `Makefile` 与包内目录结构上，`Makefile` 两端 sha256 相同 ⇒ 结论逐条照旧。
- 上一轮 5 条真机断言所在的探针树 `~/tmp/uc2/z32-mpdas/src/mpdas-0.4.5` 与本轮官方件 23 个共有文件
  字节全等 ⇒ 测试账同源不破；但因换源改了 recipe revision，旧 W3 件一律作废，按门禁全套重跑。


## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 第一轮 `conan create` 依赖解析失败 | ohpcd 制品以 plain `name/version` 发布，带 `@ohpcd/stable` 的引用查不到（create-r1.log:63） | requires 改 plain 形态；仓内 7101:5 的写法比证实这是本仓约定 |
| 2 | 上游 Makefile 用反引号硬调 `pkg-config --cflags/--libs libmpdclient libcurl` | 交叉构建环境里没人给这两个包生成 `.pc`（配方不跑 `PkgConfigDeps`），命令替换返回空 ⇒ 编译丢 `-I`、链接丢 `-l`，且 `LIBS` 是 `=` 直接赋值、命令行与环境量都盖不住 | 补丁 0001 把它参数化为 `DEPS_CFLAGS ?=` / `DEPS_LIBS ?=`（保留原 pkg-config 表达式为默认值，纯 Linux 上 `make` 照旧可用），配方从 `self.dependencies[...].cpp_info.aggregated_components()` 取真实 `-I/-L/-l/system_libs` 注入 |
| 3 | 不能在命令行覆盖 `CXXFLAGS` | Makefile 的 `CXXFLAGS += -DCONFDIR=… -DVERSION=…` 会被命令行赋值整体吃掉，而 `main.cpp` 无条件使用这两个宏（`printversion()`）⇒ 直接编译失败 | 只新增 `DEPS_CFLAGS`，让 Makefile 自己把 `-DCONFDIR/-DVERSION` 追加进 `CXXFLAGS`；实测 `-v` 输出 `Global config path is set to "/usr/local/etc/mpdasrc"` 证明两个宏都编进去了 |
| 4 | 上游 `install` 目标不可用 | 依赖 coreutils `install(1)`，OHOS 无（实测 `command -v install` 空，E174）；且写死 `${PREFIX}/bin`、`${MANPREFIX}` | 不走 `make install`，改由配方 `package()` 内 `copy()` 摆放（R16：产物仍出自 `conan create`，不手工打包） |
| 5 | HMDFS 并发 | make jobserver FIFO 不可靠（R9） | `make -j1` |
| 6 | 运行期找 `.so` | 依赖是 shared 包，测试阶段加载器要能找到 libmpdclient.so / libcurl.so | 链接期注入 `-Wl,-rpath,<依赖 libdir>`；实测已安装二进制在 conanrun 下直接跑通 5 条断言 |
| 7 | test.sh 里出现 `shell-init: error retrieving current directory: getcwd: …` / `job-working-directory: …` | HMDFS 上 bash 的 getcwd 限制（toybox/bash 噪声），**不影响判定**：5 条断言各自 rc 与 grep 全中，末行 `test mpdas 0.4.5: 5/5 checks PASS` | 只披露，不为此改脚本口径 |

## 能力面（守护进程型客户端，逐号探、分层归因）

探针 `~/tmp/uc2/z32-mpdas/probe/probe.c`（本机 `/data/service/hnp/bin/clang` 编译 rc=0，
运行 rc=0，日志 `~/tmp/uc2/z32-mpdas/probe-r1.log`），一律 `open()/connect()/bind()` 系读数，
不用 `stat()`/`ls` 定性：

| # | 调用 | 实测 | 归因 |
|---|------|------|------|
| P1 | `getaddrinfo("localhost","6600")` | `rc=0`，首个地址 `family=2(AF_INET) socktype=1(SOCK_STREAM)` | 名称+数字服务解析可用 |
| P2 | `getaddrinfo("localhost","mpd")` | `rc=-8` `Unrecognized service`（`EAI_NONNAME`） | **C 库内置服务名表缺 `mpd` 这一条**，并且本机**没有可补的服务名文件**：W4 r1 独立探针实测 `fopen("/etc/services")` → `NULL, errno=2 ENOENT`（该文件在本机不存在），而同一条探针里 `http`→`127.0.0.1:80`、`ssh`→`:22`、数字 `9`→`9` 全部 `rc=0` ⇒ 服务名解析本身可用、走的是 libc 内置表。⛔ 旧归因（把缺项记在 services 文件上）不成立，「补一个文件」这条处置路在本机根本不存在；这也不是网络能力被拦。mpdas 默认连数字端口 6600，不受影响 |
| P3 | `socket(AF_INET,SOCK_STREAM)` | `fd=4 errno=0` | TCP 套接字可创建 |
| P4 | `connect(127.0.0.1:6600)` | `rc=-1 errno=111 ECONNREFUSED (Connection refused)` | 本机没有 MPD server，**预期**；已安装二进制第 5 条断言印出同一句 `MPD connection error: Connection refused`，两条读数同源 |
| P5 | `socket(AF_UNIX,SOCK_STREAM)` | `fd=4 errno=0` | unix 套接字可创建 |
| P6 | `bind(<可写 HMDFS 目录>/mpdas-probe.sock)` | `FAIL errno=1 EPERM (Operation not permitted)` | 本机（B 机）实测复算成立：**可写目录里 bind 仍 EPERM**。**两条对照臂**（W4 r1 独立探针 `~/tmp/uc2/z32-mpdas-w4/probe.c`，读数 `~/tmp/uc2/z32-mpdas-w4/out/c3.txt` 段「C6 run」）把归因收窄：① 同探针 `bind(AF_INET 127.0.0.1:0)` rc=0 且 `listen()` rc=0 ⇒ 排除「`bind` 系统面整体被拦」；② 同一 HMDFS 可写目录里普通文件 `open(O_CREAT)` 成功 ⇒ 排除「该目录不可写」。故 EPERM 专属「在文件系统上创建 AF_UNIX 路径套接字」这一个动作。与 inputlirc 那台/那轮的读数同形，但**本包证据是这条本包自己的读数**，不引用别包结论 |
| P7 | `connect(<可写目录>/…-missing.sock)` | `rc=-1 errno=2 ENOENT` | 路径不存在（与 EACCES/EPERM 分列） |
| P8 | `bind(/tmp/mpdas-probe.sock)` | `FAIL errno=30 EROFS (Read-only file system)` | `/tmp` 只读，与 P6 是**两件不同的事** |
| P9 | `bind(抽象命名空间 @mpdas-abst-probe)` | `rc=0 ok` | 抽象命名空间可用 |

分层结论：
- **本包不需要 bind**：mpdas 是纯客户端，唯一可能的 AF_UNIX 用法是把 `host` 配成 MPD 的 socket **路径**（libmpdclient 对以 `/` 开头的 host 走 `AF_UNIX connect`）。本机既不能 `/tmp` 建（EROFS）也不能可写目录建（EPERM），因此「连到 MPD 的 unix socket」这条**未执行**——**证据是 P6/P8 的 EPERM/EROFS：造不出被连的 socket 文件**，⛔ 不得据此写「OHOS 不支持 unix socket 连 MPD」；抽象命名空间（P9）可用，但 MPD server 不在本机、无法用它做端到端验证。
- **`ECONNREFUSED`（P4）** = 没有 server，属环境事实，不是平台限制。
- **`ENOENT`（P7）** = 路径缺项，与 P6 的 EPERM 不同因。
- **无 `EACCES` / 无 `ENOSYS` / 无 SIGSYS**：本次 socket 相关调用面上没有观测到 seccomp 拦 syscall 的痕迹（观测到的 errno 只有 111/2/1/30），不外推。
- **scrobble（libcurl）这条输出面：未执行**。上游 `main()` 只有在 MPD 连上之后才 `AudioScrobbler->Handshake()`；本机无 MPD server ⇒ 该分支根本到不了，且它还需要外网 last.fm。按「既不写不可用、也不写已验证」的口径记：**libcurl 已链接、`.so` 已随 rpath 装入（`-l` 解析在链接期完成，链接 rc=0），但 HTTP scrobble 行为未验证**。
- **无 X / 无状态栏**：mpdas 只往 stdout 打印，不依赖 X；消费者（xmobar/polybar）不在本包范围。

## 测试账（rule4，三条同源）

上游测试：**0**（六形自数，全部跑在**未打补丁的 pristine 解包树** `~/tmp/uc2/z32-mpdas/src/mpdas-0.4.5`）：

```
R4_1_tar_name_test_count=0        # tar tzf …orig.tar.gz | grep -ciE 'test|spec|check'
R4_2_makefile_target_count=5      # 目标只有 all / .cpp.o / clean / install / uninstall
R4_3_TESTS_or_check=0             # 无 TESTS= 变量、无 check/test 目标
R4_4_ci_files=0                   # 包内无 .github/.gitlab/azure/travis
R4_5_corpus=0                     # 无 tests/ spec/ fixtures/ 语料目录（mpdasrc.example 是配置样例）
R4_6_selftest_in_src=0            # 源码内无 assert()/testSucceed/self_test 计数
```

适配后消费者断言：**5 条**，每条都真实执行**已安装**的 `mpdas` 二进制，且每次外部调用都套
`/usr/bin/timeout 30`（实测该路径存在：`/usr/bin/timeout -> ../../bin/toybox`），`rc=124` 判 FAIL：

| # | 断言 | 判据 |
|---|------|------|
| 1 | `mpdas -v` | rc=0 且输出含 `mpdas-0.4.5` |
| 2 | `mpdas -h` | rc=0 且输出含 `usage: mpdas [-h] [-v] [-c config]` |
| 3 | `mpdas -v` | rc=0 且输出含 `Global config path is set to`（证 `-DCONFDIR` 编进） |
| 4 | `mpdas -c nopasswd.cfg` | rc=1 且输出含 `AudioScrobbler username or password not set.` |
| 5 | `mpdas -c scrobble.cfg` | rc=1 且输出含 `Could not connect to MPD.`（证 libmpdclient 真被装载并跑到协议层） |

同源核对：`test_package/MANIFEST.yml` 的 `assertion_count: 5` = `test.sh` 内 `PASS` 计数 5 =
日志末行 `test mpdas 0.4.5: 5/5 checks PASS`（`reports/create-r2.log`）。
上游 0 → 适配后 5，合计 5 ≥ 上游静态合计 0。

## 路径 B 判定

**四范围同批扫描**（同一条命令、同一 worktree，命令原文与命中数）：

| 范围 | 命令 | 命中 |
|---|---|---|
| `knowledge/graph/*.kv` | `grep -lE "pkg.config" knowledge/graph/*.kv \| wc -l` | **23** 个文件 |
| `knowledge/graph/index.tsv` | `grep -icE "pkg.config" knowledge/graph/index.tsv` | **13** 行 |
| `knowledge/drafts/*.kv` | `ls knowledge/drafts/*.kv \| xargs grep -lE "pkg.config" \| wc -l` | **100** 个文件 |
| `archives/**/notes.md` | `grep -rlE "pkg.config" archives --include=notes.md \| wc -l` | **1084** 个文件（其中同时提到 Makefile 的 **394** 个） |

grep 命中 ≠ 语义命中。对本包机制（「原始 Makefile 用反引号硬调 pkg-config 取依赖标志，交叉环境没有 `.pc` ⇒ 参数化为可覆盖变量、由 Conan 依赖图注入 `-I/-L/-l`」）做四条件对照的邻近条目：

- **E158**（`knowledge/graph/E158.kv`，fbida 2.14）：机制=上游 GNUmakefile 的**个别目标漏了** pkg-config 标志，处置=`patch-gnu-makefile` **补上** `$(shell $(PKG_CONFIG) …)`；本包是上游**已经在调** pkg-config 但交叉环境取不到标志，处置方向相反（**摘掉** pkg-config、改由 Conan 传标志）。⇒ 同作用域（手写 Makefile）成立，**同机制/同根因/同处置面不成立**。
- **E468**（`knowledge/graph/E468.kv`）：机制=`PkgConfigDeps` 写了 `.pc` 但没扩 `PKG_CONFIG_PATH`，处置=在 `generate()` 里把 generators 目录追加进 `PKG_CONFIG_PATH`，作用域是 **autotools 的 `PKG_CHECK_MODULES` 探测期**。本包不跑 `PkgConfigDeps`、也没有探测期，构建期命令替换直接落空。⇒ 四条件不齐（根因层次不同、处置面不同、作用域不同）。
- **E480 / E533 / E538**（`knowledge/graph/E480.kv`、`E533.kv`、`E538.kv`）：分别是 X11 客户端库头文件用 `transitive_headers` 消费、libarchive/bsdtar 的 autotools+hmdfs 权限+依赖边界+测试分类、统一 C++17/libc++ profile 后 meson+pkgconfig 依赖图选项冲突——机制面都与本包不同。
- drafts 侧同族件（按文件名引用，那边 E 编号被复用）：`DRAFT-conan-shared-pkgconfig-requires-drop.kv`、`DRAFT-E572-removed-config-script-pkgconfig-migration.kv`、`DRAFT-cohomcalg-0.32-makefile-gxx-override.kv`、`DRAFT-E628-rtklib-handwritten-makefile-multi-app-adaptation.kv` —— 分别是「shared 依赖的 pkgconfig requires 收敛」「删掉 config 脚本改走 pc」「Makefile 里 g++ 需覆盖 CXX」「手写 Makefile 多目标应用」，都只与本包**局部形似**，无一覆盖「反引号 pkg-config → 参数化 + Conan 依赖图注入」这条完整机制。
- **`knowledge/drafts/E552-draft-2E8C.kv`**（W4 r1 补枚举：池内语义最近的一枚，按文件名引用、不占知识位、不建 Issue）：其 `root_cause` 原文含「Makefile FLAGS 内嵌的反引号 pkg-config --cflags --libs libgtop-2.0 在 make 执行期解析不到依赖」，`affected_scope` 原文（节选）「所有 Makefile 型且依赖通过 pkg-config 发现的 C 库…」⇒ 与本包**同机制（手写 Makefile 里的反引号命令替换在 make 执行期取不到依赖标志）、同根因（该环境里没有可被 pkg-config 消费的 `.pc`）、同作用域（Makefile 型 + pkg-config 发现的 C 库）三条成立，只有处置面不同**：E552 是补 `.pc` + 把 `PKG_CONFIG_PATH` 指向 generators 目录（让 pkg-config 继续可用），本包是**摘掉** pkg-config、改由 Conan 依赖图 `cpp_info` 注入 `-I/-L/-l`。按「处置面差即降档」口径 ⇒ **仍判 `none`**。本行补进来的目的是让读者看出这是有意降档，而不是漏扫。
- **`knowledge/drafts/DRAFT-pngnq-1.1-conan-libpng-config-wrapper.kv`**（W4 r1 补枚举：第二近，同样按文件名引用、不建 Issue）：机制按判决件 `issues[W4-R1-03].finding` 的表述 = 「`Makefile.am` 反引号调 `libpng-config` ⇒ 配方内生成 wrapper」⇒ 与本包**同机制（构建期命令替换取依赖标志）、同根因（被调用的那个发现工具在本环境给不出可用值）、同作用域（make/.am 型工程）成立，处置面不同**（它生成一个 wrapper 脚本冒充该 config 工具并前置 PATH，本包把标志参数化、由依赖图注入）⇒ 同样**降档为 `none`**。

结论：**B 判定 = none，不建知识条目、不建 Issue**。理由（三条独立成立）：
1. 撞上的都是**通用交叉编译/Conan 依赖标志注入**做法，不是 OHOS 独有能力面；本包真机上没有观测到 OHOS 特有失败（编译链接一次通过、5 条断言一次全过）；
2. 能力面读数（EPERM/EROFS/ENOENT/ECONNREFUSED 分层）虽是本机实测，但属**探针清单**已有的同源形态（客户端不因 `bind` 被拦而失能），不构成新机制；
3. 四条件对照下 23 个 graph 命中里没有任何一条同时满足同机制/同根因/同处置面/同作用域。

- **适配路径**: A（标准 Conan 配方 + 1 个可移植性补丁，未走路径 B/C）
- **使用知识库**: 是（`knowledge/graph/*.kv` + `index.tsv` 四范围查重；引用 E158、E468、E480 做四条件对照）
- **知识库扩展**: 无（B 判定 = none，未新增条目，不落 `knowledge/drafts/`）
- **关联 Issue**: 不适用（路径 B 判定 = none）

## 依赖版本

| 依赖 | 引用 | 用途 |
|---|---|---|
| libmpdclient | `libmpdclient/2.23`（plain，ohpcd 已发布） | MPD 协议 |
| libcurl | `libcurl/8.5.0`（plain，ohpcd 已发布） | scrobble HTTPS |

## 验证结果

```bash
$ conan create archives/m/mpdas/0.4.5 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
CREATE_RC=0        # reports/create-r2.log，末行 SLOT_DONE:ok MemAvailable=6483MB
...
test mpdas 0.4.5: 5/5 checks PASS

$ python3 scripts/ohc-run.py conan-verify mpdas 0.4.5
VERIFY_RC=0        # G1 PASS / G2 PASS / G3 PASS / G4 见 reports/verify-r1.log
```

## 注意事项

- 编译期内置的全局配置路径是 `/usr/local/etc/mpdasrc`（上游 `CONFIG ?= $(PREFIX)/etc` 默认值）。
  OHOS 上该目录不存在也不可写，`-c` 与 `~/.mpdasrc` / `$XDG_CONFIG_HOME/mpdasrc` 才是可用入口；
  配方**没有**擅自改写这个路径（不编造 OHOS 专有路径），只在此披露。
- `mpdas` 连不上 MPD 时会每 10 秒打印 `Reconnecting in 10 seconds.` 并常驻（`MPD->Update()` 循环），
  所以 test.sh 只在「未配置凭据 ⇒ 早退」与「配置凭据 ⇒ 连接失败即退」两条不会常驻的路径上断言；
  若将来要在有 MPD 的环境跑 test_package，第 5 条断言的预期要按现场改写（本机没有 MPD 是事实前提）。
- `daemon()` 分支（`-d`）与 `runas` 切用户分支（`getpwnam`/`setuid`）未测试：前者会常驻后台、
  后者需要 root，均属**未执行**，不写结论。
---

## 本地门禁读数（B 机真机，2026-09-25，全部日志在设备 `~/tmp/uc2/z32-mpdas/`）

| 门禁 | 命令 | 判决 | 一手证据 |
|---|---|---|---|
| W0 依赖发布态 | `bash ci/scripts/preflight_check.sh mpdas/0.4.5` | rc=0；第 8/9 行 `[OK] 已发布: libcurl/8.5.0` / `[OK] 已发布: libmpdclient/2.23`，第 15 行总结 | `preflight-w0-r1.log` 883B，md5 83d6a0fa… |
| `conan create` 第一轮 | 同上 + `--user=ohpcd --channel=stable` | **rc=2 失败**：`create-r1.log:63 ERROR: Package 'libmpdclient/2.23@ohpcd/stable' not resolved` | `create-r1.log` 2691B，md5 c4f9192a… |
| `conan create` 第二轮（requires 改 plain 后） | 同命令 | **rc=0**；`create-r2.log:137 Created package revision 16cc18106852812b8dd438f4987d949a`；test_package 末行 `test mpdas 0.4.5: 5/5 checks PASS`；末行 `SLOT_DONE:ok MemAvailable=6483MB` | `create-r2.log` 15082B，mtime 05:44，md5 572b6524… |
| conan-verify（G0–G4，**不是 W3**） | `python3 scripts/ohc-run.py conan-verify mpdas 0.4.5` | rc=0；`verify-r1.log:6 G1: PASS`、`:10 G2: PASS`、`:12 G3: PASS`、`:46 ✅ 配方验证通过: mpdas 0.4.5` | `verify-r1.log` 1280B，md5 738bc114… |
| **W3**（finish 的 step5 `build_and_test.sh`） | `python3 scripts/ohc-run.py finish mpdas 0.4.5 built` | rc=0；`finish-r1.log:55 ✅ W3 本地 CI 模拟通过`；W3 日志判决标记数 **56**（`grep -cE "^\[step\]|RESULT="`），`w3-local-ci.log:23 G0_RESULT=pass`、`:66 KC_RESULT=pass`、`:93 JC_RESULT=pass`、`:278 L0_RESULT=pass`、`:279 L1_RESULT=pass`、`:281 L4_RESULT=pass`、`:282 L2_RESULT=skip`、`:285… :291 [step] All packages built and tested successfully ✅`；5 条断言在 W3 内重跑（`:251-262`） | `archives/m/mpdas/0.4.5/reports/w3-local-ci.log` 16435B，mtime 05:45（本轮，其余日志 05:44），md5 `0fca5006…` 与相邻 6 份日志全不同；`.ci-result.json` 的 `integrity_hash=019c9b33c5f6a82c` 复算 `sha256("2026-09-25T05:45:43.798193:mpdas:0.4.5:0")[:16]` **一致**，`archive_dir` 指本 worktree |
| W5 图谱 | `python3 scripts/ohc-run.py graph validate` | rc=0（540 条覆盖统计打印） | `graph-validate-r1.log` |
| PF1–PF9 静态闸 | `python3 scripts/ohc/preflight.py . origin/main HEAD` | **rc=1**，两条 ✗（见下），PF1–PF6/PF8 无告警 | `pf-r1.log` 735B |

测试账同源复核（W3 与 create 两条独立日志同一数字）：`MANIFEST.yml assertion_count: 5` =
`test.sh` 的 `PASS` 计数 5 = `create-r2.log` 与 `w3-local-ci.log` 末行 `5/5 checks PASS`。

## 框架/存量红披露（只披露，未改任何判据、未改 scripts/ci/templates）

1. **PF7 源 URL（上一轮两条红 ⇒ 本轮已按实测换源消除，非降级、非改判据）**：
   上一轮 `pf-r1.log` 原文两条 `✗ PF7 源URL红(R39): archives/m/mpdas/0.4.5/conandata.yml:2 Debian 下游重打包源……`
   与 `✗ PF7 源URL红(R39): archives/m/mpdas/0.4.5/manifest.yaml:10 Debian 下游重打包源……`，
   判由是 `sources.url` 取了 Debian 存档域名。本轮把上游官方站同版本发布件与 `.orig`
   做了真机下载 + 逐文件 sha256 对撞 + 补丁正反向 dry-run 实测（全文见 §「源码 URL 与 PF7 的判定」），
   确认二者 23 个共有文件字节全等、官方件只多一个 `.gitignore`、补丁在两边都 `rc=0` 打得上，
   遂把 `conandata.yml` 与版本级 `manifest.yaml` 的取源换成 `https://50hz.ws/mpdas/mpdas-0.4.5.tar.gz`。
   **换源后重跑 `scripts/ohc/preflight.py` 的 PF7 命中数 = 0**（新判决行原文与行号见 §「换源后门禁复跑」与台账）。
2. **PF9 与软件级三件套互斥**（`pf-r1.log` 原文）：
   `✗ PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）——CI 将报 No packages to build（490 例）: archives/m/mpdas/README.md, archives/m/mpdas/commands.json, archives/m/mpdas/manifest.yaml`
   即交付清单要求的**软件级** `README.md / manifest.yaml / commands.json` 与 PF9「每个变更文件必须在版本目录下」直接冲突，
   本包两套都按规范写了（G1 三件套判 PASS）。⇒ 属框架侧互斥，⛔ 未删三件套凑绿，交主窗裁决。
3. **W0 判据会剥 user/channel**（`ci/scripts/preflight_check.sh:127`）⇒ 配方写 `@ohpcd/stable` 时仍报 `[OK] 已发布`，
   真实解析失败只在 `conan create` 暴露（本包第一轮即为此）。假绿灯，未改脚本。
4. `finish-r1.log:23` `❌ G0: 找不到原始 tarball`（conan-verify 段的 G0 预构建风险评估）与
   `w3-local-ci.log:23` `G0_RESULT=pass`（W3 step 的 G0）**同名不同层**，两处口径不一致；均照原样带出。
5. `finish-r1.log:84` `❌ 知识图谱完整性检查发现 1 类问题` 与 `:87` `✅ ✅ 知识完整性检查通过` 并存
   （同一步骤两行判决相反，列的是 DRAFT 池件计数，未点名本包）。
6. `finish-r1.log:88` `⚠️ gen_summary 失败: 'str' object has no attribute 'append'`（step8 框架自身异常）。
7. `finish-r1.log:94-96` step10 判 `test-report.md` / `packaging/` / `.staging-verified` 「需创建」——**本包三项均未创建**：
   `.staging-verified` 一旦落盘就是 `junk_check.sh` 的 JC1/JC5 违规件（与「不得留标记件」互斥，
   本轮 JC_RESULT=pass 正是建立在没有任何标记件的前提上）；`reports/` 被 `.gitignore:96` 忽略，
   `test-report.md` 与全部 `reports/*.log` 都进不了 PR（交付清单里的 `reports/*.log` 只存在于设备磁盘）。
   ⇒ 只披露，不自作创建/删除，交主窗裁决。
8. `w3-local-ci.log:280 L2_RESULT=skip: mpdas version/help failed`：框架 L2 只试长选项，
   而 mpdas 上游 `main.cpp` 只做 `-h/-v/-c/-d` 的**前缀**匹配、无 `--version`/`--help` ⇒ skip 属预期，
   **不是失败也不是可执行证据**；可执行证据是 L1（test_package 真跑）与上面 5 条 PASS 读数。
9. `test.sh` 输出里的 `shell-init: error retrieving current directory: getcwd: …` 是 HMDFS 上 bash 的 getcwd 噪声，
   不影响各断言 rc 与 grep 判定（同轮 5/5 PASS）。
10. `conan-verify` 尾行提示「可标记 status: published」——**本包 manifest 仍写 `built`**：
    合入与发布态由 CI/审查决定，本地无权升 published。
---

**编译结束**: 2026-09-25 06:07
**最终状态**: built

## 换源后门禁复跑（2026-09-25 第二轮，B 机真机；换源改了 recipe revision ⇒ 旧 W3 件一律作废）

台账全文在设备证据目录 ~/tmp/uc2/z32-mpdas-srcrep/GATES.md（含每条判决行原文、文件:行号、字节/mtime 与复算过程）。

| 门禁 | 命令 | rc | 判决行 |
|---|---|---|---|
| W0 | bash ci/scripts/preflight_check.sh mpdas/0.4.5 | 0 | g-w0.log:8 「[OK] 已发布: libcurl/8.5.0」、:9 「[OK] 已发布: libmpdclient/2.23」、:15 「[OK] 所有依赖都已发布到官方仓，可以继续发起集成 mpdas/0.4.5」（是真发布态行，不是 Skip recipe already in cache 的假成功） |
| recipe-search | python3 scripts/ohc-run.py recipe-search mpdas | 0 | 命中 archives/m/mpdas/0.4.5/conanfile.py，依赖 libcurl、libmpdclient |
| conan-verify（G0–G4） | python3 scripts/ohc-run.py conan-verify mpdas 0.4.5 | 0 | g-verify.log:9 G1 PASS、:13 G2 PASS、:15 G3 PASS、G4 见 （三一致：文字 PASS + Verdict + rc） |
| **W3**（finish step5） | python3 scripts/ohc-run.py finish mpdas 0.4.5 built | 外层 0 | g-finish.log:57 「✅ W3 本地 CI 模拟通过」；reports/w3-local-ci.log 非锚定标记数 56，字节/mtime 16383 2026-09-25 06:07 archives/m/mpdas/0.4.5/reports/w3-local-ci.log；.ci-result.json exit_code=0、calc=875be0a095850c26 stored=875be0a095850c26 MATCH、log_sha256 MATCH |
| W5 graph | python3 scripts/ohc-run.py graph validate | 0 | 540 条边回填（fallback 376/540、principles 158/540），存量告警，不拦 |
| PF1–PF9 | python3 scripts/ohc/preflight.py . origin/main HEAD | 1 | **PF7 命中数 = 0**（换源前 2）；✗ 共 1 条 = 仅 PF9 分支/路径红（软件级 README.md/commands.json/manifest.yaml 与「变更必须在版本号目录下」互相矛盾，CI 报 No packages to build 已 490 例的存量框架矛盾，非本包引入，✗ 集合未扩大） |

未过项与不写成通过的部分（与上一轮同源，逐条留证）：

- **finish Step6「档案检查」失败**：g-finish.log:58 是该步骤标题行、:117 是失败标记，统计为  / 缺失项:2；
  它是知识整理与档案件完备性面（紧随的 EXIT_REASON 为 finish_success、EXIT_CODE 0 表示知识整理已完成），
  不改配方内容；W3 在其上一步 Step5 且已判通过 ⇒ 交付门禁成立，Step6 留作未过项披露，未绕过、未降级判据。
- **step5b / step8** 本轮仍未过（全仓存量矛盾），照上表口径披露，不记为通过。
- 知识库索引完整性检查「发现 1 类问题」与「检查通过」在同一轮并存（框架自身矛盾），本轮未据此降级。
- L2_RESULT=skip（w3-local-ci.log:280）：框架 L2 只试长选项而 mdas 上游只有 -h/-v/-c/-d 短选项前缀 ⇒ skip 属预期，
  既非失败也非可执行证据；可执行证据是 L0/L1 与 test_package 的 5/5 PASS（:278、:279）。
- gen_summary 的 str object has no attribute append（step8 框架自身异常）本轮仍存在于日志中，未处理（不许改 scripts/ci）。

测试账同源复核（数字未动，只核换源是否破坏同源）：
本轮对官方件 tar tvzf 清单跑 grep -ciE 'test|spec|check' = 0，
对 Makefile 跑 grep -cE '^[a-z_.][a-z_. ]*:' = 5（两树 Makefile sha256 相同），
test_package/MANIFEST.yml 的 assertion_count: 5 与 test.sh 的 PASS 计数 5 一律未改；
换源后 W3 内重跑的 5 条断言仍为 5/5 PASS（reports/w3-local-ci.log:279）。

时序事实：本轮先建提交再跑 finish（避免 junk_check 拿到空 diff 退化成 full 模式数全仓）；
finish 未把 conandata.yml 改写成镜像数组形态（其工作树脏态只有框架自写的「编辑终态/最终状态」尾块），
故无需按 HEAD 还原哈希；镜像/file 字面量计数为 0（见上）。

## W4 r1 三条 P2 的文档整改（B 机，2026-09-25；纯文档，不触 recipe 导出输入）

判决件已 `git add -f` 入库到 `archives/m/mpdas/0.4.5/reports/audit-result.json`（31980 字节，sha256 `84a3a32378cbf5354c754a2f7e95f6518954cc9df45ef037f6c09339835b132f`，双端字节一致）。其 `verdict_detail` 原文：「所有 P2/P3 均为对外文本与举证完整性问题，不在构建输入面上，不阻塞建 PR，但建议先补一枚只动文档的整改提交。」⇒ 本轮只动本包 `README.md` 与本文件：

| 项 | 落点 | 改法 |
|---|---|---|
| W4-R1-01 | 版本级 `README.md:15`，并在 `:24` 新增一句 | 依赖行改成 plain name/version 形态 + 「`@ohpcd/stable` 实测不可解析」并指向本节 :33-48；把构建命令里的 `--user=ohpcd --channel=stable`（给 mpdas 自己的 user/channel，合法）与依赖引用形态分开表述 |
| W4-R1-02 | 本节 :149、:153（行内改写，行数不变） | P2 行归因改为「libc 内置服务名表缺 `mpd` 条目 + 本机 `/etc/services` 不存在（`fopen` ENOENT）」并附 `http`/`ssh`/数字三条对照臂；P6 行补 `AF_INET bind+listen rc=0` 与同目录普通文件可写两条对照臂 ⇒ EPERM 收窄到「AF_UNIX 路径套接字创建」 |
| W4-R1-03 | 本节 §路径 B 四条件对照新增 2 行（现 :211-:212） | 补枚举 `knowledge/drafts/E552-draft-2E8C.kv` 与 `knowledge/drafts/DRAFT-pngnq-1.1-conan-libpng-config-wrapper.kv`：同机制/同根因/同作用域成立、处置面不同 ⇒ 仍判 `none`；按文件名引用、不占知识位、不建 Issue |

⚠ 行号影响：新增两行 ⇒ 本节 :210 之后的行号整体 **+2**（判决件 `r40_ruling` 与 `verified_green` 内引的 `notes:250-251` 是整改前行号，整改后为 :252-:253）；:210 之前（含 :33-48、:149、:153、:163）不变。

本轮**未**重跑 `conan create` / `finish`：recipe 导出输入只有 `conandata.yml`、`conanfile.py`、`patches/*.patch`（判决件 `verified_green[C8_门禁复跑为真]` 的 HEAD 绑定判定同此口径：「notes.md 不参与 recipe revision」），`README.md` 与本文件都不在其内 ⇒ W3/verify 读数仍绑 `c99aae4f65`。
9 条 P3（`W4-R1-04`…`W4-R1-12`）本轮未改：`W4-R1-05` 的落点是 `test_package/MANIFEST.yml`（测试件，改它会前移功能 head、使已出具的 r1 判决失效）；`W4-R1-12` 是 `archives/m/mpdas/commands.json` 的 `binary` 外观字段（判决件自证 L0k 不读该字段、并写明"本轮不建议单独动 HEAD"）；其余 7 条确属纯文档可改项，本棒只获授权改三条 P2 ⇒ 未越权改，逐条理由与改法登记在 PR 正文「W4 独立审计判决与遗留项」小节，留待下一枚整改提交整批落实（那会前移 HEAD 并触发 r2 复审）。
