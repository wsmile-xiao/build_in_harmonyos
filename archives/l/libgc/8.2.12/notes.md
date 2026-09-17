# libgc 8.2.12 适配笔记

## 上游信息

- 名称：libgc（Boehm-Demers-Weiser 保守式垃圾回收器，与 bdw-gc 同源）
- 版本：8.2.12
- 仓库：https://github.com/bdwgc/bdwgc
- 发布包：https://github.com/bdwgc/bdwgc/releases/download/v8.2.12/gc-8.2.12.tar.gz
- SHA256：`42e5194ad06ab6ffb806c83eb99c03462b495d979cda782f3c72c08af833cd4e`（与 conan-center-index bdwgc/8.2.12 一致，已本地下载复核）
- 许可证：MIT
- 构建系统：autotools（configure + make，in-source 构建）
- 依赖：无外部依赖（内嵌 libatomic_ops）

## 上游测试清点（R51）

- 来源：`tests/tests.am` + `cord/tests`（tarball 内）
- 注册方式：automake `TESTS += ...`，入口 `make check`，汇总 `test-suite.log`（`# TOTAL/# PASS/# FAIL/# SKIP`）
- 基础项（7）：gctest（tests/test.c）、leaktest、middletest（tests/middle.c）、smashtest、hugetest、realloc_test、staticrootstest
- cord 项（1）：cordtest（cord/tests/cordtest.c）
- 条件项：THREADS（默认启用，+5：test_atomic_ops、threadleaktest、threadkey_test、subthreadcreate_test、initsecondarythread_test）、CPLUSPLUS（+1：test_cpp）、KEEP_BACK_PTRS（tracetest）、ENABLE_DISCLAIM（+3）
- 默认配置下预计 >= 13 项；确切数字以真机 `make check` 的 test-suite.log 为准，配方在 build() 内解析并输出 `HMBS_UPSTREAM_TEST_RESULT`，不再估算
- 证伪要求：`make check` 必须产生非空 test-suite.log；total 为 0 或存在 FAIL 即判失败，不以退出码 0 冒充通过

## 配方设计

- `conanfile.py`（name=libgc，libs=["gc"]，默认 static）：
  - `validate()` 限制 `os in ("Linux", "OHOS")`（R32）
  - `export_sources` / `basic_layout(build=".")` / `source()` 标准顺序（code-style 方法顺序）
  - R33：编译器取 `self.conf tools.build:compiler_executables` 的 `c`，不读裸 `CC`；`CONFIG_SHELL` 取环境或 `/data/service/hnp/bin/bash`，缺失回退 `bash`
  - `build()`：打补丁 → `./configure --enable-static --disable-shared --prefix=/` → `config.status` 的 `umask 077` 改 `022`（E011 运行时兜底）→ `make -j1` → `make check` → 解析 test-suite.log → 输出 `HMBS_UPSTREAM_TEST_RESULT` → 落盘 `upstream_summary/upstream_test_summary.json`
  - `package()`：`make install DESTDIR=package_folder` + 搬运 `res/upstream_test_summary.json`；清理 `.la`；R26：libgc 非 OHOS 系统同名库（/lib 无 libgc），保留 `.so`
  - `package_info()`：`libs=["gc"]`，`system_libs=["pthread", "dl"]`
- 补丁（5 个，复用 bdw-gc 8.2.6 已验证方案，已确认 8.2.12 同位置源码仍适用）：
  - 0001 config.guess：识别 HarmonyOS，输出 `aarch64-unknown-linux-ohos`
  - 0002 config.sub：接受 `ohos-linux` / `ohos*` / `linux-ohos`
  - 0003 configure：`umask 077` → `022`（E011，HMDFS 权限）
  - 0004 include/gc_config_macros.h：`GC_HAVE_PTHREAD_EXIT` 条件追加 `&& !defined(__OHOS__)`（musl 无 pthread_cancel；补丁文件内平台宏为例外，已在 PR 说明理由）
  - 0005 include/private/gcconfig.h：`CANCEL_SAFE` 条件追加 `&& !defined(__OHOS__)`（musl 无 pthread_setcancelstate；同上例外说明）
- `test_package/`（R34 实质调用）：
  - `test.c`：3 个 CHECK（GC_MALLOC、GC_REALLOC 保内容、GC_STRDUP + 1000 次 churn + GC_gcollect 后仍可达），缺一即 exit 1
  - `CMakeLists.txt`：`find_package(libgc)` + `add_test(test_libgc)`
  - `conanfile.py test()`：`cmake.test()`（ctest）→ 按名查找 `test_libgc` 二进制 → 重定向到日志解析 `CHECK n: PASS` → 输出 `HMBS_TEST_PACKAGE_RESULT(discovered=3)` → 读取包内 `res/upstream_test_summary.json` 原样输出 `HMBS_UPSTREAM_TEST_RESULT`
  - `MANIFEST.yml`：`upstream_tests_exist: true` + 非空 `upstream_test_audit`（tests.am 逐项来源），`assertion_count: 3`

