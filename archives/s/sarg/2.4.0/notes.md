# sarg 2.4.0 适配笔记

## 编译环境
- 构建系统: autotools（`configure` 由 GNU Autoconf 2.69 生成 + 手写 `Makefile.in`；上游另有一份可选 `CMakeLists.txt`，本次未使用）
- 编译日期: 2026-09-23
- 编译器: clang（OHOS NDK 侧 `/data/service/hnp/bin/clang`，clang 15 系）
- 状态: built

## 编译步骤

配方侧等价命令（`conan create` 实际执行的就是这一组）：

```sh
# 1) 上游源码包（官方 SourceForge 发布位）
#    sha256 实测：b4ca0f41f6467673b4c65c6798b44a8886f08180c055eb11c37a96dfc28cb5c3
tar -xzf sarg-2.4.0.tar.gz && cd sarg-2.4.0

# 2) 4 个 OHOS 补丁（patches/0001..0004，由 refresh-patch --auto 生成）

# 3) configure —— AutotoolsToolchain 只负责注入 --prefix=/ 与 ${prefix} 形态的
#    --bindir/--sbindir/--libdir/--includedir/--oldincludedir；配方在 build() 里
#    用 autotools.configure(args=[...]) 追加第二个 --prefix=<package_folder>
#    （autoconf 取最后一次赋值）与 --disable-sargphp。-fcommon 走 toolchain
#    cflags（R33：不裸用 shell 环境变量）。第 4) 步的 make -j1 在源码目录内做
#    in-tree 构建，见「问题 7」。实际命令行（本轮 conan-create.log:119）：
./configure --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' \
            '--libdir=${prefix}/lib' '--includedir=${prefix}/include' \
            '--oldincludedir=${prefix}/include' \
            --disable-nls --without-gd --without-ldap --without-iconv \
            --without-pcre --without-zlib --without-bzlib --without-liblzma \
            --prefix=<package_folder> --disable-sargphp

# 4) make -j1
# 5) make install DESTDIR=      ← DESTDIR 必须显式置空，见「问题 5」
```

`configure` 探测结果（关键字段）：build/host 三元组被识别为
`aarch64-unknown-linux-ohos`；`checking for implicit-function-declaration error
flag ... yes`、`checking for format error flag ... yes`（说明上游
`-Werror=implicit-function-declaration` / `-Werror=format` 在本平台编译器上成立，
无需放宽）。

打包落点（`DESTDIR=` 空、前缀即包目录）：

