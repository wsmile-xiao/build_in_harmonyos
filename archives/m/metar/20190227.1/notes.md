# metar 20190227.1 适配笔记（HarmonyOS PC / aarch64）

> 执行窗口：主理-75（子代理执行棒 2）· 构建主机 B 机
> worktree：`~/qzy/主理-75-metar-20190227.1`，分支 `feat/metar-20190227.1`，基线 `48d9cee684`
> 设备侧证据目录：`~/tmp/uc2/z75-metar/`（日志逐条见第八节）
> CONAN_HOME：`~/tmp/ch/home-metar`（配置层复制自 `~/tmp/ch/home-B-cwalk`，不含 `p/` 缓存）

## 一、概况

| 项目 | 值 |
|------|-----|
| 软件 | metar —— 航空气象 METAR 报文取数 + 解码 CLI |
| 版本 | 20190227.1（由 `VERSION.m4` 的 `m4_define([METAR_VERSION],[20190227.1])` 定义；`configure` 脚本头仍写着 20061030.1，那是 autoconf 生成时的旧 `AC_INIT` 残留，不代表版本） |
| 构建系统 | autotools（tarball 自带 **autoconf 2.59** 预生成 `configure` + automake 1.8 的 `Makefile.in`） |
| 源件 | `metar_20190227.1.orig.tar.xz`，31 个文件，sha256 `046d3f99c2ba53af910f4598173353c25333f1172693a9fe60fe8c1a4b4ff24c`（设备实测 GET 200 + `sha256sum` 一致） |
| 必需依赖 | libcurl 一枚（`configure.ac`: `AC_CHECK_LIB([curl],[curl_easy_init])`，`ac_cv_lib_curl_curl_easy_init = no` 即 `AC_MSG_ERROR(Unable to find required library libcurl)`）→ `curl/8.15.0` |
| 源码 | `src/main.c`、`src/metar.c`、`src/metar.h`（`#include <curl/curl.h>`） |
| 产物 | `bin/metar`（可执行）+ `man/man1/metar.1` + `share/doc/metar/{AUTHORS,README,TODO,NEWS,THANKS}`，无库产物 |

## 二、五维测试账本（上游口径）

| 维度 | 值 | 依据 |
|------|-----|------|
| 上游测试静态总数 | **0** | 见下方逐条静态清点 |
| 可执行数 | 0 | 没有任何可运行的上游测试目标 |
| 实测通过数 | 0 | — |
| 跳过数 | 0 | 无"因平台原因跳过"的用例（压根没有用例） |
| 失败数 | 0 | — |

静态清点（命令与结果，逐条）：

1. `grep -n "TESTS\|^check:\|check-am:" Makefile.am src/Makefile.am doc/Makefile.am configure.ac`
   → **零命中**（三个 Makefile.am 分别只有 `SUBDIRS/doc_DATA/EXTRA_DIST`、
   `bin_PROGRAMS/metar_SOURCES/EXTRA_DIST`、`man_MANS/CLEANFILES/EXTRA_DIST` + pod2man 规则）。
2. Makefile.am 行数实测：顶层 16 行、`src/` 7 行、`doc/` 11 行，全文无测试目标。
3. `configure.ac` 全文 29 行：只有 `AC_PROG_CC/AC_HEADER_STDC/AC_TYPE_SIZE_T/AC_CHECK_LIB/
   AC_CHECK_HEADERS/AC_CHECK_FUNCS/AC_OUTPUT`，无 `AC_CONFIG_TESTDIR`、无 dejagnu/autotest、
   无测试类 `AC_CHECK_PROGS`。
4. tarball 31 个文件里没有 `test/`、`tests/`、`spec/` 目录，也没有 `.exp`/`t/` 之类测试件。
5. `make -n check`（探索构建树）→ `make: *** No rule to make target 'check'`（无该目标）。

⇒ 上游测试总数记 **0**，并按惯例在 `build()` 输出
`HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",...,"discovered":0,...}`
固定证据；`build()` 不调 `make check`（无意义且 CI L1c 会 grep 该字样）。

