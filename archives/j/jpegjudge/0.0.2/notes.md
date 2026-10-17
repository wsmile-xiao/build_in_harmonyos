# jpegjudge 0.0.2 适配笔记

## 编译环境

- 构建系统: autotools（**随包发布的 autoconf 2.13 `configure` + automake 1.4 `Makefile.in`**，不重新 autoreconf）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，profile `ohos-aarch64`：os=OHOS / os.version=6.0 / arch=armv8 / libc++）
- Conan: 2.29.1（OHOS 适配版）；`CONAN_HOME=$HOME/tmp/ch/home-jpegjudge`
- 构建主机: B 机（HarmonyOS aarch64）；worktree `~/qzy/主理-33-jpegjudge-0.0.2`；基线 `origin/main` = `48d9cee684`
- 状态: built（本地验证通过，未 upload）

## 源码与 W0 依赖实测

| 项 | 实测值 |
|---|---|
| 源 URL | `https://oldhome.schmorp.de/marc/data/judge-0.0.2.tar.gz`（上游主页页面上唯一下载链接 `data/judge-0.0.2.tar.gz`） |
| 实物大小 | 39079 B |
| 实物 sha256 | `e43d15db51a5bf6f1460df0cdf6e0ea183942a17a83b0e0313102129ba0d4725`（设备 `sha256sum` 实物所得） |
| 与 Debian 池件的关系 | `jpegjudge_0.0.2.orig.tar.gz`（39320 B / `2e1faf34ef00116dd9a2542e095259fb0e8abc5ee0f9eecec81770e4b1cc99e7`）解包后 `diff -r` **零差异**、21 个文件清单一致；但 `deb.debian.org` 属 PF7/R39 的「Debian 下游重打包源」黑名单（`scripts/ohc/preflight.py:361-381` 实测该域名在 `_PF7_DEBIAN_HOSTS` 内），故 conandata 取上游官方 URL。sha256 不同只因重新打包。 |

**W0 依赖发布性（精确引用 `libjpeg/10`，不带 user/channel，与归档内先例 `archives/j/jpeginfo/1.7.1` 同形态）**

| # | 命令 | 退出码 | 结论 |
|---|---|---|---|
| 1 | `conan download libjpeg/10 -r=ohpcd --only-recipe` | 0 | 配方在仓，revision `b07f96290a88f086bad3124186e29fc7` |
| 2 | `conan install --requires=libjpeg/10 --build=never -pr:h=ohos-aarch64 -pr:b=ohos-aarch64` | 0 | 二进制 `21b17f8b2bc0e9511e276e3d57a23893067cefe5` 真实下载，输出 `Package installed` + `Install finished successfully` |

证据文件（设备侧）：`~/tmp/uc2/z33-jpegjudge/w0-libjpeg-publication.log`。
未使用通配 `conan list` 判断（R35）。补充实测：该归档 `lib/` 下只有 `libjpeg.a`（静态制品，
符合 R26 与系统同名库不污染 `/lib` 的口径）；其 `jpeglib.h:729` 仍保留 `int trace_level;`，
故 `judge.c:43` 的 `cinfo.err->trace_level = 0;` **不需要**为新版 jpeglib 改动。

## 构建系统权威形态判定（回答「configure 与 Makefile.in 同时在盘，谁是权威」）

证据链（均为本机实测，非台账转述）：

1. `configure` 第 4 行：`# Generated automatically using autoconf version 2.13`。
2. 输入文件叫 **`configure.in`**（不是 `configure.ac`），且同盘有 `acconfig.h`、
   `config.h.bot`、`stamp-h.in` —— 全是 autoconf 2.13/autoheader 旧机制的配套物。
3. `Makefile.in` 由 automake 1.4 世代生成：`$(srcdir)/Makefile.in: Makefile.am
   configure.in $(ACLOCAL_M4)` 会回调 `$(AUTOMAKE) --foreign --include-deps Makefile`，
   `$(srcdir)/config.h.in: $(srcdir)/stamp-h.in` 会回调 `$(AUTOHEADER)`。
4. 包内 **无** `autogen.sh`、**无** `configure.ac`、**无** `config.guess`/`config.sub`
   （21 个文件全清单见「上游测试清点」）。