| 路径 | 内容 |
|------|------|
| `<pkg>/bin/sarg` | 主程序 |
| `<pkg>/etc/sarg.conf`、`exclude_codes`、`user_limit_block`、`css.tpl` | 配置与数据文件 |
| `<pkg>/share/sarg/images/`、`<pkg>/share/sarg/fonts/` | 报告素材（编译期以 `-DIMAGEDIR`/`-DFONTDIR` 烧成同样的绝对路径） |
| `<pkg>/share/man/man1/sarg.1` | 手册页 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure` 报 cannot guess build type | `cfgaux/config.guess`、`cfgaux/config.sub` 是 2015-03-04 版，不认识 HarmonyOS | 补丁 0001/0002 增补 `*:HarmonyOS:*:*` 分支与 `linux-ohos` / `-linux-ohos*` 白名单 |
| 2 | 链接期 `ld.lld: error: duplicate symbol: BgImage / outdir / period / code / debugz ...` | `include/conf.h` 用**暂定定义**在头文件里定义全局变量；clang ≥ 10 默认 `-fno-common`，每个 .o 都产出强符号 | toolchain cflags 注入 `-fcommon`（补丁之外的唯一必需编译开关） |
| 3 | 加了 `-fcommon` 之后**仍然**报同样的 duplicate symbol | 上游手写 `Makefile.in:75` 的编译规则 `$(CC) -c ... $(CFLAGS) $<` 不把 `Makefile` 自身列为先决条件；CFLAGS 变了但 65 个 .o 时间戳仍新于 .c ⇒ make 一次都不重编，直接拿旧的 `-fno-common` 目标文件去链接 | 保持 `-j1` 干净全量构建（Conan 每次从干净源码树出发，天然满足）；本仓配方不引入 `make clean`，但 notes 记录该坑以免有人手工增量复现 |
| 4 | **本包未复现**——同族先例 `archives/a/aide/0.19.3`、`archives/a/a52dec/0.7.4` 在 HMDFS 上 `configure` 建 conftest 临时目录后失败 | 先例根因：`archives/a/aide/0.19.3/patches/0003-configure.patch:14-21` 的 `configure` 用 `(umask 077 && mktemp -d "./confXXXXXX")`，先例里 0700 建出的目录后续 `cp` 写不进（`archives/a/a52dec/0.7.4` 是同族的另一形态，其 `0002-configure-umask-022.patch:7-8` 改的是 `$TMPDIR/csXXXXXX` 那一处）。**本包该机理经实测不成立**：探针 `~/tmp/uc2/zhuli-5-sarg-2.4.0/logs/probe-umask077.log` 显示 HMDFS 上 `umask 077 && mkdir` 实际得 **2771**（setgid + 组可写，非 0700），后续 `cp` rc=0；**对照组 `umask 022 && mkdir` 同样得 2771** ⇒ 该挂载点上目录模式由文件系统强制、与 umask 无关，0003 对本机的结果模式没有影响；`explore2/3/4` 三轮 configure 的首条真实错误分别是 `cannot guess build type`（2 处）与 `no acceptable C compiler found in $PATH`，无一条 conftest 写不进；证据目录全量 grep `Permission denied` 只命中 `verify5.log:32` 的**检测器正则字面量**，不是失败记录 | 补丁 0003 作为**与本仓先例一致的预防性处理**保留（删它会与同类配方分叉），明确**不计为本包适配根因** |
| 5 | `make install` 产物落在 `<pkg><pkg>/bin/sarg`（路径重复） | `Makefile.in` 的 install 规则是 `cp sarg $(DESTDIR)$(bindir)/...`，而 `$(bindir)` 已被 configure 展开成**绝对**包路径；Conan 默认再塞一个 `DESTDIR=<package_folder>` | 配方里 `autotools.install(args=["DESTDIR="])`，显式把 DESTDIR 置空 |
| 6 | `sarg` 运行时打不开图片/字体目录 | `BINDIR/SYSCONFDIR/FONTDIR/IMAGEDIR/LOCALEDIR` 是编译期 `-D` 烧死的绝对路径，与安装位置无关 | 用 AutotoolsToolchain 的 `--prefix=<package_folder>` 让烧进去的路径就是包内路径；`make install DESTDIR=` 精确落到该处 ⇒ 素材可寻（消费者测试 A12 断言不再出现 `Cannot open directory`） |
| 7 | configure 成功、`make -j1` 却报 `No rule to make target 'util.c', needed by 'util.o'. Stop.` | 上游 `Makefile.in` 是**手写**的（不是 automake 生成）：`OBJS` 直接列 `util.o`，隐式规则 `%.o: %.c` 只在 make 当前目录找源码，**没有 VPATH / `$(srcdir)` 前缀**；而 Conan `basic_layout` 把 source（`<b>`）与 build（`<b>/build-release`）分目录，build 目录里一个 `.c` 都没有 | `layout()` 里在 `basic_layout(self, src_folder=".")` 之后加 `self.folders.build = "."` 做真正的 in-tree 构建（本仓同形先例 `archives/a/acpitool/0.5.1`、`archives/a/abduco/0.6`）；生成物仍在 `<b>/build-release/conan`，不污染源码树。**不去改上游 Makefile 加 VPATH**——那会把改动面从"选目录"扩大到"改构建脚本" |
| 8 | configure 报 `working directory cannot be determined`（间歇） | 设备 profile `[buildenv]` 把 `CONFIG_SHELL`/`SHELL` 钉死 `/data/service/hnp/bin/bash`，autoconf 用它重新 exec configure，而该 bash 在 HMDFS 构建目录下 getcwd 间歇失败（E386） | `tool_requires("bash/5.3")` 取包内 bash，并在 `build()` 里把生成器聚合 env 脚本中的 `/data/service/hnp/bin/bash` 文本替换成该 bash（工具链级 env 会被 profile `[buildenv]` 覆盖，聚合脚本是唯一可靠落点；同名二次 `save_script` 会自 source 递归，故不用）。只影响构建上下文，不进 host `package_id`；不改框架 profile |
| 9 | 报告输出目录被 `my_mkdir()` 判为不可用 | `util.c` 逐级探测路径前缀用 `access(w0, R_OK)`；OHOS 上 `/storage` 挂载为 `0711`，**存在**的前缀返回 EACCES，随后 `mkdir()` 又报 EEXIST，而上游把 EEXIST 当致命错误 | 补丁 0004 把存在性探测改为 `access(w0, F_OK)`（前缀只需"存在"，不需"可读"），无平台宏、非 OHOS 平台语义不变 |

问题 6 的补充说明（PHP 前端 `SARGPHPDIR`）：上游把它默认成 `/var/www/html`，
OHOS 根文件系统不可写。它**不是**编译期宏——发布树内没有任何 `.c/.h` 引用
`SARGPHPDIR`（`grep -rn 'SARGPHPDIR' --include=*.c --include=*.h .` 空命中），
只作为 `Makefile.in:134` 的安装目标存在，并被
`if test -n "$(SARGPHPDIR)" -a -d "$(DESTDIR)$(SARGPHPDIR)"` 守卫。
本次按上游自己的开关 `--disable-sargphp` 关掉这段安装（`AC_ARG_ENABLE(sargphp)`
的 `x$enableval != xno` 分支 ⇒ `SARGPHPDIR` 留空 ⇒ install 该行整体跳过），
因此 configure 输出里不再出现 `using /var/www/html ...`，构建全程不触碰只读根。
sarg-php 是 PHP 报表浏览前端，HarmonyOS 侧没有 PHP 运行时，不属于本 CLI 包的消费路径。

## 源码修改

全部以 `patches/` 下 4 个补丁形式交付，均由
`python3 scripts/ohc-run.py refresh-patch sarg 2.4.0 --auto` 依据
`.edit-tracker.json`（snapshot 基线 = 未改动的原始发布树）逐文件生成，未手工编辑补丁文本。

| 补丁 | 被改文件 | 内容 | 是否含平台宏 |
|------|----------|------|--------------|
| `0001-cfgaux-config.guess.patch` | `cfgaux/config.guess` | 主 case 顶部插入 `*:HarmonyOS:*:*) echo ${UNAME_MACHINE}-unknown-linux-ohos` | 否（纯三元组表项） |
| `0002-cfgaux-config.sub.patch` | `cfgaux/config.sub` | KERNEL-OS 组合加 `linux-ohos*`；OS 白名单加 `-linux-ohos*`；并阻断 `-linux*) → -linux-gnu*` 的归一化把 ohos 吞掉 | 否 |
| `0003-configure.patch` | `configure` | `umask 077` → `umask 022`（2 处） | 否（**预防性**：本包未复现，机理实测不成立，见症状表第 4 行） |
| `0004-util.c.patch` | `util.c` | `my_mkdir()` 前缀存在性探测 `access(R_OK)` → `access(F_OK)`，附注释说明理由 | 否 |

`0003-configure.patch` 改的是 autoconf **生成**文件：本仓 `scripts/patch-autotools-ohos.pl`
与 `knowledge` 的先例（如 `archives/a/a52dec/0.7.4/patches/0002-configure-umask-022.patch`）
都走这条路，原因是设备侧没有 autoconf 2.69 可重生成，且改动是单行策略常量、
不含平台判定 ⇒ 走 edit-tracker 精准登记，未被静默当构建产物丢弃。

工具链说明：`scripts/patch-autotools-ohos.pl` 在本包上**不可用**，实测 score 1/5，
两条硬理由记在此处以免后人重复踩：
① 它向 `config.guess` 插入的是 `GUESS=${MACHINE}-unknown-linux-ohos` 赋值形态，
   而 2015 版 `config.guess` 全文没有 `GUESS` 变量消费者（主 case 各分支一律 `echo; exit`），
   赋值不被读取 ⇒ 打完补丁仍然 cannot guess build type；
② 它对 `config.sub` 的三处锚点全部落空（warn）。

## 依赖版本

**Conan 主机依赖：0 个。** `requirements()` 不声明任何包（`package_id` 里只有 settings）。
唯一的依赖是 `tool_requires("bash/5.3")`，**构建上下文**（E386 shell 路由，见问题 9），
不进入 host 包、不参与链接、不进 `package_id`。
上游可选特性（gd / ldap / iconv / pcre / zlib / bzlib / liblzma / nls）全部显式
`--without-*` / `--disable-nls` 关闭 ⇒ 不链接任何系统同名库（R26），
也不引入预编译依赖（R36 对下游无约束）。
实测 `ci/scripts/preflight_check.sh sarg/2.4.0` → `[OK] 预检通过（无依赖需要检查）`。

运行时仅需 libm（`LIBS = @LIBS@ @LIBINTL@ -lm`）与 OHOS libc（musl）。

## 上游测试清点与五维数字（R51）

**上游测试程序数：0。** 四条清点证据（均在 sarg-2.4.0 发布树内实测）：

1. 对已 configure 好的树执行 `make check` ⇒
   `make: *** No rule to make target 'check'.  Stop.`
   设备日志：`/storage/Users/currentUser/tmp/uc2/zhuli-5-sarg-2.4.0/logs/explore_make_n_check.log:1`
2. `grep -n '^[a-zA-Z-]*:' Makefile.in` 的目标全集为
   `all sarg doc install uninstall TAGS clean mostlyclean distclean realclean
   install-po uninstall-po clean-po update-po po-from-tp`
   —— 没有 `check`、没有 `test`、没有 `installcheck`。
3. 发布树内 `find . -iname '*test*' -o -iname '*spec*'` 只命中一个文件
   `BETA-TESTERS`，内容是志愿者姓名列表（散文），不是测试程序。
4. 上游另一套构建系统 `CMakeLists.txt` 只使用 `CHECK_INCLUDE_FILE` /
   `CHECK_C_COMPILER_FLAG` 一类**特性探测**宏，全文没有 `enable_testing()`
   也没有 `add_test()`。

因此 `conanfile.py:build()` 里**不执行**任何上游测试命令（写了只会得到假的红），
`test_package/MANIFEST.yml` 的 `upstream_tests: []` 与 `upstream_test_in_build: false`
与上面的清点一致。缺失的上游套件由 test_package 的真消费者测试补足（R34：
必须真正驱动被测二进制并断言产物内容，不允许只打印字符串）。

五维测试数字：

| 维度 | 数量 | 口径 |
|------|------|------|
| 静态 | 0 | 上游无静态测试/断言框架可枚举（`make check` 无目标，CMake 无 `add_test`） |
| 注册 | 14 | `test_package/MANIFEST.yml` 的 `assertion_count: 14`，对应 `test_sarg.sh` 的 A1..A14 |
| 实测 | 14 | 真机 `conan create` 触发的 test_package 实际执行并通过的断言数（见下表逐条结果） |
| 跳过 | 0 | 无按平台/条件跳过的断言 |
| 失败 | 0 | 无失败断言 |

`test_sarg.sh` 的输入是自己写进脚本的 3 条 squid3 combined 风格日志样本
（2 个用户、2 个站点、含 1 条 404）——**上游发布树内没有 test/ 也没有 examples/
目录，不存在可直接复用的样例日志**（证据见上面第 3 条）。

## 验证结果

```text
实测轮次：`conan-verify`（`ohc-run.py conan-verify sarg 2.4.0`，memcap 2500MB / avail-factor 1.2），驱动脚本 `/storage/Users/currentUser/tmp/uc2/sarg-v6.sh`，日志 `/storage/Users/currentUser/tmp/uc2/zhuli-5-sarg-2.4.0/logs/verify8.log`。

