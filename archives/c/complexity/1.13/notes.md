# complexity 1.13 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译器: clang 15 / clang++ (HarmonyOS PC 真机工具链)
- 状态: built (待真机预检确认后由 HMBS 更新)
- 认领身份: GitCode 用户名 `gcw_6a3w2yXz`，队伍 `来都来了`

## 上游信息
- 上游: GNU complexity 1.13，https://www.gnu.org/software/complexity/
- 源码包: https://ftp.gnu.org/gnu/complexity/complexity-1.13.tar.xz
- sha256: `80a625a87ee7c17fed02fb39482a7946fc757f10d8a4ffddc5372b4c4b739e67`
  （456312 字节，已实际下载核对；CI 会自动追加 GNU 镜像 fallback）
- 构建系统: GNU autotools；gnulib 源码内嵌于 `lib/`，无 Conan 依赖

## 上游测试清点
- `tests/Makefile.am` 声明 `TESTS=complexity.test`（唯一上游测试用例）
- `tests/complexity.test`: sh 脚本，先用刚构建的 `src/complexity` 对 `src/*.c`
  全量打分并要求输出同时含 Complexity Scores / Complexity Histogram 双标题，
  再以 `-t0` 对样本打分并与脚本内嵌期望表 `cmp`
- `tests/sample.c`: 参照输入（5 个已标注期望分值的 C 函数体）
- 证伪说明: 桩二进制（无输出/空输出）必然因标题缺失或 cmp 不一致而 exit 1，
  不存在静默跳过路径；参照文件非空（sample.c，5 个函数）
- `unifdef` 仅在显式传 `--unifdef` 选项时才 popen 调用，默认打分走 `fopen`，
  无隐性运行时依赖

## 编译步骤

1. `get()` 解包官方源码包
2. `AutotoolsToolchain` 生成，附加 `--build/--host=aarch64-unknown-linux-gnu`
   与 `SHELL=<bash>`（见下表）
3. `configure && make -j1`
4. `make check`（上游 automake 套件），解析 `tests/test-suite.log`
   的 `# TOTAL/# PASS` 计数并输出 `HMBS_UPSTREAM_TEST_RESULT` 标记
5. 手动拷贝安装（不调 `make install`），产物 `bin/complexity` + `bin/cx-vs-mc` + `COPYING→licenses/`
6. test_package: `test_complexity.sh <pkg>/bin/complexity`（2 个真实断言），
   输出 `HMBS_TEST_PACKAGE_RESULT` 标记

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 硬依赖 GNU autogen libopts | `configure.ac` 中 `test -z "${ao_LIBS}"` 直接 `AC_ERROR`；真机预检实测报 `autoopts-config: command not found` + `libopts was not found`，确认真机无系统级 libopts；完整 autogen 构建又需 guile/libxml，太重 | 在配方内私有构建最小 libopts 兼容层（`libopts_shim/`：autogen-5.18.16 的 `autoopts/options.h` 原样 vendor 保 ABI + 手写 getopt_long 实现，仅覆盖 complexity 生成的 opts.c 实际用到的 optionProcess/Usage/PagedUsage/PrintVersion/NumericVal/StackArg/LoadOpt），build() 先编出 `libopts.a`，再用编译器直接产出可执行的 `autoopts-config`（绕开只读文件系统 chmod=0 限制），前置到 PATH 后再 configure；不新增 Conan 依赖，shim 不安装进包 |
| 2 | config.guess 在受限文件系统上探测失败风险 (E007) | HMDFS 上编译运行探测程序可能被拒绝 | 显式传递 `--build/--host` triplet 绕过 config.guess（同已合入的 cflow 1.0.0 做法），不打补丁 |
| 3 | configure 与 automake test-driver 的 bash 依赖 | OHOS `/bin/sh` 非 bash | `SHELL` 指向 bash（同已合入的 gnu-which 2.25 做法） |
| 4 | configure 含标准 `umask 077 && mktemp` 临时目录逻辑 + 只读 /tmp 诊断 | HMDFS 能力差异；预检报 `[readonly_tmp]` 且 `HMBS_CAP_CHMOD=0` | 配方自身只写 `build_folder/private-libopts`（不碰 /tmp）；`autoopts-config` 用编译器直接产出可执行文件而不依赖 chmod；configure 内 `autogen -MF/tmp/...` 探测因 autogen 缺失直接走 false 分支，不写 /tmp；其余复用 hmbs 注入的独立 TMPDIR |
| 5 | 真机 `config.status: can't create ./confR2fw7G/subs1.awk: Permission denied`（2026-09-07 预检，失败阶段 compile） | HMDFS 上 `mktemp -d ./confXXXXXX` 建出的 0700 目录后续不可写（平台诊断 `unsafe_local_mktemp`，能力 `local_mktemp=1/chmod=0`；知识 E011 同源）；`TMPDIR` 无法覆盖该显式本地路径分支 | 最小适配复用平台能力：①沿用注入的 `TMPDIR/TMP/TEMP`（缺失才回退 `build_folder/tmp`）；②新增编译型 `mktemp` 垫片（与 `autoopts-config` 同目录、前置 PATH，免 chmod）：仅当 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 且 `HMBS_MKTEMP_SHIM_ACTIVE=1`（`configure()` 前后开关）时对含 `confXXXXXX` 参数返回失败，触发 Autoconf 原生 `mkdir ./conf$-$RANDOM` 回退，其余调用 `execv` 委派真实 mktemp（保 `config.guess $TMPDIR/cgXXXXXX` 等可用）；不改 umask、不动上游测试 |