⇒ **权威 = 随包的 `configure` + `Makefile.in`**，不走 autoreconf：设备上是 autoconf 2.72，
`autoreconf` 需要先把 `configure.in` 改名、且新 autoconf 不再支持 `acconfig.h`/`config.h.bot`
这套 config.h 生成机制，重生成等于用新工具链覆盖包内既有生成物（本仓有「框架生成物覆盖
已写好的东西」事故先例）。实测直接用随包件可完整跑通 configure/make/install/check。

## configure 参数与安装形态

- 随包 `configure --help` 实测只接受 2.13 的目录选项（`--prefix/--exec-prefix/--bindir/
  --sbindir/--libexecdir/--datadir/--sysconfdir/--sharedstatedir/--localstatedir/--libdir/
  --includedir/--oldincludedir/--infodir/--mandir/--program-*/--build/--host/--target/--x-*`），
  未知选项走 `configure:379` 直接 `invalid option ... exit 1`。
- Conan `AutotoolsToolchain` 默认注入 `--datarootdir`（源码
  `autotoolstoolchain.py:358-364`）⇒ 与本包 configure 不兼容。
- 配方处置：`tc.configure_args = ["--prefix=/"]`（R1 参数最少化），
  `package()` 用 `autotools.install()`（= `make install DESTDIR=<package_folder>`）
  ⇒ 落盘 `bin/judge` 与 `man/man1/judge.1`。
- 不使用 `--host/--build/--target`（SKILL §4.1 native 编译禁令）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-verify` 的 L2 smoke 门禁判 `所有二进制文件均无法运行` → FAIL | `judge` 只实现 getopt 短选项 `-v/-h`，`--version`/`--help` 落入 `default` 分支 → `usage(argv[0], 2)` → exit 2；L2 先跑 `--version`、失败再跑 `--help`，两者都非 0 即判失败（`scripts/ohc/conan_verify.py:793-839`） | 按知识条目 **E503**（libubox/jshn 先例）在 `main()` 开头补 GNU 长选项，打印后返回 0；不改 `-v/-h` 既有语义 → `patches/0001-cli-long-options.patch` |
| 2 | 随包 configure 报 `invalid option` 并 exit 1 | Conan 默认注入 `--datarootdir`，autoconf 2.13 的 configure 不识别 | configure 参数收敛为只传 `--prefix=/`，安装靠 `DESTDIR` |
| 3 | `ohc-run.py init-build` / `build`（模式 A/B 两个探索入口）不可用 | 设备侧 `~/usr/local/bin/automake`（2026-09-23 23:42 落盘）的 shebang 指向 `/storage/Users/currentUser/usr/local/bin/perl`，该 perl **不存在** → `execve` 报 ENOENT；`scripts/ohc/check_env.py:24-33` 的 `except Exception:` 未绑定变量却在下一行 `str(e)` → **NameError** 崩掉整个 init-build | 本轮未修共享框架文件（越权）：改为手工完成探索（真实 configure/make/install/check + 真实行为探针），配方首稿以 `recipe-search` 推荐的 top1 骨架 `archives/j/jpeginfo/1.7.1/conanfile.py` 为底稿。证据 `~/tmp/uc2/z33-jpegjudge/init-build.log`。**已交主代理入表** |
| 4 | 补丁无法用 `refresh-patch --auto` 生成 | 该工具依赖 init-build 产出的 `.build-context-*` 与 `.orig/.work` 双轨目录（`scripts/ohc/refresh_patch.py:311-336`），而 init-build 因问题 3 崩溃 | 用 `difflib` 按 refresh-patch 同样的 `a/`、`b/` 前缀与 3 行上下文生成补丁（生成脚本 `~/tmp/uc2/z33-jpegjudge/make_longopts_patch.py`），并在 conan 的 G2 `conan create` 中由 `apply_conandata_patches` 真实应用验证 |
| 5 | `make check` / `make install` 日志里刷 `shell-init: error retrieving current directory: getcwd: cannot access parent directories` | HMDFS 下被 spawn 的 shell 取不到 cwd 的已知现象 | 非致命：实测 `make check` RC=0、`make install` RC=0 且产物齐全（`bin/judge`、`man/man1/judge.1`），未据此改配方 |

## 源码修改

补丁 `patches/0001-cli-long-options.patch`（`patch_type: portability`，改 1 个文件 `judge.c`）：

1. 新增 `#include <string.h>`（上游 `judge.c` 未包含它，原先隐式声明 `strcmp`）。
2. 在 `main()` 的 `int retcode = 0;` 之后、getopt 循环之前拦截两个信息性长选项：
   `--version` 打印 `judge version 0.0.2` 并 `return 0`；`--help` 走 `usage(argv[0], 0)`。
   只在 `argc == 2` 时拦截，不影响 `judge -b a.jpg b.jpg` 等正常使用形态。