证据落盘说明：reports/ 是本地 scratch，每轮 finish 会重跑并覆盖 reports/conan-create.log，上表行号取自 conan-verify 轮（verify8）。同一轮读数已在最后一轮 W3 本地 CI 日志 reports/w3-local-ci.log 里复核：170 行 Building from source、179 行 Calling build、180-183 行共 4 次 Apply patch、332/333 行烧进二进制的 FONTDIR/IMAGEDIR、423 行 RUN: make install DESTDIR=、464 行 Package folder 与该前缀一致（package() 镜像保险未触发）、518-520 行 A13/A14 pass 与 ASSERTS=14 PASS=14 FAIL=0。

构建侧（`reports/w3-local-ci.log`，真编译轮。`reports/conan-create.log` 已被后续缓存命中轮覆盖为 125 行 ⇒ 本块行号一律取自 w3-local-ci.log）：
  `Building from source` 1 次 / `Calling build` 1 次 / `Apply patch` 4 次（= conandata.yml `patch_file:` 条数 4）
  烧进二进制的资源目录（第 332 行）：
    configure: using /storage/Users/currentUser/tmp/ch/home-zhuli5-sarg/p/b/sargfadea10616a4a/p/share/sarg/fonts as the directory of the fonts
  第 333 行：configure: using /storage/Users/currentUser/tmp/ch/home-zhuli5-sarg/p/b/sargfadea10616a4a/p/share/sarg/images as the directory of the images
  `--disable-sargphp` 生效：configure 输出中不再有 sarg-php 安装行（全文 `grep -n 'sarg-php'` 命中 0 行）
  `make install` 命令行（第 423 行）：sarg/2.4.0: RUN: make install DESTDIR= -j20
  package() 镜像保险未触发：第 464 行 `Package folder .../sargfadea10616a4a/p` 与第 332/333 行烧录前缀同源 ⇒ 落点 == `self.package_folder`

