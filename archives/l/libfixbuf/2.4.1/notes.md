# libfixbuf 2.4.1 适配笔记

## 基本信息
- 软件: libfixbuf (CERT NetSA IPFIX 协议库, C)
- 版本: 2.4.1 (2020-12-22, 官方稳定版)
- 源码: https://tools.netsa.cert.org/releases/libfixbuf-2.4.1.tar.gz
- sha256: 8c535d48120b08df1731de709f2dbd2ba8bce568ad64cac34826102caf594d84 (与官方 Release History 页公布值一致, 本地下载复算匹配)
- 构建系统: autotools + libtool (官方 tar 包自带 configure, 无需 bootstrap)
- 许可证: LGPL-3.0-only
- 目标: OHOS aarch64, 纯库 (--disable-tools, 无 CLI, 故无 software 级 commands.json)

## 依赖
- glib2/2.88.0 (configure.ac 硬性要求 AM_PATH_GLIB_2_0 >= 2.18, 含 gthread; public.h 传递包含 glib.h)
  - transitive_headers/transitive_libs: 消费者编译测试需要 glib 头与链接
- pkgconf/3.0.5 (build_requirements, 供 AM_PATH_GLIB_2_0 的 pkg-config 探测)
- 可选的 openssl/sctp/spread 一律不启用 (默认即关闭, 无需额外依赖)

## OHOS 适配点
- autoconf config.guess/config.sub 不认识 OHOS: 在 source 树 autoconf/ 目录内做 E007 式修补
  (HarmonyOS|OHOS|OpenHarmony 早识别为 aarch64-unknown-linux-ohos; config.sub 接受 -linux-ohos)。
  复用 lzop 1.04 / ldns 1.9.0 / burp2 2.1.0 的同类做法, 无平台宏注入。
- configure 临时目录 umask 077 + mktemp -d 在真机 HMDFS 上不可写: 改为任务 TMPDIR
  (HMBS 注入) + umask 000 + mkdir -p, 主备两分支同改 (E011/E114, 复用 ldns 1.9.0 模式)。
- make -j1 单作业 (HMDFS jobserver FIFO EPERM, E074, 复用 lzop 模式)。
- HMDFS getcwd 兜底: 进 build 目录并重设 PWD, 避免 autoconf ac_pwd 校验失败 (复用 lzop 模式)。
- 安装后删除 *.la (libtool 归档无用)。
- settings 四项齐全 (os/compiler/build_type/arch, L0p 门禁)。
- 真机 hardening (2026-09-18 预检 `configure[162]: /data/service/hnp/bin/bash:
  inaccessible or not found` + 只读 /tmp): generate() 经 Environment 固定
  SHELL/CONFIG_SHELL=/bin/sh 与可写 TMPDIR/TMP/TEMP (优先 HMBS 注入值);
  build() 落盘清洗 conanbuild*.sh 坏 bash 路径并补 export, 再以
  `TMPDIR=... CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure` 内联前缀
  调用 (优先级高于 sourced 环境排序, 复用 guile/boolstuff 模式)。

## 上游测试审计 (HMBS no_tests 口径)
- 官方包内无 tests/ 或 test/ 目录, find -name '*test*' 全树零命中 (除本笔记的描述文字外)。
- Makefile.am: SUBDIRS = src include, 无 TESTS / check_PROGRAMS / check-local。
- src/Makefile.am: 仅 libfixbuf.la 与 (默认关闭的) ipfixDump 目标, 无测试目标。
- configure.ac: AC_OUTPUT 仅生成构建文件, 无测试宏。
- 结论: make check 为 automake 默认空目标, 执行 0 用例。MANIFEST.yml 按规范写入
  upstream_tests_exist: false + 非空 upstream_test_audit, test 包输出
  HMBS_UPSTREAM_TEST_RESULT status:"no_tests" discovered:0 executed:0 及具体 reason。
- 证伪说明: 不存在“静默跳过计为通过”的风险——上游根本无测试入口, 本包如实申报 no_tests,
  不虚构通过率。

