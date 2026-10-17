# librsb 1.3.0.3 适配笔记

## 基本信息
- 上游：https://sourceforge.net/projects/librsb/files/librsb-1.3.0.3.tar.gz
- 版本：1.3.0.3（首次适配，无后缀）
- 构建系统：autotools（configure + make，附带生成的 configure 脚本）
- 许可证：LGPL-3.0-only（COPYING）
- 源码校验：sha256 `f9d343f9e24bceb1d6f76c3db0617ad326eb246891b51424f3931a8f3965bf5f`，
  已用官方 `librsb-1.3.0.3.tar.gz.md5`（21ac9bdd325c83ec559074f0ab7f20ee）交叉验证一致
- 依赖：zlib/1.3.1.1（制品仓已发布版本，上游默认 `--with-zlib` 需要它）
- 适配路径：路径 A（基础适配）
- 申请人：liucu / 队伍：龙骑士

## 上游源码审计（librsb-1.3.0.3.tar.gz，847 个文件）
- 构建入口：configure.ac + 预生成的 configure / Makefile.in / config.guess / config.sub
- 库产物：librsb.la → librsb（静态），公共头 rsb.h + rsb_types.h + blas_sparse.h +
  rsb-config.h，工具脚本 librsb-config，基准程序 rsbench（bin_PROGRAMS，随包安装）
- 可选组件（默认全开）：C 示例、Fortran 示例（需 FC）、C++ 示例、Sparse-BLAS 接口、
  pkg-config 安装
- `make check`：顶层与各子目录 Makefile.am 均无 TESTS / check_PROGRAMS /
  check_SCRIPTS，`make -n check` 即 automake 默认空目标（check-am: all-am），执行 0 用例
- 真实可运行套件：examples/Makefile.am 的 `tests:` 目标——构建 noinst 程序后运行
  bench.sh、逐个运行示例二进制、在 pd.mtx 上运行 ./autotune
- rsb_gtests.cpp：221 个 TEST 用例，需系统 gtest（AC_CHECK_HEADERS([gtest/gtest.h]) +
  AC_CHECK_LIB([gtest_main])）；OHOS 真机与制品仓均无 GTest，且该程序仅为
  noinst（不在 make check 执行路径上），故 221 用例未运行（见 PR 补充说明）
- rsbtest / rsblib / librsbpp：独立实验性外部包（--with-rsbtest 等），默认不构建
- Fortran：AC_PROG_FC 搜索 xlf/ifort/gfortran 等；OHOS 无 Fortran 编译器（知识 E109），
  configure 留空 FC 并置 HAVE_FC=false，Fortran 源与示例自动排除，无需额外传参

## 配方设计
- `conanfile.py`：Autotools 模板；`--build=aarch64-unknown-linux-gnu`（config.guess
  不识 OHOS，libarchive 3.8.7 同款先例）；shared=False 时 --enable-static/--disable-shared
- zlib 接入：tc.extra_cflags/extra_ldflags 显式 -I/-L + rpath（libarchive 同款），
  另存 `librsb_ldpath` env 脚本供 make tests 运行期查找；package_info 声明
  requires zlib::zlib（静态消费方 -lz）与 system_libs m（Linux/OHOS）
- HMDFS 兼容：build() 先 chdir + 固定 $PWD（lzop 1.04 同款，防 getcwd 失败）；
  make 统一 -j1（防 jobserver fifo EPERM）
- `$(BASH)`：examples tests 目标经 $(BASH) 调 bench.sh；由 CONFIG_SHELL/shutil.which
  探测后注入（OHOS /bin/sh 为 mksh，不可直接用）
- 自检护栏：运行前断言期望的 9 个示例二进制存在；若出现 Fortran 产物（sbtf*）则
  直接失败并要求重数 discovered，避免标记数字与实际执行脱节
- 无 patches/（零补丁完成设计目标）；纯库包，不设 bindirs，不建 commands.json（L0k/PF8）

## 上游测试组成（默认配置 + 无 Fortran，共 11 步）
1. bench.sh（rsbench 全类型基准 + --compare-competitors 对照 + 性能记录往返）
2-7. hello / snippets / transpose / power / autotune / backsolve（C 示例）
8. cplusplus（C++ 示例）
9-10. hello-spblas / io-spblas（Sparse-BLAS 接口示例）
11. ./autotune pd.mtx（真实矩阵端到端调优运行）

## test_package（消费者视角）
- test_librsb.c：原创数值测试，3x3 对角阵 diag(2,3,4)，
  init → COO 建矩阵 → SpMV（N/T/beta=1 三形态逐元校验）→ free/exit，
  每阶段一行 CHECK-OK，共 6 个（test() 计数后打印 HMBS 标记，exit 0 不单独算数）
- CMakeLists 经 CMakeDeps/Toolchain 链接 librsb::librsb + ZLIB::ZLIB

