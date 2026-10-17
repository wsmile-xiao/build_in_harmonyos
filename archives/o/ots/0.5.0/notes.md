# ots 0.5.0 适配笔记

## 编译环境

- 构建系统: autotools（2007 年老式：configure.in + 预生成 configure）
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built（待真机预检验证，本轮未提交）

## 编译步骤

1. `conan get()` 下载 `ots_0.5.0.orig.tar.gz`（Debian 官方源 + Aliyun/Ubuntu 镜像回退，sha256 校验）。
2. 预生成 configure 直用，不跑 autoreconf（远端 automake 包连续两轮缺 bin dotfile 报 exit 126，改用工具包内现代 config.guess/sub 刷新 + E007 补丁）。
3. `tool_requires`：autoconf/2.72 + libtool/2.5.4（仅作 config 脚本刷新源与缺 configure 应急，不拉远端 automake）。
4. E007：刷新后的 config.guess/config.sub 打 HarmonyOS 识别补丁（官方 perl 工具优先，Python fallback）。
5. E114：configure 中 `umask 077` 改为 `umask 022`（含 `(umask 077 && mkdir $tmp)` 写法，HMDFS 可写性）。
6. OHOS 下用显式 shell 跑 configure：mksh 的 /bin/sh 把 heredoc 临时文件硬编码写 /tmp（只读 erofs），即使 TMPDIR 已设置也会失败；改用 TMPDIR 感知的 bash（无 bash 则退回 /system/bin/sh），并修正 configure/install-sh 等 shebang（osi/coinutils 同款）。
7. OHOS 下 out-of-source 构建目录 `ohos-work/`，configure 参数取工具链生成的 configure_args（prefix + `--enable-static --disable-shared --disable-gtk-doc`，不传 --build/--host，R15）；每条命令均带 `TMPDIR/TMP/TEMP` 前缀并 source conanbuild.sh；显式解析 CC/CXX 后先做编译冒烟。
8. `generate()` 同时提供 PkgConfigDeps（glib-2.0/libxml-2.0）与 AutotoolsDeps（popt 等 -I/-L/-l）；TMPDIR 经真实写入探测（makedirs + open(w) + unlink，HMDFS 下 os.access 不可信）后传递，失败时输出 config.log 首错窗口 + 尾部 + 编译冒烟以便定位。
9. `make -j1`（E074：并行 make 撞 HMDFS jobserver fifo EPERM）。
10. `make install`（OHOS 从 ohos-work 目录安装），清理 `.la` 文件，拷贝 COPYING 到 licenses；OHOS 下对 `bin/ots` 做 .codesign 自签名。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 2007 年预生成 configure/config 脚本不识别 HarmonyOS | GNU 官方脚本无 HarmonyOS 分支且过于陈旧 | 工具包内现代 config.guess/sub 刷新后再打 E007 补丁（不跑 autoreconf，避开远端 automake 缺 dotfile 的 exit 126） |
| 2 | autoreconf 远端包缺 bin dotfile（exit 126） | ohpcd automake 包的 bin/.aclocal-real 缺失 | 去掉 automake tool 依赖，预生成 configure 直用，仅应急缺 configure 时才试 autoreconf/autoconf |
| 6 | 本轮 configure 报 C compiler cannot create executables，但同 TMPDIR 下 cc 烟雾通过 | 默认 /bin/sh 为 mksh，heredoc 临时文件硬编码写只读 /tmp（preflight.sh 同报 /tmp 只读），与编译器本身无关 | OHOS 改用显式 bash（CONFIG_SHELL + shebang 修正）+ ohos-work 外置构建 + 每条命令 TMPDIR 前缀 + 显式 CC/CXX（osi/coinutils 同款）；config.log 改为首错窗口 + 尾部输出 |
| 3 | glib/libxml2 走 pkg-config，popt 走 AC_CHECK_LIB | 两种探测机制并存 | generate() 同时生成 PkgConfigDeps 与 AutotoolsDeps |
| 4 | doc/ 目录需 gtk-doc 工具链 | worker 无 gtk-doc/docbook | configure 加 --disable-gtk-doc |
| 5 | 上游无测试套件 | 2007 年项目仅有 articles 示例文本 | MANIFEST 声明 upstream_tests_exist:false + 审计说明；test_package 用真实摘要流水线验证 |

## 源码修改

无静态补丁文件（`patches: []`）。config.guess/config.sub/configure 的修改全部在 autoreconf 之后由配方运行时施加。

## 依赖版本

- glib/2.84.0.1（transitive_headers/libs）
- libxml2/2.15.3（transitive_headers/libs）
- popt/1.16（transitive_headers/libs）
- autoconf/2.72 + libtool/2.5.4（tool_requires，仅构建期；已去掉远端 automake 依赖）

## 验证结果