**功能验证由 test_package 承担，且不计入上游总数**（rule4：声明数 ≤ 实测数）：
`test_package/test.sh` 每通过一条断言自增计数器，结束时打印
`METAR_TEST_ASSERTIONS_PASSED=<N>`；本版本 N = 28（T1 usage 契约 3 条、T2 `-h` 2 条、
T3 EHAM 真实解码 12 条、T4 差分样本 9 条、T5 非法报文反向对照 2 条），与
`test_package/MANIFEST.yml` 的 `assertion_count` 同源。

## 三、三道墙：症状 / 根因 / 最小复现 / 失败方案 / 最终方案 / 适用边界

### 墙 1 —— libcurl 探测（E2186 同族：AC_CHECK_LIB 不注入 -I/-L）

- **首错原文**（裸 configure，未注入依赖 flags）：
  ```
  checking for curl_easy_init in -lcurl... no
  configure: error: Unable to find required library libcurl
  ```
  退出码 1（证据 `04-explore-configure.log` / `04a-configure-bare.log`）。
- **根因**：`AC_CHECK_LIB` 只做链接探测，配方若只生成 `AutotoolsToolchain`，
  依赖包的 `-I/-L` 根本不进环境；设备上默认库搜索路径也没有 libcurl，于是探测直接判 no。
  知识库 `DRAFT-E2186-autotools-deps-missing-dep-flags` 记的是同族的"探测假绿、make 才炸"
  形态（debfoster/`gc`），本包因"系统里连可链接的 libcurl 都没有"而表现为探测直接判红。
- **最小复现**：
  ```
  cd <srcdir> && ./configure --prefix=/tmp/p CC=clang          # → error: Unable to find required library libcurl
  cd <srcdir> && ./configure --prefix=/tmp/p CC=clang \
      CPPFLAGS="-I<curl>/include" LDFLAGS="-L<curl>/lib"        # → checking ... yes（rc=0）
  ```
  两条都已实跑（`04-explore-configure.log`、`05-explore-curl-and-runtime.log`）。
- **最终方案**：`generate()` 同时生成 `AutotoolsToolchain` 与 `AutotoolsDeps`
  （Conan 2 把"编译器/基础 flags"与"依赖的 -I/-L/-l"拆在两个 generator，
  只出前者时 `AC_CHECK_LIB` 与编译期都拿不到路径）。
- **适用边界**：所有 `AC_CHECK_LIB/AC_CHECK_HEADERS` 型 autotools 配方；纯
  `pkg-config` 型包另需 `PkgConfigDeps`。本包 configure.ac 不调用 `curl-config`
  （与 archives/d/dirb/2.22 不同），故**不需要**把依赖 bin 目录前置进 PATH。

### 墙 2 —— HMDFS 上 `umask 077` + `mktemp -d` 的 0700 临时目录不可写（E011/E114）

- **首错原文**（墙 1 修好之后，configure 走到 AC_OUTPUT 阶段）：
  ```
  config.status: creating ./config.status
  ./config.status[557]: can't create ./confstatJJ0wwV/subs.sed: Permission denied
  ./config.status[557]: can't create ./confstatJJ0wwV/subs.frag: Permission denied
  config.status: creating Makefile
  ./config.status[754]: can't create ./confstatJJ0wwV/out: Permission denied
  rm: ./confstatJJ0wwV/stdin: Permission denied
  mv: bad './confstatJJ0wwV/out': Permission denied
  ```
  现象是"configure 返回 0、`config.status: creating Makefile` 也逐条打印了，但
  Makefile 一个都没落盘"，紧接着 `make` 报
  `make: *** No targets specified and no makefile found. Stop.`（rc=2）。
  ⇒ **configure 的 rc=0 是假绿**，判墙必须看产物（证据 `05-explore-curl-and-runtime.log`）。
- **根因**：`configure`（autoconf 2.59 生成）写 config.status 的段落里用
  `tmp=\`(umask 077 && mktemp -d -q "./confstatXXXXXX")\``。HMDFS 上这样建出的目录
  模式是 `drwx--S---`（0700 + setgid），**即使 owner 就是当前 uid 也不可在其中建文件**；
  同一段落去掉 `umask 077` 后目录变成 `drwxr-s--x`，写入立即成功。这正是知识库
  **E011**（"HMDFS 的 UID 映射使 0700 目录对当前进程不可写"）与 **E114**
  （config.status 侧错误签名 `can't create ./confXXXXXX/subs1.awk: Permission denied`）
  描述的机制，本包是它在 **autoconf 2.59 + `confstatXXXXXX` + `-q`** 形态下的复现。