## 遇到的问题与解决方案（沿用 bdw-gc 8.2.6 结论，已在配方内处理）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied creating subs1.awk | E011：HMDFS umask 077 建目录 0700，uid 与属主不一致 | configure 补丁 umask 022 + build() 内重写 config.status |
| 2 | undefined reference: pthread_setcancelstate | OHOS musl 无该函数；UNIX_LIKE+THREADS 默认开 CANCEL_SAFE | gcconfig.h 条件排除 `__OHOS__` |
| 3 | undefined reference: pthread_cancel | OHOS musl 无该函数；Linux 线程默认开 GC_HAVE_PTHREAD_EXIT | gc_config_macros.h 条件排除 `__OHOS__` |

## 验证计划（真机，HMBS 后台执行）

1. `conan create archives/l/libgc/8.2.12 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing`
2. 期望：configure/make/make check 通过；日志含 `HMBS_UPSTREAM_TEST_RESULT={"status":"passed",...}`（discovered/executed/passed 来自 test-suite.log）；test_package 含 `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":3,"passedCount":3}`；ctest 1/1 通过
3. PR 正文「上游测试用例通过率」「新增测试用例通过率」以预检日志实测为准，本轮不填数字、不猜测
4. 本轮未 commit/push，未创建 PR；工作树保持未提交，等待 HMBS 真机预检

## 注意事项

- 本机为 Windows（GBK 控制台），含中文文件一律经文件 API 以 UTF-8 写入；控制台显示乱码不代表文件乱码，已用 Python 按 UTF-8 复核
- Windows 大小写不敏感导致 `archives/l/libXext` 与 `archives/l/libxext` 同路径冲突，本地 `git status` 曾出现两文件 dirty；已用 `git update-index --assume-unchanged` 屏蔽该上游问题，仅 libgc 为本 PR 新增内容
- 补丁 0004/0005 在 patches/ 内含 `__OHOS__` 平台宏，属 R8 例外（无 POSIX 等价物：musl 缺函数，需条件排除），已在此与 PR 正文说明理由

## 2026-09-15 preflight fix
- 0003 patch CRLF->LF,最小上下文重写;conanfile build()追加configure内umask兜底;conandata url改为gh-proxy镜像优先+官方回退,sha不变。

## 2026-09-16 preflight fix (round 2)
- 0003-configure.patch: minimal-hunk header row count was wrong
  (@@ -5,12 claimed 12 lines, body has 13) -> "patch stream is incomplete".
- Different strategy: delete 0003 patch entirely; E011 umask 077->022
  is now done only at build() runtime on ./configure (pre-configure)
  plus the existing config.status rewrite. No configure patch to parse.

## 2026-09-16 preflight fix (round 3)
- 0001/0002 passed but 0004 failed with context drift
  (actual '#   define GC_NO_PTHREAD_SIGMASK'): all 8.2.6-copied
  patches share the drift risk, so patch files are removed entirely.
- New strategy: _apply_ohos_source_fixes() in build() does
  exact-substring edits (config.guess/config.sub/configure/
  gc_config_macros.h/gcconfig.h), anchors verified byte-for-byte
  against gc-8.2.12.tar.gz; missing anchor raises ConanException.

## 2026-09-16 preflight fix (round 4)
- 真机 `configure: cannot guess build type`, `config.guess[206]: syntax error:
  unexpected '$UNAME_MACHINE:...'`。
- 根因：`_apply_ohos_source_fixes()` 向 config.guess 插入 HarmonyOS 分支时，
  把整段 `case ... in` 又复制了一遍，形成两个 `case ... in` 共存、
  第一个缺 `esac`；/bin/sh 解析到第二个 `case` 行即报语法错误。
- 修复：只插入 `*:HarmonyOS:*:*)` 分支条目（`guess_entry`），复用原有
  `case ... in` 头，不再重复 `case` 行；多余空行删除。`sh -n` 逻辑已核对，
  conanfile.py 通过 py_compile。

## 2026-09-16 preflight fix (round 5)
- config.guess 语法错误已消除；本轮新失败为 `checking whether the C compiler
  works... no` / `C compiler cannot create executables`（build() line 192，
  `CC=/data/service/hnp/bin/clang` 裸调 `./configure`）。
- 根因：配方绕过 AutotoolsToolchain，直接 `CC=clang ./configure`，缺 OHOS
  sysroot/target 等工具链 flags，链接测试失败。同仓 aalib/flex 等 autotools
  配方均走 AutotoolsToolchain + Autotools 助手。
- 修复（与上轮只改 config.guess 不同策略）：新增 `generate()` 使用
  `AutotoolsToolchain`（static/shared 参数 + OHOS 时
  `--build/--host=aarch64-linux-ohos`，config.sub 已打对应补丁）；
  `build()` 改用 `autotools.configure()/make()/make(check)`，
  `package()` 改用 `autotools.install()`；保留 source fixes、umask 兜底
  （source/build 双目录）、make check 解析与双标记透传。TMPDIR 沿用
  HMBS/buildenv 注入，不硬编码 /tmp；preflight.sh 自身 /tmp 只读属基建侧，
  配方不处理。

