# libbrahe 1.3.2 适配笔记

## 编译环境
- 构建系统: autotools（configure + Makefile.in + libtool，随包脚本为 2009/2010 世代）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（OHOS SDK，/data/service/hnp/bin/clang，默认 Target: aarch64-unknown-linux-ohos）
- 状态: built

## 上游信息
- 软件: libbrahe（Scott Robert Ladd 的 Brahe 数值工具集，纯 Standard C，gnu99）
- 版本: 1.3.2（ChangeLog 末条 2011-07-06，上游最后一次发布）
- 许可证: BSD-2-Clause（Simplified BSD/FreeBSD License，`LicenseOpenSource.txt`；`LicenseClosedSource.txt` 是作者双许可的商业条款说明）
- 官方主页（已失效，仅存归档）:
  https://web.archive.org/web/20191102085924/http://coyotegulch.scottrobertladd.net/products/brahe/index.html
- 源码 URL: https://deb.debian.org/debian/pool/main/libb/libbrahe/libbrahe_1.3.2.orig.tar.gz
- sha256: f102fed803ce1a75a1ee6bc56d2ddc0cedf9199e51d09a6e97fd3bec6f1ca98e（331,062 字节）
  - 与 `libbrahe_1.3.2-10.dsc` 的 Checksum-Sha256 完全一致（Format: 3.0 (quilt)，无 dfsg/改名 = pristine 上游原包）
  - 本地下载后 `shasum -a 256` 实测同值

### 为什么取 Debian pool 的 .orig.tar.gz（R39/PF7 官方托管例外，见 PR「补充说明」）
1. 作者域名 `coyotegulch.scottrobertladd.net` 经 DoH 查询返回 NXDOMAIN（`dns.google/resolve` Status=3），
   源码内引用的 `www.coyotegulch.com` 现由停放服务解析（HTTP 200 + `<script>...href="/lander"`），
   两处都没有可下载的 1.3.2 包；
2. Internet Archive 保存的官方页只给出当年的 `libbrahe-1.3.2.tar.gz`/`.zip` 相对链接，指向已停放的域名；
3. Debian 自 2011 年起维护该软件（Al Stone 引入），其 `debian/watch` 显式写作
   `https://people.debian.org/~eriberto/ FakeWatchNoUpstreamSiteForThisPackage-(\d\S+)\.gz`
   —— 即 Debian 自己声明「无上游站点」，pool 里的 `.orig.tar.gz` 是社区唯一在维护的上游原包镜像；
4. 本仓库对同类「上游已消失但 Debian 在维护」的包统一采用该形态。在 `upstream/main`
   （`62302961cd8f44677a64a6f146db595012e37686`）上实测取数：
   `git grep -l "deb.debian.org" upstream/main -- "archives/*/*/*/conandata.yml" | wc -l` = 237；
   同一行同时含 `deb.debian.org` 与 `orig.tar` 的（即本包所取形态）
   `git grep -l -e "deb.debian.org" --and -e "orig.tar" ... | wc -l` = 199，例如 `archives/a/a52dec/0.7.4/`；
5. PF7 源URL闸按实现口径把 `deb.debian.org` 一律判为「Debian 下游重打包源」，对 `.orig.tar.gz`
   没有例外，因此本包在建 PR 时保留该官方 URL 并对 PF7 命中留痕（见下）。

## 上游测试清单（R51 第一步：清点，附单位与取数命令）

计数字段：**程序**（可执行测试程序个数）与**值比对行**（程序自己打印的
`... = A (should be B)` 行数）分别统计，两者不混加。