- **最小复现（逐字可跑，5 行）**：
  ```
  mkdir -p /storage/Users/currentUser/tmp/builds/probe && cd $_
  (umask 077 && mktemp -d -q "./confstatXXXXXX")   # → ./confstatABC123，ls -ld 见 drwx--S---
  : > ./confstatABC123/subs.sed                    # → can't create: Permission denied
  (umask 022 && mktemp -d -q "./confYXXXXXX")      # → drwxr-s--x
  : > ./confY*/subs.sed                            # → 成功
  ```
  对照实验另证：`mkdir`（同样的 umask 077）建出的目录是 `drwxrws--x` 且可写 ⇒
  触发点是 **mktemp 显式把临时目录置 0700** 的行为与 HMDFS 权限模型的组合。
- **已试过的失败方案**：
  1. **整文件替换 config.guess/config.sub（框架 `patch-autotools-script`）** ——
     本包**没有落点**：tarball 里根本没有这两个文件，`configure.ac` 也没有
     `AC_CANONICAL_HOST`（详见第五节，这是 B 判定的关键事实）。
  2. **`export TMPDIR=$HOME/tmp` 后重跑 configure** —— 无效：autoconf 2.59 的这一段落
     模板把临时目录**硬编码在当前目录**（`"./confstatXXXXXX"`），不读 TMPDIR。
  3. **改在别处构建（out-of-tree `mkdir build && cd build && ../configure`）** ——
     无效且更糟：HMDFS 的权限语义与目录位置无关，任何 0700 目录都写不进。
  4. **给 `mktemp` 造一个 PATH 替身** —— 未采用：那是伪造环境探针/构建工具语义，
     CI 侧环境不同就会翻，且不可审计。
- **最终方案**：`patches/0001-hmdfs-config-status-umask.patch` —— 按 E011 的处方
  把 configure 内该段落的两处 `umask 077` 改成 `umask 022`（改动 2 行、补丁 17 行，
  一处是 `mktemp -d -q` 主路径，一处是 `mkdir $tmp` 回退路径；后者在 HMDFS 下本就可写，
  一并改是为了与主路径同语义、防止回退分支再引入模式差异）。
  补丁用 `patch -p1 --dry-run` 在设备上验证可干净套用（`10-exp7-sample2-and-patch.log`）。
- **适用边界**：autoconf ≤2.59 一代、tarball 自带预生成 configure 的老 autotools 包
  （模板里带 `umask 077 && mktemp -d` 段落者）。autoconf 2.6x 之后段落形态是
  `./confXXXXXX`，同族修法见 archives/d/dirb/2.22 与 archives/a/aaphoto/0.45；
  **锚点字符串不同，不能直接照抄 dirb 的 replace 规则**。

### 墙 3 —— automake 1.8 maintainer 模式的反向再生成链

- **症状**：墙 2 的补丁生效后，`make -j1` 反而报
  ```
  ./config.status[709]: can't create ./confWFQMD2/subs1.awk: Permission denied
  config.status: error: could not setup config files machinery
  make: *** [Makefile:175: Makefile] Error 1
  ```
  且 `configure` 行数从 4918 变成 5713（临时目录段落变成 `./confXXXXXX` + `$ac_tmp`）
  —— 说明 configure 已被**设备上的 autoconf 2.72 重新生成**，E011 的补丁也被写回原样。