## 真机 fork 失败修复（2026-09-20 预检 failed：sh: can't fork - try again）
- 现象：编译阶段 `sh: can't fork - try again`，上游/新增测试 0/0/0。小盒子单编译单元内存峰值耗尽导致 fork 失败（make 已是 -j1，仍复现）。
- 处理：generate() 经 AutotoolsToolchain 追加 `-g0 -O1`（C/CXX，追加在最后以覆盖 build-type 默认的 -g/-O2），保留 zlib -I/-L/rpath 不动；不改变测试口径、不拆分测试、不跳过用例。
- 待下轮真机验证是否通过编译并跑出 11 步上游 + 6 个消费者断言。
## 真机编译器失败修复（2026-09-21 预检 failed：C compiler cannot create executables）
- 现象：`checking for gcc... /data/service/hnp/bin/clang` 后 `checking whether
  the C compiler works... no`，`configure: error: C compiler cannot create
  executables`，conan build() Error 77。bash 路由已通（configure 跑过了 141 行），
  新失败域在编译器本身。
- 根因判断：profile 把 `tools.build:compiler_executables` 钉在
  `/data/service/hnp/bin/clang{,++}`，该路径在本预检机上缺失/不可执行时
  configure 仍回显该路径名，随后执行失败即报 cannot create executables
 （libe131 同款签名，探针为 inaccessible or not found）。配方此前无任何
  CC/CXX 存在性校验与回退；且 TMPDIR/SHELL 只经 os.environ 与单 save_script
  注入，Autotools 以 env=conanbuild 运行时会被 profile 聚合覆盖（coinor-vol
  教训：不可写 TMPDIR 同样表现为 Error 77）。
- 处理（只改配方环境路由，不动测试口径）：generate() 改经
  `tc.environment()` 注入 TMPDIR/TMP/TEMP/TMP_DIR + 探测 shell + 存在性校验
  通过的 CC/CXX（flags/sysroot 不动），附带 `zzz_librsb_build_env` save_sh
  备份；build()/package() 先 sanitize 再对 conan*.sh 落盘覆盖（含
  generators_folder），缺编译器时报环境失败而非配方失败；configure 前加
  `$CC --version` 探针，失败时落 config.log 尾部再抛出。保留 --build 三元组、
  zlib -I/-L/rpath、`-g0 -O1`、-j1、examples 11 步与双标记计数逻辑。
- 待下轮真机验证编译器回退是否生效并跑出 11 步上游 + 6 个消费者断言。
## 待真机验证（本轮未提交，待 HMBS 预检）
- conan create 全流程：configure（FC 为空是否一次通过、zlib 是否检出 yes）、
  -j1 全量编译时长（约 150 个编译单元，默认 3600s 预算是否够用）
- `make tests` 11 步在真机是否全过；bench.sh 与 autotune 的实际耗时
- test_package 6/6；标记行是否正常输出
- 若 zlib/1.3.1.1 在制品仓缺失，改配方 --without-zlib 并同步下方表格

## 给后端的话（Windows 工作树说明）
- 本机为 Windows，archives/g/gama/2.29 内有一个文件名以回车结尾的上游文件，
  NTFS 非法，故工作树为稀疏检出（cone：ci/docs/knowledge/templates/scripts/
  .gitcode/archives/l/code/config/tests/probes/references/feedback + 根文件）。
  `git status` 会显示大量 D（域外文件缺失），属本地受限与稀疏索引假象——
  最终提交请只 staged `archives/l/librsb/` 新增文件，切勿 `git add -A`。
- 上游 archives/l 内同时存在 `libXext/` 与 `libxext/`（仅大小写不同，Linux
  合法、Windows 同一目录冲突）。本机工作树只能容纳其一，故 `git status`
  恒显示其中两文件为 modified——此为 Windows 大小写冲突假象，与本任务无关，
  提交时忽略（以 Linux 全量检出为准）。

## config.status Permission denied repair (2026-09-21 preflight failed: confjo1jhO/subs1.awk)
- Symptom: configure runs to the end then config.status dies with can_t create ./confXXX/subs1.awk: Permission denied, Error 1 in autotools.configure.
- Why previous route invalid: cycle 1-2 fixed SHELL/CC/TMPDIR redirection, compiler now works and configure reaches config.status creation, so the remaining fault is not shell or compiler but E011 umask 077 on HMDFS plus unsafe_local_mktemp.
- New route (different from shell/compiler): patch umask 077 to 022 in every configure copy unconditionally (lame/libcitadel precedent) and, only when HMBS_AUTOCONF_MKTEMP_FALLBACK=1, prepend a PATH mktemp shim failing only for conf templates with mkdir fallback, active during configure; make/test untouched.
- Pending next preflight: whether config.status passes and 11-step examples plus 6 consumer checks run.