补丁内不含任何平台宏（PF5 口径），改动是 CLI 接口补齐而非平台分支。

## 依赖版本

| 依赖 | 引用 | 说明 |
|---|---|---|
| libjpeg | `libjpeg/10` | IJG 参考实现 v10；本仓归档，静态 `libjpeg.a` |
| 构建工具 | clang 15.0.4 / GNU make 4.4.1（profile 提供） | 不 tool_requires autoconf/automake（随包生成物直接用） |

## 上游测试清点（R51，五维账本取数）

清点面 = 官方 tarball 实物解包树（`tar tzf` 全清单 21 个文件），
**未** 使用 `ci/tools/extract_upstream_tests.sh`（该脚本硬编码只读 `/tmp`，
设备上必失败、产出只有 `mkdir /tmp/...: Read-only file system`，不能当证据）。

| 探针命令 | 命中 |
|---|---|
| `tar tzf judge-0.0.2.tar.gz` | 21 个文件（无 test/、无 t/、无 spec/） |
| `find . -type d \( -name t -o -name tests -o -name test -o -name spec \)` | 0 |
| `grep -rlE "Test::More|use_ok\(|def test_|TEST_CASE|add_test\(|enable_testing"` | 0 文件 |
| `grep -nE "^(TESTS|check|check-am|installcheck)" Makefile.in` | `check-am: all-am`（323）、`check: check-am`（324）、`installcheck*` 空目标；**无 TESTS、无 check_PROGRAMS** |
| `grep -rn assert *.c` | 3 处，全部是 `judge.c` 自身运行期 `assert()`（不是测试用例） |

⇒ **N_static = 0**（上游无任何静态声明的测试）、**N_registered = 0**（构建系统里注册的可执行
测试用例为 0，只有一个 `check` 目标壳）、**N_executed = 0**（配方 `build()` 内真实执行
`make check`，RC=0、0 用例）、**未执行分类 = 0**（无「条件编译/缺资产/预期失败」可言，
因为分子分母都是 0）、**N_consumer = 1**（`test_package/test_jpegjudge.sh`，
括注 `N_assertion = 36`）。

上游确无自动化测试，本包**不声称**跑过任何不存在的 `make check` 用例；
消费者测试按下节真实设计。

## 消费者测试夹具（真实输入构造方式）

夹具由 IJG libjpeg **真实编码器**生成（`jpeg_set_defaults` + `jpeg_set_quality` +
`jpeg_write_scanlines`，`JCS_GRAYSCALE`，1x1 sampling），生成程序
`mkjpeg.c` 与产物均在设备侧 `~/tmp/uc2/z33-jpegjudge/`，以 base64 内联进
`test_package/conanfile.py`（不让 CI 依赖任何 Python 图像绑定）。

| 夹具名 | 尺寸 | 编码质量 | 像素内容 | 字节数 | sha256 |
|---|---|---|---|---|---|
| `hi_noise.jpg` | 32x32 | 90 | 轻度抖动（`(i%17)-8` 叠加 128） | 508 | `ebc4d549c880ec0814ed7feafcb10244764ae54faef1d9c560dab067238fd002` |
| `lo_noise.jpg` | 32x32 | 30 | 同上（同图不同质量） | 373 | `c6e7f99bcb8d330705fbc58142922d92d2a3d0435a0e3f4382db114a0ac7067a` |
| `flat.jpg` | 32x32 | 90 | 纯色 128 | 342 | `e1c1a7513c550a7da8930c38b63d2ff368196ae39473b02adbfbf6ba7f2ec7ff` |
| `tiny_4x4.jpg` | 4x4 | 90 | 轻度抖动（宽度不足一个 8x8 块） | 337 | `8e43fdc8a173f6729d63f86f7a423d7a81e7dfd204d86853d4e5babe370990bc` |

测试时另在夹具目录现场派生两类坏输入：`head -c 400 hi_noise.jpg > case_trunc.jpg`
（截断件）、`printf 'NOT A JPEG FILE ...' > case_notjpeg.jpg`（非 JPEG 文本），
不往仓库里塞二进制垃圾。