- **根因**：`AM_INIT_AUTOMAKE()`（automake 1.8）默认开启 maintainer 模式，
  `Makefile.in` 里带 `$(ACLOCAL_M4): configure.ac` / `configure: $(ACLOCAL_M4)` /
  `$(top_builddir)/config.status: configure` 一组再生成规则。补丁改过 `configure` 的
  mtime 后，`make` 沿这条链去跑 `aclocal`/`autoconf`（设备上 autoconf=2.72，
  与 tarball 的 2.59 不同构）。而设备上的 `automake` 一旦需要参与就更糟：
  `~/usr/local/bin/automake` 的 shebang 指向 `~/usr/local/bin/perl`，该解释器不存在，
  执行即 `No such file or directory`（这也是 `scripts/ohc/check_env.py` 在
  init-build 阶段抛 `NameError: name 'e' is not defined` 的真因，见第七节）。
- **已试过的失败方案**：用 `cp -R` 复制源码树后直接 make —— 反而更容易触发：
  `cp -R` 不给文件打时间戳（全部变"现在"），`configure.ac` 比 `aclocal.m4` 新 ⇒
  aclocal/autoconf 全链被踩（`06-explore-umask-fix.log` 实拍）。
- **最终方案**：`generate()` 里 `tc.configure_args.append("--disable-maintainer-mode")`，
  从 configure 侧把再生成规则整体摘掉；配方只消费 tarball 自带的预生成件。
  与上游 `bootstrap`（要 aclocal-1.8/automake-1.8）不自举的口径一致。
- **适用边界**：一切"tarball 自带 configure/Makefile.in + AM_INIT_AUTOMAKE"的老包；
  凡是配方需要对生成文件动补丁（本包 patch 0001 就是），都应显式关 maintainer 模式，
  否则补丁会被上游再生成静默覆盖。

## 四、运行期特征与测试口径

- metar 的业务是访问 NOAA（`https://tgftp.nws.noaa.gov/data/observations/metar/stations`），
  CI/设备不保证可达。上游 `src/main.c` 的 `download_Metar()` 支持
  **`METARURL` 环境变量覆盖取数地址**，实际请求 `<METARURL>/<站号大写>.TXT`
  （`strupc()` 会把入参原地转大写）。因此 test_package 把样本写成
  `file://<临时目录>/EHAM.TXT`，**完全离线**地真实走完
  `curl 取数 → parse_NOAA_data() → parse_Metar() → decode_Metar()`。
  curl/8.15.0 的 `Protocols` 列表含 `file`（实测 `curl --version` 第 3 行），
  file:// 取数在本设备跑通（`09-exp6-decode-corrected.log` 完整解码输出）。
- **上游 NOAA 报文头是斜杠日期**：`parse_NOAA_data()` 的正则是
  `^([0-9/]+ [0-9:]+)[[:space:]]+(.*)$`，日期字符类只收数字与斜杠，
  所以「年-月-日」这种连字符写法不匹配，走 `METAR pattern not found in NOAA data.`
  分支；「年/月/日」写法正常解码（两份样本只差分隔符，各实测 3 次结果稳定，
  见 `10-exp7-sample2-and-patch.log`；`test.sh` 里分隔符用 ASCII 码 47 现拼，
  不写字面日期，避免任何传输/编辑环节把分隔符改掉后测试静默失真）。
  测试样本一律用斜杠日期，并把「非法报文 → pattern not found → 字段不伪造」作为反向对照。
- **上游缺陷（不改，只披露）**：`download_Metar()` 不看 `curl_easy_perform()` 返回值，
  永远 `return 0` ⇒ 取数失败（网络不可达 / URL 非法）时 `metar` 仍**以 0 退出**、
  只打印 `METAR pattern not found in NOAA data.` 与全空字段。实测：
  `METARURL=file:///nonexistent-dir metar -d EHAM` → rc=0（`07-exp4-tar-maintainer.log`）。
  因此 test_package 的断言全部落在**输出内容**上，不依赖退出码判成功。
- man 页：`doc/Makefile.am` 有 `metar.1: metar.pod` + `pod2man --release=... --center=metar`
  规则，但 tar 内 `metar.1` 与 `metar.pod` 的 mtime **完全相同**
  （`2019-03-01 14:12:52`，`ls --full-time` 实测），make 判定 metar.1 已最新 ⇒
  `Making all in doc` 只报 `Nothing to be done for 'all'`，**pod2man 不参与构建**，
  `make install` 直接安装上游自带 man 页。未给文档规则打任何补丁。