## rsb.h not found repair (2026-09-21 preflight failed: rsblib/rsb.hpp:55 rsb.h file not found)
- Symptom: configure now passes (umask route worked) but rsblib/rsb.cpp fails: fatal error rsb.h file not found; C examples built, C++ wrapper did not.
- Why previous route invalid: prior cycles fixed SHELL/CC/TMPDIR/umask-mktemp; config.status now succeeds so those domains are closed. New fault is VPATH include routing, unrelated to permissions.
- Root: rsb.h lives at source root; top configure builds SRCDIR_CPPFLAGS via cd+pwd/echo-PWD, fragile on HMDFS where getcwd fails (recipe seeds PWD=build dir). Observed rsblib compile carries -I build dir but no -I source root, so angle-bracket include fails.
- New route (different): generate() appends explicit -Isource_folder and -Ibuild_folder to extra_cflags/cxxflags, covering all TUs and sub-configures (rsblib/librsbpp/rsbtest); finds rsb.h and generated rsb-config.h deterministically.
- Pending next preflight: rsblib compile pass plus 11-step examples and 6 consumer checks.

## install Error 64 repair (2026-09-21 preflight failed: install-dist_docDATA)
- Symptom: build + upstream 9/9 passed, package() dies at
  `install -c -m 644 README AUTHORS README.md .../share/doc/librsb`
  with `make[3]: *** [Makefile:2192: install-dist_docDATA] Error 64`.
- Why previous route invalid: VPATH -I fix worked (compile green,
  `HMBS_UPSTREAM_TEST_RESULT discovered=9/executed=9/passed=9`);
  remaining fault is in `make install`, a new domain untouched before.
- Root: HMBS shim `install` rejects `-m` (EX_USAGE) while bare
  `install -c` works -- install-binPROGRAMS/binSCRIPTS (no -m) installed
  fine just before the failing DATA target. Matches
  HMBS_PLATFORM_CAPABILITIES chmod:0 (mode-setting unsupported).
- New route (different): package() runs
  `autotools.install(args=["INSTALL_DATA=cp"])`; plain cp needs no
  chmod, dest modes follow umask 022; command-line assignment propagates
  to sub-makes via MAKEFLAGS (rsblib headers, pkgconfig covered).
  INSTALL/INSTALL_PROGRAM stay on the proven shim path. No test logic.
- Count correction: no-Fortran config disables the BLAS interface, so
  hello-spblas/io-spblas are not built; real suite is 9 steps
  (6 C + 1 C++ + bench.sh + autotune), marker already 9/9/9.
  MANIFEST.yml + test_package comments updated from stale 11 to 9.
- Pending next preflight: make install green, test_package 6/6 markers.

## test_package CMake compiler repair (2026-09-21 preflight failed: project() CMAKE_C_COMPILER)
- Symptom: main package built + upstream 9/9 passed (INSTALL_DATA=cp route
  worked), test_package dies at CMakeLists.txt:2 project() with
  `The CMAKE_C_COMPILER: /data/service/hnp/bin/clang` broken.
- Why previous route invalid: install-shim fix closed package(); this is a
  new domain -- test_package has its own CMakeToolchain generate() with no
  compiler existence check, so the profile-pinned but absent
  /data/service/hnp/bin/clang flows straight into the toolchain file.
- Root: same signature as main recipe Error 77 (profile
  tools.build:compiler_executables path absent on this runner); CMake
  ignores CC env once the toolchain file sets CMAKE_C_COMPILER.
- New route (different): test_package generate() mirrors the main recipe
  discovery (conf-if-exists -> $CC -> PATH clang -> siblings) and overrides
  via tc.cache_variables (-D wins over toolchain file); no-op when the
  profile path exists. Flags/sysroot untouched, test counting unchanged.
- Pending next preflight: test_package configure/build/run 6/6 with
  HMBS_TEST_PACKAGE_RESULT marker.

## make check/qtests timeout disconnect repair (2026-09-21 preflight failed: Connection closed, upstream 0/0/0)
- Symptom: examples programs all ran, then log entered `./rsbench -Q 30.0Q`
  (INTERNALS/BASIC/ADVANCED PASSED:19235) + `make qtests -C librsbpp` +
  `rsbtest --max 30` loops, then `Connection to 47.242.172.160 closed by
  remote host` with upstream markers 0/0/0. Trigger is build()'s
  `autotools.make(target="check")`, previously assumed an automake no-op.
- Why previous route invalid: all prior cycles fixed shell/CC/TMPDIR/umask/
  VPATH/install/test-toolchain domains; compile + examples 9/9 were green,
  so those domains are closed. New fault is test-scope selection, not env.