## 验证结果

```bash
# 探索期（设备手工，真实数值来源）
$ ./judge -v                                  → judge version 0.0.2                 RC=0
$ ./judge hi_noise.jpg                        → hi_noise.jpg: 424                   RC=0
$ ./judge lo_noise.jpg                        → lo_noise.jpg: 293                   RC=0
$ ./judge flat.jpg                            → flat.jpg:   0                       RC=0
$ ./judge tiny_4x4.jpg                        → tiny_4x4.jpg: 1000                  RC=0
$ ./judge case_trunc.jpg                      → jpeg read error / case_trunc.jpg: 226  RC=0
$ ./judge case_notjpeg.jpg                    → Not a JPEG file: starts with 0x4e 0x4f  RC=1
$ ./judge no_such_file.jpg                    → No such file or directory           RC=1
$ ./judge                                     → Usage: ...                          RC=2
$ ./judge -Z                                  → unrecognized option: Z + Usage      RC=2
$ ./judge -b hi.jpg lo.jpg                    → 424 / 293（仅数字，无文件名）        RC=0
$ ./judge - < hi_noise.jpg                    → -: 424                              RC=0
# 打补丁后新增的两个长选项
$ ./judge --version                           → judge version 0.0.2                 RC=0
$ ./judge --help                              → Usage: judge [ -vb ] file ...       RC=0
# 消费者测试套件（36 条断言）
$ bash test_jpegjudge.sh <judge> <fixture-dir> → SUMMARY pass=36 fail=0             RC=0
```

（门禁判决行 G0-G4 / L0-L5 / W3 / graph validate 的原文实测值由
`finish` 与 `conan-verify` 落进 `reports/`，本文件只写口径与命令。）

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 配方（application、`--prefix=/`、build() 内真实执行 make 与 make check） |
| `conandata.yml` | 官方源 URL + 实物 sha256 + 补丁声明 |
| `patches/0001-cli-long-options.patch` | GNU 长选项补齐（E503） |
| `test_package/conanfile.py` | 落夹具 + 真运行 judge |
| `test_package/test_jpegjudge.sh` | 36 条行为断言（消费者测试程序，N_consumer=1） |
| `test_package/MANIFEST.yml` | 上游 0 用例声明 + 消费者测试声明（CI L0e） |
| `../commands.json` | 软件级 CLI 声明（R38/L0k，`name=jpegjudge`、`versions["0.0.2"].ref="jpegjudge/0.0.2"`） |
| `../README.md`、`../manifest.yaml` | 软件级说明与版本索引 |

## 注意事项

1. **安装的可执行文件名是 `judge`，不是 `jpegjudge`**（上游 `Makefile.am`：
   `bin_PROGRAMS = judge`）。`commands.json` 的 `name` 按 PF8 口径必须等于包名
   `jpegjudge`，两者差异已写进 README 与 commands.json 描述。
2. 上游 man 页自陈指示值「非线性、可以更好」，且算法是 1998 年「盯直方图 10 分钟」
   得出的 ⇒ 数值只做**相对比较/判重**，不宜当绝对质量分。
3. **上游缺陷（未修，只记录）**：图像宽度不足 8px 时 `process_blocks()` 的
   `xoff = (width/8 - 1)*8` 为负，累加器 `pixels` 保持 0，`estimate_quality()`
   做 `histogram*1000/pixels` 整数除零。x86 上会 SIGFPE，**AArch64 整数除零不陷入**
   （结果为 0）⇒ 本包实测输出 1000 且退出码 0。消费者测试 B9/B10 把这个平台事实
   钉成断言，将来上游或工具链变了会立刻暴露。未据此改上游源码（超出本任务范围）。
4. `judge.txt` 规则需要 `man -T ascii`，但它不在 `all` 目标里（`EXTRA_DIST` 项），
   实测 `make`/`make install` 不会触发。
5. 上游 README 让「See file INSTALL」，而包内**没有** INSTALL 文件（2.13 的
   automake `foreign` 选项不装 INSTALL）——只是文档瑕疵，不影响构建。
6. `finish` 的 step5b `check_knowledge_gap` 可能因 `knowledge_gained` 行的
   `ref:` 判据写法和全仓存量形态冲突而显红（本仓实测 92.5% 存量包同为红），
   属框架判据与存量的矛盾，不在本包改形（披露见 `手册/04-交付门禁.md` §11.5）。