| 取数命令 | 结果 |
| --- | --- |
| `grep -E '^bin_PROGRAMS' test/Makefile.am` | 6 个程序：brahe_test_prng/trig/rounding/gcflcm/fft/pretty |
| `grep -c 'check_PROGRAMS\|TESTS\|\.log:' test/Makefile.am` | 0（1.3.2 无 automake check 机制，`make check` 不执行任何用例） |
| `find . -name 'tests*' -o -name '*ctest*'` | 无 tests/ 目录、无 CTest 注册 |
| 执行后 `grep -E '=\s*-?[0-9.]+ \(should be' \| wc -l` | 39 条值比对行（rounding 26 + gcflcm 13） |
| 程序自证行 | `brahe_test_gcflcm`: `found 0 error(s)`；`brahe_test_fft`: `Good data... success!` |

上游可运行入口 = 6 个程序；`brahe_test_prng/trig/pretty` 只打印表格/渲染结果，
自身不给出 pass/fail 结论（无断言、无退出码判定），配方按「退出码 0 且输出内无
`ERROR`/`wrong data` 且值比对行全部一致」判定。

## 编译步骤

```sh
# 探索构建（设备 ws/tmp，与 conan ohos-aarch64 profile 同环境）
umask 022
export PATH="$HOME/usr/local/bin:/data/service/hnp/bin:$PATH"
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib
export CC=/data/service/hnp/bin/clang
export CONFIG_SHELL=/bin/sh SHELL=/bin/sh TMPDIR=<任务私有 tmp>

tar xzf libbrahe_1.3.2.orig.tar.gz && cd libbrahe-1.3.2
# 应用 0001..0004（补丁前实测：config.guess rc=1 "unable to guess system type"，
# config.sub aarch64-unknown-linux-ohos rc=1 "Invalid configuration"）
./config.guess      # -> aarch64-unknown-linux-ohos（rc=0）
./config.sub aarch64-unknown-linux-ohos   # -> 原样回显（rc=0）
./configure --prefix=<tmp>/pfx            # rc=0
make -j2                                   # rc=0
make install                               # rc=0（配方内为 make install SUBDIRS=src）
LD_LIBRARY_PATH=src/.libs ./test/brahe_test_*   # 6 个全部 rc=0
```