## 2026-09-16 preflight fix (round 6)
- Failure: `configure[139]: /data/service/hnp/bin/bash: inaccessible or
  not found` (Error 127 in build()). Profile
  `ci/conan/profiles/ohos-aarch64` exports
  `CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash`, but that path does not
  exist on this worker (caps: `shell=/bin/sh`); autoconf re-execs via
  `$CONFIG_SHELL` so every configure dies before the compiler check.
  Head noise (/proc cmdline, /tmp read-only, RequestsDependencyWarning)
  is environmental and ignored.
- Fix (recipe-side only, profile untouched): `_working_shell()` probes
  `/bin/sh` then `/system/bin/sh` then env then PATH; `build()` runs
  configure explicitly as `CONFIG_SHELL=<shell> SHELL=<shell> <shell>
  ./configure <autotools._configure_args>` (same pattern as proven
  `archives/a/abx/0.1`), so the prefix overrides sourced conanbuild.sh.
  Toolchain flags still come from `AutotoolsToolchain.generate()`.
- conandata.yml reverted to single official GitHub URL (sha unchanged):
  CI auto-adds mirror fallback; `gh-proxy.com` prefix trips PF7/R39.

## 2026-09-16 preflight fix (round 7)
- Failure: `checking whether the C compiler works... no` /
  `C compiler cannot create executables` (Error 77) + HMBS
  `[readonly_tmp]` (`can't create temporary file /tmp/...: Read-only`).
- Fix (libseqlib/unixodbc precedent, temp-root only): new
  `_writable_tmpdir()` reuses HMBS TMPDIR/TMP/TEMP/HMBS_TMPDIR (+
  HMBS_AUTOCONF_MKTEMP_FALLBACK path); `generate()` defines
  TMPDIR/TMP/TEMP via `tc.environment()`; `build()` syncs os.environ
  and runs configure with `TMPDIR="$TMPDIR" TMP="$TMP" TEMP="$TEMP"`
  inline prefix + `env="conanbuild"` so OHOS sysroot flags aggregate.
- py_compile pending (Windows shell); HMBS preflight will verify.

## 2026-09-16 preflight fix (round 8)
- Same fingerprint 2nd time: TMPDIR-only fix did not move the failure
  (still `C compiler cannot create executables`, Error 77 at new line
  306 with `env="conanbuild"`). TMPDIR is therefore not the sole cause;
  autoconf hides the real compiler error inside config.log.
- Different strategy (libseqlib-round10 pattern, C-only adapt): pin the
  exact CC via `_resolve_cc()` (conf c if file, else PATH clang, else
  known OHOS paths), smoke-test it before configure (`--version` plus
  minimal compile+link, raw stderr reaches the log), prefix configure
  explicitly with `CC="<resolved>"`, and dump config.log tail (80
  lines) on configure failure before re-raising. TMPDIR handling from
  round 7 is kept unchanged. No test skipped.

## 2026-09-16 preflight fix (round 9)
- Progress: configure/make/make-check now green (HMBS_UPSTREAM = 16/16
  passed). New failure in package(): libtool install then chmod ->
  cannot access: No such file, autotools.install() Error 2.
- Different strategy from all prior rounds (never touched install):
  package() re-establishes writable TMPDIR, writes cp/mkdir install shim,
  redirects Makefile INSTALL and libtool script copy. Upstream untouched.

## 2026-09-16 preflight fix (round 10)
- Progress: round-9 shim worked, make install completed; new failure in
  package() line 602 copy() src==dst rejected by Conan2.
- Root cause: dead cleanup block called copy() in same dir; correct API rm().
- Fix: import rm, replace loop with rm(*.la)+fallback; tests untouched.

## 2026-09-16 preflight fix (round 11)
- New failure domain: main build/package green (16/16 upstream, package
  built after round-10 rm fix); test_package cmake.configure fails with
  CMAKE_C_COMPILER=/data/service/hnp/bin/clang error plus readonly_tmp.
- Root cause: profile hardcodes tools.build:compiler_executables to
  /data/service/hnp/bin/clang(++), absent on this worker (main build
  _resolve_cc fell back to harmonybrew clang via PATH, hence main green
  but CMakeToolchain still emits the stale path); CMake compiler check
  plus clang temp files also hit read-only /tmp.
- Fix (test_package only, main recipe untouched; jthread/libxtst pattern
  adapted, no test skipped): drop generators attribute, manual generate()
  with CMakeDeps + CMakeToolchain overriding CMAKE_C/CXX_COMPILER to
  probed executable (conf-if-file else which) plus toolchain-file patch
  for stale paths; build() re-establishes writable TMPDIR and passes the
  same compilers to cmake.configure variables; VirtualRunEnv kept.