门禁判定：
  ## G0: ✅ PASS
  ## G1: ✅ PASS
  ## G2: ✅ PASS
  ## G3: ✅ PASS
  ## G4: ✅ PASS（⚠️ 无法找到程序包 ID）
  ## L2: ✅ PASS（⏭️ 跳过（无 cache 路径）⇒ 本轮未实际执行）
  ## L4: ✅ PASS（⏭️ 跳过（无 cache 路径）⇒ 本轮未实际执行）
  ## L5: ✅ PASS（⏭️ 跳过（无 cache 路径）⇒ 本轮未实际执行）

消费者测试（test_package，`sh test_sarg.sh <pkg>/bin/sarg <pkg> <workdir>`，逐条读数见 w3-local-ci.log 第 506-519 行）：
  [A1] pass: sarg exits 0
  [A2] pass: success marker in output
  [A3] pass: --version reports 2.4.0
  [A4] pass: all 3 log records were parsed
  [A5] pass: top level index.html
  [A6] pass: date index report was generated
  [A7] pass: topsites lists www.example.com
  [A8] pass: topsites lists missing.example
  [A9] pass: user1 only sees its own sites (per user isolation)
  [A10] pass: user2 report has its own domain
  [A11] pass: siteuser maps the site back to user1
  [A12] pass: baked IMAGEDIR resolves at run time (no missing asset warning)
  [A13] pass: all 4 png assets of the baked IMAGEDIR were copied into the report
  [A14] pass: fonts and images installed inside the package under the baked FONTDIR/IMAGEDIR
  汇总（w3-local-ci.log:520）：ASSERTS=14 PASS=14 FAIL=0
  W3 门禁 L4_RESULT=**warn**（w3-local-ci.log:527-528、545）：静态安全扫描在补丁里命中危险函数名。
  本轮**未逐条核**该 warn ⇒ 不据以声称已排除误报（xrdp 侧有 `fgets` 被 `gets` 子串正则命中的同款误报先例，见 `build_and_test.sh:1469`）。