test_package `test_ots` 执行真实摘要流水线（parse → grade → highlight 50% → text/HTML 摘要），3 个检查点：

1. 解析产出行数与词数；
2. 评分产出非空标题；
3. text/HTML 摘要非空且短于原文（证伪：空摘要或等长输出即 FAIL）。

另有 `ots --version` CLI 烟雾测试。上游 `make check` 无目标（no-op），无上游测试可执行。

```bash
./test_ots
ots --version
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/ots | 文本摘要命令行工具 |
| lib/libots-1.a | 静态摘要库 |
| include/libots-1/ots/libots.h | C API 头文件 |
| lib/pkgconfig/libots-1.pc | pkg-config 元数据 |
| share/ots/ | 词干字典（dic/*.xml） |

## 注意事项

- 本机为 Windows，`archives/g/gama/2.29` 下存在文件名含回车符的上游文件，无法在本机完整检出；工作树为稀疏检出（不影响 `archives/o/ots/` 新配方，远端 Linux 环境不受影响）。
- `ots --version` 不依赖字典文件，可直接做 CLI 烟雾测试；常规摘要需 `share/ots/*.xml` 字典（已随包安装）。
- 真机预检通过前不 commit、不 push、不建 PR（本轮仅工作树）。

## 2026-09-19 configure LD path fix
- configure AC_TRY_RUN links shared glib/libxml2/popt then RUNs ./a.out; loader failed (libxml2.so.16/libgio/libglib not found) -> cannot run C compiled programs.
- fix: generate() adds VirtualRunEnv(scope=build); build/_build_ohos export LD_LIBRARY_PATH from host deps libdirs + prefix every configure/make/install command; source conanrun.sh when present.

## 2026-09-19 lld libxml2 shadowing fix
- preflight failed at cc smoke/configure: lld needed system libxml2 but LD_LIBRARY_PATH front-loaded conan libxml2.so.16 -> xml* symbol not found + Error 77.
- fix: drop global LD_LIBRARY_PATH export and conanrun.sh sourcing; add -Wl,-rpath per host lib dir via tc.extra_ldflags for conftest run; strip conan-home entries from LD before compile/make/install.

## 2026-09-21 configure shell order + diagnostics (uncommitted)
- preflight 2026-09-21 failed in configure (Error 1); cc smoke passed; log shows `OHOS configure shell: /system/bin/sh` (mksh) despite TMPDIR set.
- root cause (recipe logic): `_build_shell()` appended `/system/bin/sh` before the `shutil.which("bash")` fallback, so PATH bash was dead code; plus hmbs injects `SHELL=/bin/sh`, making the env-bash check a no-op. 2007 configure is heredoc-heavy; mksh hardcodes /tmp (erofs read-only).
- fix: probe PATH bash first, then well-known absolute bash paths, env bash, finally mksh fallback; detect pkg-config binary and export PKG_CONFIG via toolchain env; emit compact `OTS_CONFIGURE_FAIL_REASON=<first configure: error:>` one-liner so the hmbs focused summary preserves the real error next round.
- scope: no test changes, no configure semantics change; awaiting hmbs preflight re-run.

## 2026-09-22 E007 guess silent-miss + diagnostics (uncommitted, 3rd repair, different strategy)
- preflight 2026-09-21T03:35 failed in configure (Error 1); cc smoke passed; shell still /system/bin/sh (no bash on worker). ogg/1.1.1 passes with same mksh, so shell is not the blocker; no bash-search change this round.
- new root cause: refresh pulls 2024-vintage config.guess from autoconf package whose anchor layout differs from old 4-space NetBSD spelling, so HarmonyOS case silently never lands (log shows patched config.sub but never patched config.guess). With --build/--host omitted, unpatched guess yields uncanonicalisable triplet and 2007 configure exits 1.
- fix: robust guess patch with multi-anchor plus catch-all fallback (never silent), harmonyos acceptance in config.sub, OTS_CONFIG_GUESS probe after patch, configure.ac copy moved into emergency-only branch (avoids missing-aclocal rebuild), OTS_CONFIGURE_FAIL_REASON now falls back to last error-like line plus last checking line.
- scope: recipe-only; no test changes, no configure semantics change; awaiting hmbs preflight re-run.

## 2026-09-23 pkg-config missing (uncommitted, 4th repair, different strategy)
- preflight 2026-09-23T05:10 failed in configure (Error 1) with OTS_CONFIGURE_FAIL_REASON="configure:20082: error: Library requirements (glib-2.0 >= 2.0 libxml-2.0 >= 2.4.23) not met"; cc smoke passed.
- root cause: worker has no system pkg-config, and recipe had no pkgconf tool_requires, so PKG_CHECK_MODULES could never succeed despite PkgConfigDeps .pc files and PKG_CONFIG_PATH being exported. shutil.which fallback alone cannot create a binary.
- fix: build_requirements adds tool_requires pkgconf/2.2.0 (conancenter version); generate() resolves the pkgconf tool bindir/binary from dependencies.build and prepends PATH + defines PKG_CONFIG via toolchain env; _build_ohos_with_explicit_shell exports the same bindir/PKG_CONFIG in-shell after sourcing conan*.sh (defense in depth).
- scope: recipe-only; no test changes, no configure semantics change; SUPERSEDED by 5th repair below (pkgconf tool_requires unresolvable on ohpcd).

## 2026-09-23 pkgconf graph failure (uncommitted, 5th repair, removes tool_requires)
- preflight 2026-09-23T05:17 failed at graph resolution (compile never reached):
  "ERROR: Package 'pkgconf/2.2.0' not resolved: Unable to find 'pkgconf/2.2.0' in remotes.
  Required by 'ots/0.5.0'". The 4th repair made it worse: preflight checks only the ohpcd
  remote, which carries no pkgconf recipe (archives/p/pkgconf holds only a README).
- root cause: wrong fix layer. configure.in calls PKG_CHECK_MODULES(OTS, [glib-2.0 libxml-2.0])
  which reads preset OTS_CFLAGS/OTS_LIBS env first (pkg.m4 short-circuit), so no conan
  pkg-config binary is needed at all.
- fix: removed tool_requires pkgconf/2.2.0; added _ots_pkg_module_flags() aggregating
  OTS_CFLAGS (-I/-D + cflags) and OTS_LIBS (-L/-l incl. system_libs) over ALL host deps
  (superset is harmless for the probe); generate() exports them via toolchain env and
  _build_ohos_with_explicit_shell re-exports them in-shell after sourcing conan*.sh.
  PKG_CONFIG is set only when a system binary exists on PATH (diagnostics only).
  No dependencies.build["pkgconf"] reference remains.
- scope: recipe-only; no test changes, no configure semantics change; awaiting hmbs preflight re-run.

## 2026-09-23 pkg-config shim (uncommitted, 6th repair, corrects 5th assumption)
- preflight 2026-09-23T05:42 failed again in configure (Error 1) with
  OTS_CONFIGURE_FAIL_REASON="configure:20082: error: Library requirements (glib-2.0 >= 2.0
  libxml-2.0 >= 2.4.23) not met"; cc smoke passed; logs show OTS preset exported
  (CFLAGS_len=413 LIBS_len=309) but sys_pkg_config=None.
- root cause (corrects 5th repair): the 2007-vintage pkg.m4 baked into the pre-generated
  configure does NOT honor preset OTS_CFLAGS/OTS_LIBS (that short-circuit exists only in
  modern pkg.m4); it unconditionally execs "$PKG_CONFIG --exists/--cflags/--libs", and the
  worker has no system pkg-config/pkgconf binary, so the probe can never succeed.
  Evidence: preset lengths non-empty yet same "not met" error; generate-time which() is None.
- fix: added _write_ots_pkg_shim() writing a minimal POSIX-sh pkg-config shim answering
  --exists/--cflags/--libs/--modversion/--version with the conan-aggregated flags
  (glib 2.84 / libxml2 2.15.3 satisfy >= floors); generate() installs it into
  generators_folder and defines PKG_CONFIG as "sh <shim>" (no +x needed, HMBS chmod=0)
  plus PATH prepend for AC_PATH_TOOL fallback; _build_ohos_with_explicit_shell reinstalls
  it into writable work_folder, re-exports PKG_CONFIG/PATH after sourcing conan*.sh, keeps
  OTS_* exports as defense in depth, and smoke-probes the shim before configure.
  No pkgconf tool_requires (ohpcd has none); no dependencies.build["pkgconf"] reference.
- scope: recipe-only; no test changes, no configure semantics change; awaiting hmbs preflight re-run.

## 2026-09-23 Signal 9 empty-log audit (uncommitted, 10th repair, different strategy)
- preflight 2026-09-23T13:25 failed in compile with bare Signal 9; stdout/stderr tails empty, zero test counters. Previous round (SSH connection closed) used no-change wait, so this round must differ.
- audit: memory knobs already minimal (make -j1 everywhere, pre-generated configure with autoreconf skipped on hot path, tool_requires only autoconf+libtool, tiny test_package). No duplicate test runs to merge.
- fix (behavior-preserving, no test/semantics change): _refresh_config_scripts_from_tools no longer os.walk entire tool package trees on the hot path; share-rooted walk with hidden-dir prune, depth cap 4, candidate cap 20 (config.guess/sub always ship under share/). _dump_configure_diagnostics (failure path only) caps config.log read at 2MB.
- scope: recipe-only; configure/build/test semantics unchanged; awaiting hmbs preflight re-run.

## 2026-09-24 Signal 9 third strategy - cut compiler RSS + zero-walk + streaming diagnostics (uncommitted)
- preflight 2026-09-24T12:11 failed in compile with bare Signal 9; stdout/stderr tails empty, zero test counters. Previous round (bounded share-rooted walk + 2MB read cap) did not prevent OOM, so this round uses a different strategy.
- root cause: peak cc1/ld RSS on the small worker, not search cost; prior -j1 alone does not cap debug-info memory for glib/libxml2-linked conftest/ots objects.
- fix: (1) generate() appends -g0 -O1 -fno-unwind-tables to extra_cflags/cxxflags + MAKEFLAGS=-j1/CMAKE_BUILD_PARALLEL_LEVEL=1 via toolchain env and os.environ/source_prefix; (2) _refresh_config_scripts_from_tools removes os.walk entirely, probing only fixed share paths + single-level share fallback; (3) _dump_configure_diagnostics streams config.log line-by-line (71-line window + 60-line tail, <100KB) instead of read+splitlines.
- scope: recipe-only; configure/build/test semantics unchanged; awaiting hmbs preflight re-run.

## 2026-09-24 config.guess build-copy miss (uncommitted)
- preflight 2026-09-24T14:20 failed in configure: `b/config.guess: unable to guess system type` (2006-02-23 vintage), UNAME_SYSTEM=HarmonyOS, while recipe log showed source copy patched via NetBSD anchor.
- root cause: refresh found no modern scripts in tool packages (fixed list missed versioned share/res layouts) and patch/shebang/verify only covered source_folder; the executed <build>/config.guess stayed unpatched 2006 vintage.
- fix: _config_script_pairs now enumerates source/build/work roots + shallow source discovery; _refresh probes versioned share dirs + share/*/ glob and distributes to all roots; _patch/_verify/shebang cover all copies; build() syncs patched source scripts into build/work when dirs differ.
- scope: recipe-only; no test changes; awaiting hmbs preflight re-run.