## 五、平台识别：为什么本包没有 E007/E205/E268 的落点

- tarball 31 个文件里**既无 `config.guess` 也无 `config.sub`**（`ls` 实测；
  顶层只有 `Makefile.in/aclocal.m4/depcomp/install-sh/missing/bootstrap/VERSION.m4`）。
- `configure.ac` 全文没有 `AC_CANONICAL_HOST`/`AC_CANONICAL_SYSTEM`/`AC_CANONICAL_BUILD`；
  `configure` 里 `ac_config_guess="$SHELL $ac_aux_dir/config.guess"` 只是
  `AM_INIT_AUTOMAKE` 留下的**赋值**（`am__api_version="1.8"` 段落），
  全文再无第二处引用 ⇒ 该分支永不执行。
- ⇒ 本包的 `configure` 在鸿蒙上**不做三元组猜测**，实测 `checking for ...` 一路到
  `config.status: creating ...` 没有任何 "cannot guess build type / OS not recognized"
  类错误。框架的 `patch-autotools-script`（E007/E205/E268 的文件级替换）在本包**无落点**。
- 真正的第一道墙是**依赖探测**（墙 1）与 **HMDFS 临时目录权限**（墙 2），
  两者都有既有条目覆盖：墙 2 命中 **E011**（`ohc-run.py engine` 对本包首错原文实跑命中，
  处方 `umask 077 → umask 022` 与本包实测一致），E114 是同机制的 config.status 侧签名；
  墙 1 命中草稿 **DRAFT-E2186**（`AutotoolsDeps` 缺失家族）。

## 六、依赖发布核验（W0/R35/R36）

- `bash ci/scripts/preflight_check.sh metar/20190227.1` → 见第八节读数。
- 二进制可用性按 R35 用精确 install 判定，不用通配 `conan list`：
  ```
  conan install --requires=curl/8.15.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 --build=never
  → curl/8.15.0: Retrieving package df2856b724fa5aed00dc7f60cec6755df39cf2b6 from remote 'ohpcd'
  → Install finished successfully
  ```

## 七、环境与流程事实（如实记录，含与任务书不符项）

- 任务书写"B 机没有 `nice`"，实测 **`~/usr/local/bin/nice` 存在**（补齐
  `PATH=$HOME/usr/local/bin:$HOME/.local/bin:$PATH` 后可用）；本轮构建准入仍按
  `gate.sh --light` + `build-slot.sh --kind short` 走（GATE_PASS 记录在
  `01-preflight-before.log` 同轮输出，槽位实测"机动 0/3 空闲"）。
- `python3 scripts/ohc-run.py init-build metar 20190227.1 --url=... --tar tar.xz`
  在 Step8 环境检查崩溃：
  `scripts/ohc/check_env.py:33` 的 `return False, str(e)` 里 `e` 未绑定 →
  `NameError: name 'e' is not defined`（框架 bug，`scripts/` 对协作者只读，未改）。
  **真错不是"依赖没发布"**，而是它探测 `automake` 时 subprocess 抛 FileNotFoundError：
  `~/usr/local/bin/automake` 的 shebang 是 `#!/storage/Users/currentUser/usr/local/bin/perl`，
  该路径下没有 perl（设备上 perl 在 `/data/service/hnp/bin/perl`）。
  崩溃发生在 download/extract/scaffold 之后，故归档骨架与源码树
  （`~/tmp/builds/metar-20190227.1.orig`）已正常产出，本包不需要 automake（走预生成
  configure），改由手写配方继续，未伪造任何目录。
- `ohc-run.py recipe-search metar`（无语境）→ 无相似配方；
  `recipe-search metar -b autotools -d curl` → top1 `dirb/2.22`（score 0.6，含补丁智慧），
  本配方以其为底稿，并按本包实物差异（无 curl-config 探测、autoconf 2.59、无 install
  语义问题）收敛。

## 八、B 声明（3+2）