| 7 | 真机 `options.h:68 typedef _Bool` 硬错误 + `AO_TEMPLATE_VERSION` 错配（第 3 轮，configure 已过、卡 `autotools.make`） | shim 头为 42:1:17（172033）而上游 opts.h 要 42:2:17（172034，`#error+Choke Me` 连锁出 20 个 INDEX_OPT 未声明）；`_Bool` 回退 typedef 在新 clang（bool 关键字化）下非法 | 头文件最小对齐：版本号三处改为 172034/42:2:17/42.2，`HAVE_STDBOOL_H` 分支改为恒走 `<stdbool.h>`（`|| 1`），布局不动；仅修 shim 头，不动上游测试 |
| 8 | 真机 `make all` 卡 `doc/mk-texi.sh example.texi`（第 4 轮，configure/src 已过：`Makefile:1463: .deps/info-dep: No such file or directory` + `make[2]: *** [Makefile:1477: example.texi] Error 1`，此前还有 `autogen: command not found`） | doc/ 的 texi/man 由 `mk.sh`/`mk-texi.sh` 经完整 autogen 二进制从 `src/opts.def` 再生成；私有的 libopts shim 只覆盖 src 运行时链接，不提供 doc 生成器；属上游已知坏 doc 构建（Debian 01_fix_autobuild.patch + Homebrew gnu-complexity.rb 同样打补丁绕过，Build-Depends 另要 autogen+texinfo）。umask/mktemp 垫片只修 configure 临时目录，与此域无关 | 最小适配跳过 doc 构建与安装：build 改 `make SUBDIRS="lib src"`，上游测试改 `make check SUBDIRS=tests`（tests/ 全量仍跑，test-suite.log 解析不变），package 改 `install SUBDIRS=src` + 仅当 tarball 自带预生成 `complexity.1` 时才复制 man 页（不触发重建）；不新增依赖、不动上游测试 |

## 依赖版本

无 Conan 依赖。GNU autogen libopts 由 `libopts_shim/` 在 build() 内私有构建
（静态 `libopts.a` + 编译产出的 `autoopts-config` 可执行文件，仅供本次
configure 探测与链接，不安装进包，不新增依赖包，保持单 PR 原子性）。

## 配方文件（本轮全部新增，未 commit）