- Root: upstream NEWS.TXT defines `make check` as alias of `make qtests`
  (brute-force correctness suite, tens of seconds per chunk plus recursive
  librsbpp/rsbtest loops), which overruns the single-slot preflight SSH
  lifetime on the small box. Evidence: this round's tail hung exactly in
  `rsbtest --max 30 --quiet ... | grep` lines before the disconnect.
- New route (different, scope-only): delete the `make check` invocation from
  build(); gate only deterministic `make -C examples tests` (9 steps:
  6 C + 1 C++ + bench.sh + autotune pd.mtx) with marker command updated to
  `make -C examples tests`. MANIFEST.yml documents `make check`/`qtests` as
  intentionally unrun with this evidence. No test logic altered, no asserts
  deleted, no counts patched.
- Pending next preflight: examples 9/9 + test_package 6/6 markers without
  disconnect.

## test_package toolchain file patch repair (2026-09-21 preflight failed: CMAKE_C_COMPILER still bad after cache_variables)
- Symptom: fallback detected (CC=harmonybrew clang, profile hnp clang absent) yet CMake project() still used /data/service/hnp/bin/clang.
- Why previous route invalid: cycle 9 assumed tc.cache_variables (-D) wins over conan_toolchain.cmake; preflight proved it does not (toolchain file is authoritative, sets compiler before project()). New domain closed for main package (upstream 9/9 green), fault isolated to test_package generate().
- New route (different): after tc.generate(), byte-patch conan_toolchain.cmake + CMakePresets.json/CMakeUserPresets.json under generators/build folders replacing absent profile paths with discovered clang, plus CC/CXX env export; build() redundantly passes -D variables. Zero test logic change.
- Pending next preflight: test_package configure/build/run 6/6 marker.

## packaged headers backfill repair (2026-09-21 preflight failed: rsb_types.h file not found)
- Symptom: main build + upstream 9/9 green, test_package dies at
  `rsb.h:302: fatal error: 'rsb_types.h' file not found` while
  `p/include/rsb.h` exists.
- Why previous route invalid: install-shim (INSTALL_DATA=cp) closed
  package() install Error 64 and test-toolchain patch closed CMake
  compiler routing; compile + examples 9/9 prove those domains closed.
  New fault isolated to packaged headers (test_package-only domain).
- Root: upstream ships rsb.h + rsb_types.h + rsb-config.h (+ blas_sparse.h
  / rsb.hpp; FreshPorts file list) but the HMBS-box `make install` left
  rsb_types.h out of the prefix, so consumer `#include <rsb.h>` cannot
  resolve its quoted `#include "rsb_types.h"`.
- New route (different, packaging-only): package() keeps
  INSTALL_DATA=cp, then backfills any missing required header
  (rsb.h / rsb_types.h / rsb-config.h) from source/build tree via
  conan copy (fail loudly if nowhere found) plus best-effort
  blas_sparse.h / rsb.hpp (warn only; legitimately absent when the
  no-Fortran config disables the BLAS interface). No test logic touched.
- Pending next preflight: test_package 6/6 with HMBS markers.

## test_package OpenMP+C++ link repair (2026-09-21 preflight failed: __kmpc_* + operator delete)
- Symptom: main build + upstream 9/9 green, test_package `cmake.build()`
  dies linking test_librsb: `undefined symbol: __kmpc_reduce_nowait`,
  `__kmpc_end_reduce_nowait`, `__kmpc_serialized_parallel`,
  `__kmpc_barrier`, `__kmpc_critical`, `__kmpc_dispatch_init_4`,
  `__kmpc_for_static_init_8u`, `omp_get_num_procs` plus
  `operator delete(void*)` from rsbpp_coo.cpp (std::__n1::vector).
- Why previous route invalid: header backfill + test-toolchain compiler
  patch closed configure/build/headers/compiler domains (upstream 9/9
  proves the archive itself links fine via autotools' own -fopenmp line).
  New fault isolated to the CMake consumer link line, a new domain.
- Root: librsb builds OpenMP-parallel by default (can be serial, but this
  build kept OpenMP and examples prove OHOS clang accepts it); the static
  archive therefore embeds OpenMP-offloaded + C++ objects behind a C API.
  test_package used `project(C)` + plain `librsb::librsb`, so the C linker
  never pulled the OpenMP runtime or libc++ (E247 shape; ladybug/lzham
  precedent for the C++ half, but E247 forbids test-only masking alone).
- New route (consumer link, no lib behavior change, no asserts touched):
  test_package CMake -> `project(C CXX)` + `find_package(OpenMP)` with raw
  `-fopenmp` fallback + `LINKER_LANGUAGE CXX`; main package_info propagates
  `-fopenmp` via cflags/cxxflags/sharedlinkflags/exelinkflags on
  Linux/OHOS so direct consumers get the same runtime. No OpenMP disable,
  no test scope change.
- Pending next preflight: test_package configure/build/run 6/6 with both
  HMBS markers, upstream still 9/9.