## 路径判定与知识库声明（3+2）

- **适配路径**：A（配方适配 + 上游 CLI 缺口按既有先例 E503 处置；未发现需要新建知识条目的 OHOS 特有行为差异）
- **使用知识库**：E503（libubox/jshn 先例：CLI 只实现 getopt 短选项时，`--version`/`--help` 落入 `default` 分支 `exit 2`，被 conan-verify 的 L2 smoke 判成「所有二进制文件均无法运行」）——`patches/0001-cli-long-options.patch` 即按该先例口径处置；另逐条对照框架条款 PF5/PF7/PF8/R1/R26/R36/R37/R38/R39/R51/L0e/L0g；配方首稿取 `recipe-search` top1 骨架 `archives/j/jpeginfo/1.7.1/conanfile.py`。
- **知识库扩展**：无（本轮新撞到的两点——L0g 硬编码 remote 判据**计数含注释**、HMDFS 下 spawn shell 的 `getcwd` 告警——都是本仓工具/环境既有行为，不是 OHOS 新机制）。**B 判定待主代理定案**，本包不自建 Issue、不起【知识库扩展】前缀。
- **关联 Issue**：待创建（PRE_CREATE）；若主代理判定升 B，再由主代理执行 `$P issue jpegjudge 0.0.2 --mechanism "..."`。

## 上游测试用例修改说明（补丁逐项，§10 口径）

| 项 | 内容 |
|---|---|
| 原文件 | `judge.c`（官方 tarball 21 个文件中**唯一**被改者；补丁 `patches/0001-cli-long-options.patch`，`patch_type: portability`，`conandata.yml` 已声明描述） |
| 原因 | 上游 `main()` 只用 `getopt(argc, argv, "vbh")` 处理短选项，`--version`/`--help` 落 `default` → `usage(argv[0], 2)` → `exit 2`；而 conan 的 L2 smoke 门禁先试 `--version` 再试 `--help`，两者非 0 即判「所有二进制文件均无法运行」→ `conan-verify` FAIL。属上游 CLI 接口缺口，非 OHOS 平台问题。 |
| 内容 | ①补 `#include <string.h>`（上游隐式声明 `strcmp`）；②在 `int retcode = 0;` 之后、getopt 循环之前，仅在 `argc == 2` 时拦截 `--version`（打印 `judge version 0.0.2` 后 `return 0`）与 `--help`（走 `usage(argv[0], 0)`）。不含任何平台宏（PF5 口径），不改 `-v/-h/-b` 既有语义。 |
| 结果 | W3 `L2_RESULT=pass: judge --version OK`、`L4_RESULT=pass: patches clean`；消费者测试 A1–A9 把长短选项与退出码契约钉成断言（`-v`/`-h` 未回归，见 `consumer-probe.log`），`make check` RC=0。 |

## 已知限制

1. 安装的可执行文件名是 `judge`（上游 `bin_PROGRAMS = judge`），包名是 `jpegjudge`：见「注意事项」1。
2. 上游指示值只做**相对比较/判重**，不是绝对质量分：见「注意事项」2。
3. 宽度不足 8px 时上游有整数除零（`estimate_quality()` 除 `pixels==0`）；AArch64 不陷入故实测输出 1000 / RC=0，x86 上会 SIGFPE——未修上游，只由消费者测试 B9/B10 钉成断言：见「注意事项」3。
4. `judge.txt` 需 `man -T ascii`，属 `EXTRA_DIST` 不在 `all` 目标内，本包不生成。
5. 上游 README 指向的 `INSTALL` 文件在包内不存在（文档瑕疵）。

## 门禁判决（本轮实测原文，与 `reports/` 同源）