- `archives/c/complexity/1.13/conanfile.py`：validate(Linux/OHOS) +
  source(get) + generate(triplet/SHELL) + build(先私有构建 libopts_shim/
  `libopts.a` 与编译产出 `autoopts-config` 并前置 PATH，再
  configure/make/make check 计数打标) + package(autotools.install +
  COPYING) + package_info
- `archives/c/complexity/1.13/libopts_shim/`：`autoopts/options.h`
  （autogen-5.18.16 原样 vendor，保 tOptions/tOptDesc ABI）+
  `libopts.c`（手写最小实现，见文件头注释）
- `archives/c/complexity/1.13/conandata.yml`：GNU 官方源 + sha256 实测值
- `archives/c/complexity/1.13/manifest.yaml`（版本级）
- `archives/c/complexity/1.13/test_package/`：conanfile.py（VirtualRunEnv +
  2 断言标记）、test_complexity.sh、MANIFEST.yml（含 upstream_test_audit）
- `archives/c/complexity/commands.json`（软件级，L0k/R38：bin/ 有可执行文件必填）
- `archives/c/complexity/README.md`（软件级）
- `.hmbs/pr-body.md`：PR 正文草稿（测试数字待真机 evidence 回填）

| 9 | 真机 `make check` FAIL 1 且平台诊断 `[readonly_tmp]`（2026-09-07 预检，失败阶段 upstream_test）+ 预检 wrapper 报 `can't create temporary file /tmp/shnr*.tmp: Read-only file system` | 上游 `tests/complexity.test` 用 here-doc 写 rcfile/期望表（`cat > "$rcfile" <<-`、`sed ... <<-`），真机 `/bin/sh` 对 here-doc 临时文件硬编码 `/tmp`（只读），无视 HMBS 注入的 TMPDIR；而 bash 按 TMPDIR 建临时文件。此前配方只设 `os.environ` TMPDIR，可被 Conan toolchain env 过滤，且测试仍经 `/bin/sh`（shebang）执行，故预检仍 FAIL | 文件内最小适配（不断言、不改期望表、不删测试）：①build() 内新增 `_bash_path()` 定位 bash、`_patch_test_tmpdir()` 把所有 `complexity.test` 副本（source+build 树）的 shebang 指到 bash 并在首行后内嵌 `TMPDIR/TMP/TEMP` 导出（ baked 为真机可写 tmpdir，Conan env 过滤穿透）；②`make check` 追加 `LOG_COMPILER=<bash>` + `TMPDIR/TMP/TEMP` make 变量双保险；③configure 前后各 patch 一次以覆盖 build 树新拷本 |

| 10 | 同一指纹第 2 次失败：上一轮 bash/TMPDIR 补丁已进预检（报错行号 296→396 证实新代码已跑），但 `make check` 仍 TOTAL=1 FAIL=1，说明根因不在 shell/tmp 而在别处 | 本轮用 MinGW gcc 把真实生成的 `src/opts.c` + 兼容层 `libopts.c` + 自写 harness 直连单测（仅诊断，不作验证证据）：场景 A（`-< rcfile -I main foo.c`）与 B（`-< rcfile -t0 sample.c`）的 HAVE/ENABLED/阈值/IGNORE 栈/返回值全部正确，排除 rcfile 解析与 `-<` 处理嫌疑；剩余风险转向 optstring 首字符 `+`（POSIX 模式）——部分 libc 不认 `+` 会整体破坏解析，而上游真实调用里选项恒在操作数之前，置换模式与遇操作数即停在此完全等价 | ①`libopts.c` 去掉 optstring 的 `+` 前缀，改走全范围置换解析（harness 重验 A/B/E：A ret=5 全标志+阈值 0+IGNORE=[main]，B ret=4 阈值 0，E（`--` 终止）ret=2 且阈值保持默认 30；中间曾试手动预扫描方案，因把 `-<` 的独立参数误判为操作数而被 harness 当场证伪并放弃）；②`conanfile` 新增 `_dump_test_logs()`，check 失败时把 `tests/complexity.log` 与 `test-suite.log` 各末 60 行打进输出，使下次预检自带真实差异；上一轮 shell/TMPDIR 补丁保留 |