## test_package 设计 (R34)
- test_libfixbuf.c 真实调用被测库 API, 无网络、无文件、无随机性, 原生可跑:
  1. fbInfoModelAlloc() 非空
  2. fbSessionAlloc(model) 非空
  3. fbTemplateAlloc(model) 非空
  4. 新模板计数为 0 且会话模型指针回指同一 model
  5. 全链路清理完成
- 二进制打印每条 PASS/FAIL + `FIXBUF_TEST assertions=N failures=M`, conanfile.py 用正则解析,
  数字来自测试程序输出 (非硬编码); 零断言或无摘要直接判失败。
- 标记: HMBS_TEST_PACKAGE_RESULT {executed,passed,command,discovered=5,passedCount=5},
  HMBS_UPSTREAM_TEST_RESULT {status:"no_tests",framework:"autotools",command:"make check",
  discovered:0,executed:0,passed:0,failed:0,skipped:0,reason}。
- CMakeLists 经 CMakeDeps 链接 libfixbuf::libfixbuf, 传递的 glib 头/库由依赖链提供。

## 本轮修复 (2026-09-18 真机 compile 失败)
- 现象: config.guess 2020-11-07 unable to guess system type, configure 报 cannot guess build type; 伴随只读 /tmp 诊断。
- 根因: _patch_config_guess_sub 单一无引号 marker 与旧版 config.guess/config.sub 版式不匹配, 替换静默跳过, OHOS 分支从未写入; 且仅修 autoconf/ 单目录、未放宽 config.guess 内 umask。
- 修复: 改为全树递归修补全部 config.guess/config.sub; config.guess 优先 NetBSD 锚点插入 enscript 式 HarmonyOS|OHOS|OpenHarmony 分支 (兼容引号/无引号/正则兜底三档), config.sub 用 linux-android 通用锚点接受 linux-ohos; config.guess 与 configure 内残留 umask 077 统一放宽为 000, configure 主备分支缺失时不再硬失败。
- 复检 (2026-09-18 第二轮真机): config.guess 已输出 aarch64-unknown-linux-ohos, 但 config.sub 报 OS `ohos' not recognized。
  下载官方 tar 包实查: 新版 field-split 版式下 `*-*)` 分支先于 `linux*)` 命中, kernel=linux os=ohos, 而 OS 白名单只有 gnu*|android* 无 ohos*;
  且 2.3 保护条件误用裸串 `linux-ohos` (2.1 已写入 basic_os=linux-ohos) 导致内核组合行从未补上。
  修复: 2.1 补 ohos-linux 三元组分支 (4 空格 `;;` 缩进按字节转储对齐), 2.2 白名单加 ohos*, 2.3 改用 `linux-ohos*` 带星保护。
  验证: 对官方包实物跑 shipped 补丁逻辑, git-bash 下 `sh config.sub aarch64-unknown-linux-ohos` 返回 0 且原文输出。
- 复检 (2026-09-18 第三轮真机): 三元组已通过, configure 倒在 `checking whether the C compiler works... no` (C compiler cannot create executables, Error 77, build() line 368)。conftest 为裸链接, CC 本身已解析到 hnp clang, 故疑点在自研 build() 链路: 手工 `sh configure` + 落盘改写 conanbuild 脚本可能丢弃工具链 CFLAGS/LDFLAGS/CC 环境 (E001/E505/E524 均指向工具链环境; E350 的运行拦截论对不上本错误串且其 --host 绕法违反 E007/R1 铁律, 不采纳)。
- 修复 (换策略): 删除 _sanitize_conanbuild_scripts/_configure_switches/手工调用, build() 改回标准 Autotools.configure()+make -j1 (enscript 1.6.6 / epsilon 0.9.2 同 worker 成功先例); 保留已验证的 config.guess/sub/mktemp 源码补丁与 generate() 的 SHELL/CONFIG_SHELL/TMPDIR 钉选; 等待 HMBS 真机复检。
- 复检 (2026-09-18 第四轮真机): 标准 Autotools.configure() 倒在 `configure[162]: /data/service/hnp/bin/bash: inaccessible or not found` (Error 127, build() line 297) + 只读 /tmp 诊断, HMBS 能力 shell=/bin/sh、tmpdir=任务独立可写目录。根因: 聚合 conanbuild.sh 在工具链环境之后被 source, 重新导出坏 CONFIG_SHELL 与陈旧 /tmp, 覆盖了 generate() 的 Environment 钉选; configure 的 autoconf 重执行分支 (`exec $CONFIG_SHELL`) 与 mktemp 回退因此同时命中坏值。标准 helper 本身无错, 错在落盘脚本的旧值。
- 修复 (本轮, 最小多通道): 保留标准 Autotools.configure()/make -j1 (工具链 CFLAGS/LDFLAGS/CC 不动); 新增 `_sanitize_hmbs_shell_scripts()` 在 build()/package() 前遍历 build/generators 目录下 conanbuild*/conanautotools*/conanrun*.sh, 将 `/data/service/hnp/bin/bash` 改为 `/bin/sh` 并追加 `export SHELL/CONFIG_SHELL=/bin/sh + TMPDIR/TMP/TEMP=<可写tmpdir>` (末尾追加, source 时后者胜出); os.environ 同步钉选同组变量。只替换临时根与失效 shell, 不碰上游源码与测试口径。

## 状态
- 本轮: 配方已改未提交, 等待 HMBS 真机预检 (编译 + test_package + 上游 no_tests 证据)。
- 严禁事项遵守: 未 commit/push, 未改 PR 正文, 未发送 /rebuild 或 /ai review。
- 复检 (2026-09-18 第五轮真机): 标准 helper + 落盘清洗后仍倒在 `checking whether the C compiler works... no` (Error 77) + `can't create temporary file /tmp/shk*.tmp: Read-only` + HMBS `[readonly_tmp]` 诊断, CC 已正确解析到 hnp clang。根因: TMPDIR 目录悬空 — generate() 只透传 HMBS 注入路径但从不 mkdir, _hmbs_tmpdir() 又以 `isdir` 为门: HMBS 路径尚不存在时直接弃用并回落到 build 内目录, 两阶段看到不同 TMPDIR; clang 不会 mkdir -p $TMPDIR, 缺目录即报 cannot create executables, 回退到只读 /tmp 即命中诊断。
- 修复 (本轮, 最小): generate() 计算 tmpdir 后立即 `os.makedirs(tmpdir, exist_ok=True)`; _hmbs_tmpdir() 去掉 `isdir` 前置门, 改为先 makedirs 再 `isdir` 确认后返回, 不存在才回落; configure 的 umask 077 全量放宽 + 主备 TMPDIR/mkdir -p 补丁保留, 标准 Autotools.configure()/make -j1 与落盘清洗不动。只保证临时根存在且一致, 不碰工具链与测试口径。
- 复检 (2026-09-18 第六轮真机): 同一 Error 77 + 只读 /tmp/sh*.tmp 复发, CC 仍正确解析到 hnp clang。根因: 上轮只保证目录存在, 未验证可写且 generate()/build() 解析链不一致 — generate() 只认 TMPDIR/TMP/TEMP, build() 同样三变量, 均忽略 HMBS_AUTOCONF_MKTEMP_FALLBACK/HMBS_TMPDIR, 且以 isdir 为门不做写探针; 若 HMBS 路径存在但不可写 (或两阶段看到不同值), clang/conftest 仍回退到只读 /tmp。
- 修复 (本轮, 最小): _hmbs_tmpdir() 改为探针式共享解析 — 候选顺序 HMBS_AUTOCONF_MKTEMP_FALLBACK(仅路径形态, 跳过 0/1 标志)/HMBS_TMPDIR/TMPDIR/TMP/TEMP, 逐个 makedirs + 写探针文件验证, 拒绝空/0/1//tmp, 不通过则回落 build 内 .hmbs-tmp (balboa 同款); generate() 改调该共享方法保证三阶段同值; build()/package() 同步 HMBS_TMPDIR。标准 helper、config.guess/sub/mktemp 补丁与落盘清洗不动, 不碰工具链与测试口径。
- 复检 (2026-09-18 第七轮真机): 同一 Error 77 + `can't create temporary file /tmp/shii*.tmp: Read-only` + `[readonly_tmp]` 复发, CC 仍正确解析到 hnp clang, 且 harness 自身 preflight.sh[306] 也报 /tmp 只读 (toybox ash 模板 `/tmp/shXXXXXX` 硬编码, 见 knowledge/environment.md HiShell 条目)。
  审计发现三处漏网: ① generate() 只写 tc.environment() 文件, 同进程的 pkg-config/工具链探针仍继承旧 os.environ 见到 /tmp; ② 上轮把 configure 主分支从可写的 `./confXXXXXX` 搬到 `${TMPDIR}` (悬空即回退 /tmp), 而主分支本就不需要 /tmp; ③ 落盘清洗只追加不替换, profile 聚合的 `TMPDIR="/tmp"` 无 export 赋值 + 后续 `export TMPDIR` 会重新导出旧值; config.guess/configure 内显式 `/tmp/cg*` 与 `mktemp -d /tmp/*` 模板绕过 $TMPDIR。