- **适配路径**：路径 A（基础适配，命中既有条目；无框架改动、无源码功能补丁）
- **使用知识库**：E011（HMDFS `umask 077` 临时目录不可写，处方 umask 077→022，本包按此实施）、
  E114（config.status 侧错误签名，用于确认同一机制）、
  DRAFT-E2186-autotools-deps-missing-dep-flags（`AutotoolsToolchain` + `AutotoolsDeps`
  双 generator 修法）、archives/d/dirb/2.22（同族 autotools+curl CLI 配方底稿，
  recipe-search 命中 top1）
- **知识库扩展**：无新增机制条目 —— 本包三道墙全部落在既有条目内；
  两处"条目未直接覆盖"的细节已写入本 notes（第五节：E007/E205/E268 在无
  config.guess/config.sub 的包里**无落点**；第二节：autoconf 2.59 的
  `confstatXXXXXX` + `-q` 锚点与 dirb/aaphoto 的 `confXXXXXX` 锚点**字符串不同**，
  不能照抄 replace 规则），建议由主理决定是否折进 E011/E114 的 `match_keywords`。
- **关联 Issue**：无（B 判定为命中，未建【知识库扩展】Issue）

## 九、最终状态

**最终状态**：built —— 五道门禁本轮全部真跑并读数（执行棒 3 · 主理-75 续做 · B 机），
配方修复提交 `398869b2f2`（父提交 `3e5f072d48`，基线 `48d9cee684`，分支
`feat/metar-20190227.1`）；本节所在提交即交付提交。设备侧证据目录
`~/tmp/uc2/z75m2/`（逐条日志路径见 9.5）。

### 9.1 第四道墙：conan 依赖的共享库使 configure 的运行探测被判「不能运行编译出的程序」

上一棒停在 G2 FAIL。**第一条真实错误不在 configure 的转述里，而在构建目录的
`build-release/config.log`**（原文照录，行号为 config.log 自带）：

    configure:2165: checking whether the C compiler works
    configure:2171: ./a.out
    Error loading shared library libcurl.so: (needed by ./a.out)
    configure:2174: $? = 127
    configure:2181: error: cannot run C compiled programs.

- **根因**：墙 1 的处方 `AutotoolsDeps` 除 -I/-L 外，还把 host 依赖的 libs 导成环境变量
  `LIBS=-lcurl`，于是 `AC_PROG_CC` 里最早那次运行探测编出的 `a.out` 一上来就动态依赖
  `libcurl.so`；OHOS 动态加载器的默认搜索路径不含 conan 缓存包目录，执行返回 **127**，
  autoconf 把「加载器找不到库」误写成「cannot run C compiled programs」并建议改用
  `--host`。**不是**能力墙、**不是**上游源码 bug。
- **三态探针**（`~/tmp/uc2/z75m2/probe.log`；编译 flags 逐字取自 config.log 的
  `configure:2111`）：RUN1 无 `LD_LIBRARY_PATH` → rc=127 且报错与 config.log 同签名；
  RUN2 注入 `<CONAN_HOME>/p/curl3b1c48f2fda9f/p/lib` → rc=0；RUN3 对照件（同一份
  `m.c` 但不链共享依赖）→ rc=0。⇒ **否证**「交叉产物在本机不可执行」「exec 位/目录
  umask」「陈旧或不可达 CWD」三条备选，**证实**「依赖共享库对 conftest 不可见」。
- **修法**（增量 22 行）：`generate()` 里用 `conan.tools.env.Environment` 把全部 host
  依赖的 `cpp_info.libdirs` 前置进 `LD_LIBRARY_PATH`，再
  `env.vars(self).save_script("dep_libdirs_runpath")` 落进 conanbuild 环境。
  生效直证：`build-release/conan/dep_libdirs_runpath.sh` 导出
  `LD_LIBRARY_PATH=".../p/curl3b1c48f2fda9f/p/lib"`，且同目录 `conanbuild.sh` 第 1 行
  串入该脚本。
- **出处**：`knowledge/drafts/DRAFT-conan-dep-shared-libs-break-configure-conftest`
  （rec=`inject-dep-libdirs-ld-library-path`，metrics_success_count=2），同法先例
  `archives/a/aaphoto/0.45`、`archives/d/dirb/2.22`。草稿 forbid 项一并遵守：**未**用
  `--host/--build` 绕过（那会让全部检测走假设值），**未**把 .so 拷进系统或全局路径。
  草稿的另一半 `bindirs→PATH` 本包不需要——`configure` 全文 `curl-config` 命中 **0** 次
  （实测 grep，与 dirb 不同）。