| 11 | 上轮加入的失败转储首次带回实证：`complexity.log` 显示测试前半全正常（srcdir 定位、rcfile here-doc 成功——shell/TMPDIR 方向已被证有效），唯一错误是 `complexity.test[39]: .../build-release/src/complexity: inaccessible or not found`，即 VPATH 构建下 `make SUBDIRS="lib src"` 退出 0 却没在 `$(top_builddir)/src/` 留下二进制，而测试只能从该固定路径执行；`[readonly_tmp]` 平台诊断实为 preflight.sh 自身 `/tmp/sh*.tmp` 噪声，与测试本体无关 | 构建域最小修复（不碰测试）：build() 在 SUBDIRS 构建后硬门控 `build_folder/src/complexity` 是否存在，缺失则用无空格 SUBDIRS 的显式 `make -C src` 补建，再缺失则带 `src/` 目录清单抛错，使下次日志无论成败都有实物证据 |

| 12 | 本轮预检 compile 失败：`make: Nothing to be done for 'src'` 后 `src/complexity missing after SUBDIRS build`，补建 `make -C src` 在编译 `complexity-complexity.o` 成功后仍 Error 2（build() line 416） | 双根因：① `SUBDIRS=lib src` 作为单个 make 参数被 shell 拆成 `SUBDIRS=lib` + 目标 `src`，顶层只编 lib 而 src 目录已存在故报 Nothing to be done，二进制从未生成；② `src/Makefile.am` 的 `cx-vs-mc: cx-vs-mc.sh` 规则用字面 `chmod 555`（非 $(CHMOD)），在 HMBS_CAP_CHMOD=0 文件系统上失败导致 `make -C src` Error 2（证据：上游包内 `src/Makefile.am` 含 `cp $(srcdir)/cx-vs-mc.sh $@ && chmod 555 $@`，`complexity_LDADD=$(ao_LIBS) $(gnulib) -lm` 说明链接本身已由 shim 覆盖） | ①构建改用无空格的显式 `make -C lib` + `make -C src`，彻底避开 SUBDIRS 含空格拆分；② `_private_libopts()` 新增编译型 `chmod` 容错垫片（与 autoopts-config 同目录、前置 PATH，免 chmod 安装）：execv 真实 chmod 但恒返回 0，CI 上仍正确设模式，HMDFS 上容错通过；cx-vs-mc 的 +x 对测试无影响（上游测试与 test_package 只执行 `complexity`）；不断言、不删测试 |


| 13 | 本轮预检 test_package 阶段失败：上游 1/1 已通过，但 `complexity binary not found: .../p/bin/complexity`（test_package/conanfile.py line 26） | `package()` 用 `autotools.install(args=["SUBDIRS=src"])` 后包内 bin 为空：顶层 automake install 递归依赖 doc 子目录（autogen 重建 example.texi），SUBDIRS 覆写方式在受限文件系统上不可靠；证据链：日志显示 `HMBS_UPSTREAM_TEST_RESULT` 1/1 passed 后直接进 test_package 并报 bin 缺失，上游 `src/Makefile.am` 确认 `bin_PROGRAMS=complexity` 本该安装到 bindir | 跟随已合入 cflow 1.0.0 方法：`package()` 改为手动 `copy()`——从 build_folder/src （回退 source_folder/src）拷贝 `complexity` 到 `package_folder/bin`，同时拷贝 `cx-vs-mc` （缺失则用 `cx-vs-mc.sh` 重命名兼容），best-effort `chmod +x` 兼容 HMBS_CAP_CHMOD=0；未找到二进制时探错结束；不动上游测试、不删断言。同时更新第 5 步描述为手动拷贝安装。 |