配方 `conan create` 走同一套补丁与参数；W3 由 finish 内嵌的 conan create 真实执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type`（configure rc=1） | 随包 config.guess 时间戳 2009-12-30，`uname -s` 返回 `HarmonyOS` 不在 GNU config 已知系统列表内 | 补丁 0001：在 `case "${UNAME_MACHINE}:${UNAME_SYSTEM}:..." in` 顶部加 `*:HarmonyOS:*:*) echo "${UNAME_MACHINE}-unknown-linux-ohos" ; exit 0`。E007/E160 规定的三元组路线，不用 `--build/--host`（E007 forbid_1、E011 forbid_1） |
| 2 | 官方一键补丁 `scripts/patch-autotools-ohos.pl` 对本包无效 | 该脚本按新版 config.guess 结构插入 `GUESS=${MACHINE}-...` 赋值，而 2009 版每个 case 分支必须自行 `echo ... ; exit 0`（case 起于 `config.guess:145`，Linux 匹配只有 `arm*:Linux:*:*)`(875)、`x86_64:Linux:*:*)`(974) 这类机器限定分支，无 aarch64 条目、也无通配 `*:Linux:*:*)`）；config.sub 需要的 `android-linux`、OS 白名单位、`linux-uclibc*- )` 三处锚点在 2010 版中计数均为 0 → 实测 `Done. cg=1 sub=0 change(s)`、`Score: 1/5`、rc=1，复跑 `sh config.guess` 仍报 unable to guess（取证回执 `task-data/.../refs/perl-probe-20260918-134200.log`，sha256 `e6e320db44…`） | 不修改框架脚本；按同一目标三元组手写 0001、0002 两处最小补丁（新增知识候选，见 `knowledge/drafts/DRAFT-libbrahe-1.3.2-config-guess-vintage.{kv,md}`） |
| 3 | `config.sub: Invalid configuration 'aarch64-unknown-linux-ohos'` | config.sub 2010-01-22 不认 `linux-ohos` 组合，把 `aarch64-unknown-linux` 当机器名而失败（同 `archives/a/a52dec` 的 aarch64 情形） | 补丁 0002：在「# Separate what the user gave into CPU-COMPANY…」之前插入 early-exit 直通块（`aarch64/arm/armv7/x86_64-*-linux-ohos`）。`host_os` 规范化为 `linux-ohos` 后，autoconf/libtool 的 `linux*)` 分支照常命中，实测 configure rc=0 |
| 4 | `./config.status: line 794: ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | E011：configure 的 config.status 段用 `umask 077` 建临时目录，HMDFS 把目录属主映射为 20001006 而进程 UID 为 20020083，0700/02700 目录对自己不可写 | 补丁 0003：configure 内 2 处 `umask 077` → `umask 022`（mktemp 路径与 mkdir 回退路径各 1 处，只改 1 处会在回退路径复发） |
| 5 | `make install` 失败：`bash: /libtool: No such file or directory`、`shell-init: error retrieving current directory: getcwd: ...` | E386：conan ohos-aarch64 profile 的 buildenv 把 CONFIG_SHELL/SHELL 设为 `/data/service/hnp/bin/bash`，该 bash 在 HMDFS 构建目录内 `pwd` 即失败（实测 rc=1 并打印 getcwd 诊断），libtool 变量拼接因此丢掉路径 | 配方 generate() 末尾用 `Environment()` 重新声明 `CONFIG_SHELL=SHELL=/bin/sh`（能力实测：`/bin/sh -c pwd` 在构建目录内 rc=0 且无任何诊断输出），在 conanbuild 之后生效；实测 install rc=0 |
| 6 | 上游测试程序与库的安装名不一致风险 | `src/Makefile.am` 传 `-release $(GENERIC_RELEASE)`，安装名是 `libbrahe-1.3.so.3.0.1`；实测 libtool 同时生成 `libbrahe.so`/`libbrahe.a`/`libbrahe.la` 开发名，`-lbrahe`（含静态模式，libtool 解析到 `src/.libs/libbrahe.a`）与消费者链接均正常 | 不改上游版本命名（与 Debian 现维护的 soname 保持一致），配方按 `cpp_info.libs = ["brahe"]` 声明 |
| 7 | `brahe_test_rounding` 有 1 条值比对不成立：`sigdig(-pi,8) = -3.14159270 (should be 3.14159270)` | 上游测试源码笔误：调用的是 `brahe_sigdig(-pi,8)`，打印的期望值漏了负号；`src/rounding.c:90` 的实现是 `round(x*f)/f`，按设计保号。在 macOS（Apple clang，非 OHOS）用同一份源码原生编译运行，得到完全相同的 39 条比对与同 1 条不匹配 → 与本平台无关 | 补丁 0004 只把该期望值字面量补上负号（不改任何断言逻辑、不放宽判定），并在本笔记与 PR 正文里保留补丁前的双平台复现证据。若评审认为不应触碰上游测试，可撤掉 0004 并按「6 执行 / 38 一致 / 1 上游期望值笔误」口径复核 |
| 8 | 上游 `libbrahe.pc.in` 与 pkg-config | `.pc` 里 `Libs: -L${libdir} -l@GENERIC_LIBRARY_NAME` 展开成 `-llibbrahe`（多了 lib 前缀），且顶层 Makefile.am 根本不安装该文件 | 不新增打包 .pc（与上游/Debian 行为一致），消费者通过 Conan 的 CMakeDeps/PkgConfigDeps 获得正确链接信息；配方 `set_property("pkg_config_name", "libbrahe")` 供下游生成器使用 |
| 9 | 第二轮 `conan create` 后 conan-verify L5 报 `产物与基线有差异: +0 -0 ~1（lib/libbrahe.a）`，`finish` 随之 rc=1（失败步骤 step8） | 每轮验证使用随机命名的任务私有 CONAN_HOME（上一轮 `libbrahe-ewk78svv`，本轮 `libbrahe-skbcb2io`），归档成员路径与 build-id 被写进 `libbrahe.a`；源码、补丁、配方与编译选项逐字未变，属跨轮缓存路径差异而非制品回归（与 mpir、libnoise 实测同型，工具自身的 L5 提示即此情形） | 按 L5 既定口径删除 `reports/baseline.json` 重立基线（语义等同首轮），并在最终 HEAD 上只做一轮正式验证后不再改 HEAD；差异原因即本行所述，不做「基线随轮漂移」的连续放行 |
| 10 | conan-verify G0 命中知识 E490 并给出「已知风险 E490 未在配方中处理」告警（Autotools helper 需可执行位，HMDFS 上可能因权限归一化失败） | E490 面向「解包后脚本丢执行位」的场景；本包实测两处都不成立：探索树 `ls -l` 显示 configure/config.guess/config.sub/install-sh/missing/depcomp/ltmain.sh 均为 `-rwxrwx---`，且 conan 直接以绝对路径执行 `"<build>/configure" --…` 成功（rc=0），`make`/`make install` 亦未出现 permission denied | 不额外加 chmod 步骤（E046：HMDFS 上 chmod 语义不可靠，且实测无缺口可补），如实披露该告警与判定依据，不以「G0 PASS」标签代替说明 |