- **`shell-init: error retrieving current directory` 判为非根因**：修好后同一噪声在本轮
  `conan-create.log` 里仍占 **178** 行而构建通过；且本包 configure（autoconf 2.59 生成）
  全文 `ac_pwd` 命中 **0** 次 ⇒ 不存在「working directory cannot be determined」硬校验，
  该噪声只是 HMDFS 不提供 getcwd 的副作用（同族记载见
  `knowledge/drafts/DRAFT-6487-classads-configshell-hmdfs-getcwd.md`、dirb 的
  `_patch_configure_pwd`），对本包**无落点**、不需处置。
- **机制认知变更（提请主窗重判 B，本棒不改判）**：第三节「三道墙」的清单不含本道墙，
  §五「真正的第一道墙是墙 1/墙 2」的覆盖面结论也随之不再等价；本道墙的处方落在**既有
  草稿**内（hit 家族，未新增机制条目），故 §八 的 3+2 与 B 判定的字样本棒**一字未动**，
  只把新事实补在这里，由主窗据 E011/E114/DRAFT-E2186/DRAFT-conan-dep-shared-libs
  四条重判 hit 或 create。
### 9.2 五道门禁逐条读数（worktree 根执行，命令 / 退出码 / 判据）

1. `bash ci/scripts/preflight_check.sh metar/20190227.1` → **RC=0**；
   `[OK] 已发布: curl/8.15.0`、`[OK] 版本号未被占用: metar/20190227.1`（W0/R36）。
   配方依赖版本 = `curl/8.15.0`（未发布的 8.5.0 已弃用）。
2. `python3 scripts/ohc-run.py conan-verify metar 20190227.1` → **RC=0**；
   `reports/conan-verify-report.md` 第 3 行 **Verdict: PASS**（Date 2026-09-27T01:26:08），
   逐门：G0 ✅ PASS、G1 ✅ PASS、G2 ✅ PASS、G3 ✅ PASS、G4 ✅ PASS、L2 ✅ PASS、
   L4 ✅ PASS、L5 ✅ PASS（文字与 Verdict 行一致，无图标反转）。
   ⚠️ G0 的 E490 与 G4 的「无法找到程序包 ID」为建议级；L2/L4/L5 的 PASS 实测是
   「跳过（无 cache 路径）」形态——纯可执行包 + conan 驱动流程无 staging 产物，
   这三项在本包形态下没有实际判据，如实记此。
3. `python3 scripts/ohc-run.py finish metar 20190227.1 built` → **HANDOFF EXIT_CODE: 0**，
   状态 `built`；W3 本地 CI 模拟通过（`.ci-result.json` 的 `"exit_code": 0`，
   timestamp 2026-09-27T01:20:44，含完整性哈希，本棒未手改）；3 条 ⚠ 见 9.4。
4. W4/W5 审计（入口 `scripts/pre_pr_audit.py`）：`generate` **RC=0** →
   审计输入 64779 B / 11 个变更文件；`report` **RC=0** → 结论 **PASS**，
   统计 **P0=0 P1=0 P2=0 P3=4**；`check --repo-dir <版本目录>` **RC=0**
   （✅ W3 本地 CI 模拟已通过）。审计报告落
   `archives/m/metar/20190227.1/reports/audit-result.json`（`submission.py` 读取的权威
   路径；`reports/` 被 .gitignore 第 96 行忽略，故它是本地/submit 证据件、不进 PR）。
   4 条 P3：url 模板字段（仓内 6175 份 conanfile 中 1196 份同款，CI 回填）、
   test.sh 用 `set -u` 而非 `set -euo pipefail`（T1/T5 依赖非零退出码取 rc）、
   补丁文件名按机制命名（同已合入的 a52dec `0002-configure-umask-022.patch`）、
   E490 清单不可照抄（本包无 config.guess/config.sub）。
   **本条审计由本棒在同一上下文执行**（未另派独立子任务），主窗若要求严格上下文隔离应复核。