| 14 | 本轮预检 test_package 阶段失败（上轮手动 copy 修复后）：`FAIL: complexity --version rc=64 output=complexity: unknown option '-v'` + `FAIL: complexity scoring rc=5 output=No procedures were scored`，RESULT passed=0 failed=2 | 双根因：① shim 把 VER/HELP 按 OPTST_ARG_TYPE=STRING 建成 required_argument，裸 `--version` 被 getopt 报缺参数而误报 unknown option（生成的 opts.h 证实 VERSION value=‘v’、long 名=version，VER_FLAGS 含 OPTST_ARG_OPTIONAL+OPTST_IMM）；②测试脚本直接 `$BIN sample.c`，而默认 threshold=30（opts.def arg-default 30）过滤掉所有 0~2 分样本函数，主轭 main-fini 打印 No procedures were scored 并 exit 5，与上游测试始终用 `-t0` 保持一致 | ① libopts.c 建表时对 ‘v’/‘?’/‘!’ 强制 has_arg=0（即时无参数选项，裸 `--version`/`-v` 走 optionPrintVersion 正常退 0）；② test_complexity.sh 打分行改为 `$BIN -t0 sample` （与上游 complexity.test 的 `-t0` 用法一致）；不删断言、不降阈值、保持 2 用例口径。 |
| 15 | 本轮预检 evidence/incomplete：`conan create 通过` 但 `缺少 HMBS_UPSTREAM_TEST_RESULT 上游测试证据`（发现 0/执行 0），同期 test_package 2/2 已过 | 构建缓存命中跳过 build()：日志 `Exported: complexity/1.13#706e97…` 紧接 `Already installed! (1 of 1)` 后直接进 test_package，build() 内 `make check` 与标记打印根本未执行；配方本身无错，证据只在重建轮出现，复跑同代码即命中缓存 | test_package 内对上游做忠实重跑兜底（与 build() 的 `make check` 并存、不替代）：①新增 `test_package/upstream_sample.c`（与官方包内 `tests/sample.c` 逐字节一致，260 字节）；②新增 `test_package/test_upstream_check.sh`（POSIX sh：rcfile 双标题断言 + 与上游完全相同的 `sedcmd` 归一化 + 与上游内嵌期望表逐字 cmp，临时文件走 `$TMPDIR`，桩二进制在标题/cmp 处必 exit 1；与 build 树版本唯一差异是 phase 1 用 sample 而非 `src/*.c`，故 `handle_noop==0` 行检保留给 `make check` 专属）；③`test_package/conanfile.py` 在既有 2 断言标记后真实运行该脚本（`self.run` 非零即抛），成功才输出 `HMBS_UPSTREAM_TEST_RESULT={status:passed,framework:automake,discovered:1,executed:1,passed:1}`；④`MANIFEST.yml` 登记新文件与缓存命中原因。未删断言、未跳过测试 |

## 待真机验证

- 工作树保持未提交，等待 hmbs 同步后真机预检复跑。预期：私有 libopts
  构建成功，`autoopts-config cflags/ldflags` 探测非空，configure 越过
  `libopts was not found`，上游 1/1 + 新增 2/2。

| 16 | CI build 42269 FileNotFoundError clang (building private libopts) | old code trusted bare CC/clang name without validation; CI worker CC=clang not on PATH so check_call crashed though gcc/cc existed | added _resolve_c_compiler/_resolve_ar: Conan conf first, CC first-token only, every candidate validated via which/isfile, absolute path must exist+exec; keeps preflight clang, falls back to gcc on CI; no test change |
| 17 | CI build 42389 lld fails loading libxml2.so.16 (E132/E266 fingerprint, _private_libopts line 248 link step) | OHOS SDK llvm/bin/lld dynamically needs SDK llvm/lib libxml2.so.16; worker CI-020 default loader path lacks it, so every clang link dies (xmlFreeDoc symbols missing). Prior fix only validated compiler names but kept clang+lld, hence same link failure recurred | generate() now prepends SDK llvm/lib (fixed path + glob fallback) to LD_LIBRARY_PATH via toolchain environment; build()/_private_libopts() export the same dir for direct subprocess links (autoopts-config/chmod). No -fuse-ld switch (OHOS sandbox needs lld-signed ELF), no test change |