## 2026-09-24 config.guess 2006-vintage语义修复 (uncommitted, 与上轮不同策略)
- preflight 2026-09-24T14:32仍失败：b/config.guess unable to guess system type。 distributed patch已生效（build-release/ohos-work shebang已修），但2006版脚本即使插入HarmonyOS分支仍失败。
- root cause：锚点块用GUESS=...（现代脚本语义），而2006脚本各分支直接echo+exit、从不读GUESS，分支落空到catch-all。
- fix：_patch_config_guess_python新增shebang后短路块（uname -s匹配Harmony即echo三元组+exit，不依赖任何版本分支语法）+锚点块改为echo+exit+旧GUESS块自动迁移；锚点判定改测*:HarmonyOS:*:*)避免被短路注释误跳过。本地仿真验证：新鲜/幂等/迁移三路径全过。
- scope: recipe-only；awaiting hmbs preflight re-run.

## 2026-09-24 config.sub 2006-vintage拒收三元组 (uncommitted, 与上轮不同策略)
- preflight 2026-09-24T14:38新进展：guess短路生效，configure推进到build system type检查，但2006版config.sub拒收：Invalid configuration aarch64-unknown-linux-ohos / machine aarch64-unknown-linux not recognized。
- root cause：旧锚点补丁全键控android时代文本（2006脚本中不存在，静默no-op却报already handles）+2006机器表早于aarch64（2013+）根本无此CPU。
- fix：_patch_config_sub_python新增shebang后ohos短路（任意*ohos*输入按首字段CPU规范化后输出*-unknown-linux-ohos）+basic_machine首位插入aarch64/arm64臂；锚点补丁保留作纵深；判定改测臂体避免被短路注释误跳过；_verify新增OTS_CONFIG_SUB探针；诊断降噪（跳过clang -V无害行，优先Invalid configuration/not recognized）。
- evidence：Git sh实测短路 aarch64/x86_64-unknown-linux-ohos与aarch64-linux-ohos均规范输出rc=0；仿真新鲜/幂等全过。
- scope: recipe-only；awaiting hmbs preflight re-run.

## 2026-09-25 package DESTDIR fix (uncommitted)
- preflight 2026-09-25T05:40 failed in package(): manual make install from ohos-work ran without DESTDIR, prefix=/ so libtool tried //lib/libots-1.la -> Read-only file system; fallback Autotools.install ran in build_folder (no Makefile there) -> No rule to make target install.
- root cause: manual install omitted DESTDIR while toolchain prefix is / (Conan stages via DESTDIR, osi/0.108.12 precedent uses make install DESTDIR=package_folder in work_folder).
- fix: package() OHOS path now runs make install DESTDIR=package_folder -j1 in ohos-work (primary and fallback both in work_folder); no test/semantics change.