5. `python3 scripts/ohc-run.py graph validate` → **RC=0**；
   `✅ All checks passed (169 warnings)`，540 个 .kv ↔ 540 个 .md ↔ 540 行 index 配套；
   告警全是存量条目（E219/E253/E305 字段空、C13 长尾词、C14 编号空洞），与本包无关；
   本棒**未新增也未删除** `knowledge/drafts/` 下任何文件。

### 9.3 测试账本（本轮从盘上复取，与证据同源）

| 项 | 值 | 出处 |
|---|---|---|
| 上游测试静态总数 | **0** | §二 五条清点（3 个 Makefile.am + configure.ac 全文无 `TESTS`、无 `check:`；`make -n check` → No rule to make target）|
| 上游实测通过 / 跳过 / 失败 | 0 / 0 / 0 | 无用例可跑；`build()` 打 `HMBS_UPSTREAM_TEST_RESULT` 固定证据（conan-create.log 第 312 行 status=no_tests）|
| test_package 断言 | **28 / 28 通过** | `reports/conan-create.log`（457 行 / 39693 字节）第 455 行 `METAR_TEST_ASSERTIONS_PASSED=28`；同日志 `grep -c "^ok  :"` = 28；W3 日志 `reports/w3-local-ci.log`（390 行）第 359 行同值 28，第 199 行 `checking whether the C compiler works... yes` |
| 断言分组实测 | T1 3、T2 2、T3 12、T4 9、T5 2 = 28 | 与 §二、`test_package/MANIFEST.yml` 的 `assertion_count: 28` 同源一致（rule4：声明 28 ≤ 实测 28）|
### 9.4 已知非阻断告警与边界（如实，不粉饰）

- finish 的 3 条 ⚠：①「缺少 release/debug tar.gz」——conan 驱动流程不产 staging 包；
  ②「状态不一致 notes=creating vs manifest=built」——框架正则 `(?:状态|status)[：:]\s*(.+)`
  取最后一次匹配，被 §三/§五 里引用的 `config.status: creating …` 日志原文命中，属正则
  误抓而非状态伪造（本节末框架自写的 `最终状态: built` 才是终态）；③「notes.md 无对话记录」
  ——`### 对话 #` 约定，仓内该约定落地极少。三条均未改变 EXIT_CODE 0。
- 上一棒 §七 记录的两条环境事实本棒**未复核**（原文照录）：B 机 `~/usr/local/bin/nice`
  存在（与任务书不符）；`scripts/ohc/check_env.py:33` 的 `str(e)` 未绑定会假红（框架 bug，未改）。
- 框架自更新记录：`finish` 在 notes.md 末尾追加过 4 行（`**编译结束**: 2026-09-27 01:19` /
  `**最终状态**: built`），本棒原样保留、未改写。
- 本棒未做：未跑 `submit`、未建 PR、未 upload、未碰任务登记表与平台令牌、未改任何
  框架文件（`ci/`、`scripts/` 零改动）。`git status` 里的 `archives/l/libXext/` 两个
  改动文件是他棒资产，本棒未触碰、未提交；`.build-cache/` 未跟踪、未加入。

### 9.5 证据路径清单（B 机 `~/tmp/uc2/z75m2/`）

`probe.log`（三态探针）、`20-preflight.log`、`21-conan-verify.log`（首次转绿）、
`22-finish.log`、`23-audit-generate.log`、`24-graph-validate.log`、`25-audit-check.log`
（`--repo-dir` 传仓库根时的 RC=1 记录）、`26-audit-report.log`、`27-audit-check2.log`
（RC=0）、`28-remove.log`（只清本包 `metar/20190227.1*`）、`29-conan-verify-final.log`
（判绿终态）、`audit-input.json`、`audit-result-feat-metar-20190227-1.json`。
仓内件：`archives/m/metar/20190227.1/reports/` 下的 `conan-create.log`、
`conan-verify-report.md`、`w3-local-ci.log`、`audit-result.json`（均被 .gitignore 忽略，
不进 PR），以及 `.ci-result.json`（同样不入库）。
---

**编译结束**: 2026-09-27 01:46
**最终状态**: built