## 源码修改

4 个补丁，全部落在 `patches/`，均由 `diff -u` 从「pristine 原包 vs 设备探索构建树」生成，
逐文件哈希绑定；上游仅这 4 个文件被改动（其余 60 个文件字节级一致，已逐文件比对）。

| 补丁 | 文件 | 内容 | sha256 |
| --- | --- | --- | --- |
| 0001-config.guess-harmonyos-triplet.patch | config.guess | +5 行 HarmonyOS 分支，输出 `aarch64-unknown-linux-ohos` | 201c2b6354bf3257c1e2c7a7085324b7ac56e2fbb866b6ef22da1597dcf212df |
| 0002-config.sub-ohos-triplet.patch | config.sub | +8 行 `*-linux-ohos` 直通块 | d92646ba0e88729636d784450e74f3792d70c01801f0a89f1015b20cbdf011ce |
| 0003-configure-umask-022-hmdfs.patch | configure | 2 处 `umask 077` → `umask 022` | 5f8d05b68b5eefc797e5a331b00dd2e4670e5192c0010fb05c446bedcc329ce0 |
| 0004-test-rounding-expectation-sign.patch | test/brahe_test_rounding.c | 1 行期望值字面量补负号 | 8e9614bb397727b6abec96ae92fd4e50326927537e8f5b361d283bb34de4a707 |

层级口径（build-systems.md §3.6）：0001、0002 改的是 autoconf 辅助脚本（E007 指定做法），
0003 改 configure 本身 = 优先级 ②（configure.ac 里没有这段，umask 来自 autoconf m4，
无法通过 ① 表达），0004 改源文件 = 优先级 ①。三者都不含 `__OHOS__` 平台宏（PF5/R8）。

## 依赖版本

零外部依赖（W0 实测：`dependencies_known=true`、`dependencies={}`、
`version_occupancy=missing`，即制品仓无同名版本次、配方未被占用）。
源码只包含 stdlib/stdio/string/stddef/math/limits/unistd/fcntl/time/stdbool/stdint；
`test/Makefile.am` 额外 `-lm -lrt`：设备 sysroot
`usr/lib/aarch64-linux-ohos/` 内 `libm.a`、`librt.a` 均在（`-lrt` 静态命中，实测链接通过），
`src/` 本身不需要 librt。配方以 `cpp_info.system_libs = ["m"]` 声明数学库。

## 验证结果