- 修复 (本轮, 最小, 只换临时根不碰工具链与测试): generate() 计算后立即 makedirs 并同步 os.environ 同组变量; configure 主分支改回 `./confXXXXXX`(仅 umask 077→000), 回退分支改 `${TMPDIR:-.}/conf$` + mkdir -p; config.guess 内 `/tmp/cg`、`/tmp/sh` 与 configure 内显式 `mktemp* /tmp/*` 模板统一换为 `${TMPDIR:-/tmp}` 根; 落盘清洗新增对 TMPDIR/TMP/TEMP=`/tmp` 赋值的原地替换 (regex, 覆盖引号/无引号), 追加块保留作 last-wins 保险。标准 Autotools.configure()/make -j1、OHOS 三元组补丁与 HMBS 探针顺序不动。
- 复检 (2026-09-18 第八轮真机): 上述全套透传机制生效后仍同一指纹复发 (Error 77 + /tmp/shk*.tmp, build() line 475, CC 仍为 hnp clang)。比较结论: 机制已修到头，剩余变量是位置而非机制——Python 探针称 HMBS runtime tmp 可写，但 toybox-ash 子进程与 clang conftest 仍回退 /tmp，且 harness 自身 preflight.sh[306] 并发 /proc+`/tmp` 受限，指向按进程 SELinux 域差异。
- 修复 (本轮, 换策略, 仍只换临时根): _hmbs_tmpdir() 改为构建目录本地 `.hmbs-tmp` 优先经同一探针 (makedirs+写文件) 命中即返回，与必定成功的 .o 输出同域同文件系统；HMBS 注入路径退为回退候选；最终仍回退本地目录。传播三通道、主分支保持 ./、显式模板根替换与落盘原地替换全部保留；工具链、三元组补丁与测试口径不动。
- 复检 (2026-09-18 第九轮真机): 本地优先后仍同一指纹第三次复发 (Error 77 + /tmp/sh6g*.tmp, build() line 494, CC 仍为 hnp clang)。三轮结论: 位置和机制都已换过且指纹纹丝不动，/tmp 很可能只是 harness 自身 preflight.sh[306] 的环境噪声 (每次不同 PID/不同 shk/shii/sh6g 后缀)，而 conftest 链接失败另有根因；但三轮均无 config.log，只能盲猜。
- 修复 (本轮, 换策略, 不碰临时目录): ① generate() 经工具链透传通道追加显式 GNU 三元组 `--build/--host=aarch64-unknown-linux-gnu` (libtlsrpt/0.5.1 已验证经验的适配：同通道、同取值，OHOS/HarmonyOS 双串门控；CC/CFLAGS/LDFLAGS 仍来自 OHOS 工具链，conftest 仍测真实 OHOS 编译器；自带 ohos guess/sub 补丁保留作兜底)，使 configure 跳过脆弱的 2020 版 config.guess 执行整段 (/tmp 敏感的 uname+mktemp+编译探针)；② build() 对 autotools.configure() 加失败时打印 config.log 末尾 60 行 (HMBS_CONFIG_LOG 前缀) 后原样重抛，仅加诊断、不改成功行为、不跳过任何检查。