上游测试：0 个（`make check` 无目标，四条清点证据见上一节 ⇒ 实测 0 条、跳过 0 条、失败 0 条，不存在被跳过或虚报的上游用例）。
```

## 交付物

| 文件 | 说明 |
|------|------|
| `<pkg>/bin/sarg` | Squid 日志分析报告生成器主程序 |
| `<pkg>/etc/sarg.conf` | 默认配置样例 |
| `<pkg>/etc/exclude_codes`、`user_limit_block`、`css.tpl` | 运行期数据文件（消费者测试直接消费 `exclude_codes`） |
| `<pkg>/share/sarg/images/`、`<pkg>/share/sarg/fonts/` | HTML 报告素材（与烧进二进制的 IMAGEDIR/FONTDIR 同一路径） |
| `<pkg>/share/man/man1/sarg.1` | 手册页 |

sarg-php（PHP 报表浏览前端）未打包：上游默认装到 `/var/www/html`，
且需要 Web 服务端与 PHP 运行时，不属于本 CLI 包的消费路径。

## 注意事项

1. **包不可迁移（已申报，不是已解决项）**：`SYSCONFDIR/FONTDIR/IMAGEDIR/LOCALEDIR`
   是编译期 `-D` 烧死的绝对路径，本次烧的是 `conan create` 时的 `self.package_folder`
   （⇒ `--prefix=<package_folder>`）。⇒ 换部署路径后报告素材会找不到（程序仍能出报告，
   只是丢图片/字体，退化为纯文本 HTML）；用户侧可用 `sarg.conf` 的 `image_dir` /
   `graph_font` 重新指路（`getconf.c:977`、`getconf.c:943`），包内 `share/sarg/{images,fonts}`
   就是它们要指向的位置。若下游要把包搬到固定运行位（例如 HNP 挂载点），
   需要以该路径为 `--prefix` 重新构建。
   `package()` 里另有一道保险：把 `make install` 的落点（= 烧进去的前缀）与
   `self.package_folder` 比对，不一致时告警并把整棵树镜像进包，保证包结构完整；
   正常 `conan create` 两者相同，该分支是无操作（本轮日志见「验证结果」）。
2. `SARGPHPDIR`（PHP 前端安装位，上游默认 `/var/www/html`，OHOS 不可写）已按上游
   开关 `--disable-sargphp` 关闭，configure 输出中不再出现该行；它本来也不是编译期宏，
   所以关掉不影响 `sarg` 可执行文件的功能。sarg-php 未打包。
3. `-fcommon` 是本包**必需**开关，不是可选优化。去掉它以前提到的 duplicate symbol
   方式失败，且失败点在链接期、报错量超过 lld 的 error limit，第一眼看上去像平台问题。
   排查时请按本 notes 问题 2 的口径判断，不要归因给 OHOS/工具链。
4. 上游 0 测试这一事实已按 R51 留证据（4 条 + 日志路径行号）。若后续版本引入
   `make check`，`build()` 与 `MANIFEST.yml` 需同步回填。
5. `--disable-nls` 后 `po/Makefile` 仍在 configure 的生成清单里（configure 输出里有 creating po/Makefile 一行），而 `install: all install-po` 会 `$(MAKE) -C po install`。
   实测该路径在 nls 关闭时为无操作：`po/Makefile:183` 的 `all: check-macro-version all-no`
   （`USE_NLS = no` ⇒ `install-data: install-data-no: all`），不触发 `msgfmt`，
   本轮 install 阶段真实走完、无报错。
---

**编译结束**: 2026-09-23 14:12
**最终状态**: built