- **conan-verify**（`finish` step4 重跑，2026-09-25 03:58）：`G1: PASS` / `G0: PASS` / `G2: PASS` / `G3: PASS` / `G4: 产物完整性检查` → 末行 `✅ 配方验证通过: jpegjudge 0.0.2`。首轮独立日志 `conan-verify-1.log`（03:50）判决同为全 PASS。
- **W3 本地 CI 模拟**（step5，真跑 `ci/conan/build_and_test.sh`）：`✅ W3 本地 CI 模拟通过`；`reports/w3-local-ci.log` 31256 B、mtime `03:59:05` 晚于同轮 `conan-create.log` 的 `03:58:44`、md5 `711cc6f0900a3211189f7df4b553ed9b` ≠ `conan-create.log` 的 `ab8d4ddb013ba7f844b1d40f7e056099`（四条同判成立）。判决行原文：`G0_RESULT=pass`、`KC_RESULT=pass`、`JC_RESULT=pass`、`L0_RESULT=pass: all checks passed`、`L1_RESULT=pass: upstream tests + test_package executed`、`L2_RESULT=pass: judge --version OK`、`L4_RESULT=pass: patches clean`、`L5_RESULT=pass: bin/ has content`、`Success: 1`、`Pass rate: 100.0% (1/1)`。
- **知识图谱**：`python3 scripts/ohc-run.py graph validate` → `✅ All checks passed (169 warnings)`（`.kv` 540 / `.md` 540 / index 540；169 条 warning 与 `[C14] 编号空洞 E429/E479` 均属全仓存量，非本包引入）。
- **W2 PR 原子性**（step9）：`✅ 仅含配方变更 (11 文件)，无框架文件`。
- **消费者测试独立复跑**（夹具二进制移除后）：`conan test archives/j/jpegjudge/0.0.2/test_package jpegjudge/0.0.2@ohpcd/stable -pr:h=… -pr:b=…` → RC=0、`SUMMARY pass=36 fail=0`。
- **`finish` 未清零（`finish-2.log` 第 100 行原文：`失败步骤: step5b, step8`）**：真正判红的是 step5b `check_knowledge_gap` 与 step8 `gen_summary`；**step6 `finalize-archive` 只出警告**，它报缺 release/debug tar.gz 与 `packaging/`、`reports/test-report.md`、`.staging-verified`——三者逐条 `git check-ignore` 均命中（造出来也不进 PR），对照本仓已合入的 `archives/j/jpeginfo/1.7.1/`（只有 `conandata.yml`/`conanfile.py`/`manifest.yaml`/`notes.md`/`patches/`/`test_package/` 六项），这几项不属现行交付物形态；step8 `gen_summary 失败: str object has no attribute append` 是框架脚本自身异常。两者已如实披露，是否需补由主代理定案。

## 测试夹具形态变更（第二棒，2026-09-25 04:00 后）

4 个 `.jpg` 在抢救提交 `c4579f53e8` 里曾被一并收进仓库。经核：`test_package/conanfile.py` 的 `build()` 已把同批字节以 base64 内联并在构建时逐文件落盘（sha256 与上表逐条一致），仓库内的二进制副本属**构建副产物**，故在 `5669581e0a` 中移除，PR diff 不再携带二进制文件。
否证/证实：移除后独立执行 `conan test` → RC=0、`SUMMARY pass=36 fail=0`，且 `build()` 重新落盘的文件字节数与 sha256 与上表**完全相同**。
声明：这 4 个 JPEG 是本包**自造的合成输入夹具**，不是上游测试资产（上游 0 用例，见「上游测试清点」），也不是 vendored 第三方文件。

## 未执行 / 未覆盖的检查

- 未跑 `ohc-run.py build` / `init-build` 一键探索：设备侧 `~/usr/local/bin/automake` 的 shebang 指向不存在的 perl，`scripts/ohc/check_env.py` 吞异常反而 `NameError` 崩掉入口（「遇到的问题」3，证据 `init-build.log`）；探索改为手工真实命令，已交主代理入表。
- 未跑 `ci/tools/extract_upstream_tests.sh`：该脚本硬编码只读 `/tmp`，设备上必失败，其 log 不构成「上游 0 测试」的证据。上游清点改为手工执行，原始输出落 `~/tmp/uc2/z33-jpegjudge/upstream-test-inventory.txt`（本文件「上游测试清点」一节即其摘要）。
- 未 `upload`、未发布制品：verify 的「可标记 status: published」只是门禁给出的建议，不代表已发布。
- 未做跨机交叉构建：本 PR 全部产物出自 B 机单台 worktree（worktree 不跨机共享）。
- 未做多 arch / `-m32`、未做 ASAN/fuzz/压力测试；L4 只覆盖 checksec 静态面。
- 未修上游整数除零与 `EXTRA_DIST` 文档瑕疵（见「已知限制」3–5），超出本任务范围。
- 未建知识库 Issue、未起【知识库扩展】前缀：B 判定待主代理定案。

---

**编译结束**: 2026-09-25 03:58
**最终状态**: built