- Tenth round (2026-09-18, 2nd strategy cycle): reverted ninth-round GNU triplet bypass; E007 and build-systems S3.0 forbid faking --build/--host=gnu (cross misdetect, AC_RUN_IFELSE wrong). Evidence: with triplets active the fingerprint was byte-identical (Error 77 + /tmp/sh*.tmp, CC=hnp clang), so bypass fixed nothing. New route: (1) no explicit triplets, E007 ohos patch only; (2) pre-configure direct-CC trivial-compile probe in build dir + tmpdir (HMBS_CC_PROBE, log-only) to isolate toolchain vs shell/heredoc fault; (3) targeted config.log block HMBS_CONFIG_FAIL (compiler-check anchor + error lines) replacing tail-60 dump truncated to exit 77. Tmp channels, umask, ohos patches, standard Autotools helper, test posture untouched.

- Eleventh round (2026-09-18, new decisive evidence): tenth-round HMBS_CONFIG_FAIL captured configure:3721 /data/service/hnp/bin/clang: inaccessible or not found, exit 127. Root cause is the conf compiler path itself, not /tmp or triplets (same fingerprint with and without gnu triplets proves triplet-independence). Fix: (1) probe ordered C/CXX candidates (conf c/cpp, hnp bin, SDK llvm bin via version-agnostic glob, which clang/cc/gcc) with --version and pick first executable; export CC/CXX/LD_LIBRARY_PATH plus last-wins append into sourced scripts; (2) prepend SDK llvm/lib to LD_LIBRARY_PATH in generate (E501, glob-based); trivial-TU proof retained via HMBS_CC_PROBE. Triplet bypass stays reverted per E007/S3.0; tmp/umask/ohos patches/tests untouched.
- Twelfth round (2026-09-18 can't-fork): new fingerprint configure[36]: can't fork - try again + harness preflight.sh[306] /proc+`/tmp/shcausxi.tmp` Read-only (capabilities hardlink=0/chmod=0/local_mktemp=1). Python-side TMPDIR probe still reports writable, so fault is worker-level fork/process-table pressure, not a deterministic recipe tmp path. Fix is fork-light only: cap --version candidates to conf/env/SDK/clang (drop hnp-bin/which/cc/gcc fallbacks), single tmpdir-only trivial-compile proof, and carry TMPDIR/TMP/TEMP env into every probe subprocess. Standard Autotools.configure()/make -j1, ohos/config.guess/sub, umask/mktemp, sanitize channels and no_tests posture untouched.
- 2026-09-19 preflight (new fingerprint): `checking for pkg-config... no` + `configure[19239]: no: inaccessible or not found` + `configure: error: Cannot find a suitable glib2 (>= 2.18)` (build() line 706). Compiler chain healthy (prior Error 77/127 gone); glib discovery chain missing: VirtualBuildEnv did not provide the literal `pkg-config` name (pkgconf exposes `pkgconf`), and Conan 2.29 does not export the PkgConfigDeps folder via PKG_CONFIG_PATH (ccfits/astrometry precedent). Fix (minimal, discovery vars only): new `_hmbs_pkg_config_bin()` resolves absolute `pkg-config`/`pkgconf` binary; generate() defines PKG_CONFIG + prepends PATH (tool dir) + PKG_CONFIG_PATH (generators_folder with glib-2.0.pc) via tc.environment() and mirrors to os.environ; build() re-exports same; `_sanitize_hmbs_shell_scripts()` appends last-wins exports. Standard helper, ohos patches, TMPDIR/SHELL pins, no_tests posture untouched. Recipe changed, uncommitted, awaiting HMBS preflight.
- 2026-09-19 preflight round 2 (strategy changed): last round's PKG_CONFIG pin worked (`checking pkg-config is at least version 0.16... yes`) but `configure: error: Cannot find a suitable glib2` persists with `$PKG_CONFIG --exists` failing for glib-2.0 args and gio-2.0 (build() line 820). Root cause per knowledge E348: PkgConfigDeps emits only the single .pc declared by glib2/2.88.0 (glib-2.0.pc), while libfixbuf configure probes the GLib multi-.pc family (gthread module + gio-2.0 probe). Fix (adapt E348 graphene 1.10.8 forwarding-pc + fallback alias loop): new `_forward_glib_family_pc()` called right after PkgConfigDeps.generate() writes gobject-2.0/gio-2.0/gthread-2.0/gmodule-2.0 forwarding .pc into generators_folder, Version dynamically inherited from glib-2.0.pc, Requires: glib-2.0; existing files untouched; package-embedded .pc never added to search path. Toolchain, triplet/mktemp/sanitize pins, no_tests posture untouched. Recipe changed, uncommitted, awaiting HMBS preflight.
- 2026-09-19 preflight round 3 (strategy changed, link stage): configure now passes (glib family fix worked); `make` fails linking libfixbuf.la with `grep: //lib/libpcre2-8.la: No such file or directory` + `libtool: error: '//lib/libpcre2-8.la' is not a valid libtool archive` (build() line 917, autotools.make). Root cause E236: OHOS autotools dep packages install with --prefix=/ so their .la files bake libdir='//lib' and dependency_libs referencing //lib/*.la. Fix (adapt ekg2 0.3.1 _fix_la_libdirs, gts 0.7.6 E236 precedent): new `_fix_la_libdirs()` called in build() right after source patches builds a //lib/<name>.la map across host deps and rewrites libdir/dependency_libs/-L//lib to real package lib dirs; .la files kept so transitive static deps still resolve. Configure/discovery pins, triplet/mktemp/sanitize channels, no_tests posture untouched. Recipe changed, uncommitted, awaiting HMBS preflight.

- 2026-09-19 preflight round 4 (package install): configure+make passed, make install died in src/ with install echo ok but chmod 644 <pkg>/lib/libfixbuf.a ENOENT (package() line 1006, caps chmod=0/hardlink=0/install_shim). Fix adapts wv/1.2.9 + cataract/1.0.0 install shim: package() writes _ohos_install_shim/install (mkdir/cp, chmod best-effort, os.open 0755), redirects INSTALL/install_sh/mkdir_p in generated Makefiles, tolerates bare chmod (|| true), then autotools.install(args=[-j1]). Build/check/test posture untouched. Recipe changed, uncommitted, awaiting HMBS preflight.

- 2026-09-19 preflight round 5 (test_package cmake): main lib install fixed, test_package died at CMake project() with System unknown Platform/HarmonyOS + CMAKE_C_COMPILER /data/service/hnp/bin/clang broken (test build line 37). Root cause is CMake compiler check on worker, not test code. Fix uses different strategy from install-shim round: test_package drops CMake, compiles single TU directly with tools.build:compiler_executables c (gumbo-parser/0.10.1 precedent), flags aggregated from host deps cpp_info; same 5 assertions and markers kept. Recipe changed, uncommitted, awaiting HMBS preflight.

- 2026-09-19 preflight round 6 (test_package CC probe): direct-cc round compiled TEST_CC with conf c=/data/service/hnp/bin/clang but shell died inaccessible or not found exit 127 (same fingerprint as main eleventh round). Root cause is blind trust of conf path, not flags. Fix uses different strategy: test_package _select_cc() probes conf c/env CC/SDK llvm clang/PATH clang via --version no-shell and uses first executable (main _hmbs_cc_probe pattern); same 5 assertions and markers kept. Recipe changed, uncommitted, awaiting HMBS preflight.