```bash
# 1) 上游 6 个测试程序（配方 build() 内执行，命令逐条写进 conan create 日志）
LD_LIBRARY_PATH=".../src/.libs" ".../test/brahe_test_prng"      # rc=0
...                                                            # trig/rounding/gcflcm/fft/pretty
# 汇总标记：HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"autotools", ...}
# 39 条值比对全部一致；gcflcm 自报 found 0 error(s)；fft 打印 Good data... success!

# 2) 安装包消费者测试（test_package，conan create 阶段执行）
# ./test_libbrahe -> libbrahe consumer test: 43 checks, 0 failures
```

门禁口径（如实，不用 PASS 标签代替事实）：conan-verify 的 G0/G1/G2/G3/G4/L5 为真实通过；
L2 记为 passed 但明细是「无 bin/ 目录（纯库包，跳过 smoke test）」，等同 W3 的 `L2_RESULT=skip`；
L4 记为 passed 而明细是「无可扫描的 ELF 文件」（静态包无 .so 可扫）；G0 带 E490 告警（见问题表第 10 行）。
消费者测试的实质执行由 W3 的 L1a/L1b/L1e（含破坏性反向验证）证明。

设备探索构建实测：`configure rc=0`、`make -j2 rc=0`、`make install rc=0`、
6 个上游测试程序 `rc=0`（输出 4040/702/1639/413/62/733 字节，均在 task-data 日志内）。
正式 `conan create` 的逐条门禁与哈希绑定证据保存在协调端 `task-data/libbrahe-1.3.2/evidence/`；
逐条结果另写入 `reports/test-report.md`，该文件按仓库审查规则 19（`test-report` 属 PR 禁止文件）
只保留在设备工作树、不进本 PR，可核对的事实以本笔记与 PR 正文为准。

## 交付物

包内布局（`shared=False` 默认静态）：

| 路径 | 说明 |
| --- | --- |
| `include/libbrahe/mathtools.h`、`include/libbrahe/prng.h` | 上游 `library_include_HEADERS` 原样安装 |
| `lib/libbrahe.a`（shared=True 时 `lib/libbrahe-1.3.so.3.0.1` + `libbrahe.so`） | 上游 libtool 命名 |
| `licenses/LicenseOpenSource.txt`、`licenses/LicenseClosedSource.txt` | 双许可条款 |
| 不打包 `bin/brahe_test_*` | 上游 6 个测试程序按 `make install SUBDIRS=src` 排除（见下） |
| 删除 `lib/*.la` | libtool 包装文件在 Conan 包内无意义（与 `archives/a/a52dec` 同口径） |

## 注意事项

- **不打包上游测试程序**：`test/` 内 6 个程序是上游自校验表格（多数无断言），不是库的交付物；
  配方仍然编译并在 build() 内实跑，用于 R51 上游测试证据。这样包内没有 `bin/`，
  因此按 R38/L0k 属纯库包、不需要 `commands.json`（PF8 同口径）。
- `brahe_moving_average()` 上游实现把累加写进未初始化的 `result[i]`
  （`result = malloc(...)` 后直接 `result[i] += data[x]`），读取未定义值。
  本包未对该函数建立断言，只如实记录；修它属于改上游算法，超出适配范围。
- `shared=True` 时 soname 为 `libbrahe-1.3.so.3`（上游 `-release 1.3` 的结果），
  与 Debian 的 `libbrahe-1.3-3` 包命名一致；不要期望 `libbrahe.so.0`。
- PF7：conandata.yml 与版本级 manifest.yaml 的源 URL 各命中一次「Debian 下游重打包源」，
  属上文已论证的官方托管例外，留痕与证据见 PR 正文；不使用 `OHC_PREFLIGHT=0`。
- PF9：新包的软件级 `README.md`/`manifest.yaml` 是 4 段路径，会被 PF9 的 5 段口径误报，
  与 PF8 的「commands.json 必须在软件级」互斥（框架已知缺陷），同样按留痕处理。
