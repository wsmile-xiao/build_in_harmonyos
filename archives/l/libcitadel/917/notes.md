# libcitadel 917 适配笔记

## 编译环境

- 构建系统: autotools (configure + make, 917 时代生成文件)
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: built (配方已完成, 待 HMBS 真机预检回填证据)
- 申请人: sheepss
- 队伍: 来都来了

## 上游信息

- 名称: libcitadel 917 (Citadel 共享工具库)
- 官方主页: https://www.citadel.org/
- 官方源码: http://easyinstall.citadel.org/libcitadel.tar.gz (滚动包, 无版本号)
- 本次版本锁定源: Debian 版本锁定 orig 包 (由上游 917 标签构建)
  - https://deb.debian.org/debian/pool/main/libc/libcitadel/libcitadel_917.orig.tar.gz
  - 备用: https://ftp.debian.org/debian/pool/main/libc/libcitadel/libcitadel_917.orig.tar.gz
  - 官方回退: http://easyinstall.citadel.org/libcitadel.tar.gz
- SHA256: d588cfe0d47cef8af75286492036c371d1b4e602f807f9d82b254fdd0f406ec2
  - 来源: PureOS/Debian dsc 双源一致 (libcitadel_917-5.dsc)
- 许可证: GPL-3.0-only (libcitadel.h 头部 GPLv3 声明, COPYING)
- 上游结构: configure (约 678KB 生成文件) + Makefile.in + configure.in + lib/ + tests/ + sysdep.h.in + libcitadel.pc.in
- 上游测试: 917-5 源码树含 tests/ 目录, 通过 make check 运行, 具体用例数待真机 conan create 日志回填

## 编译步骤

1. `get()` 解包 orig tarball (strip_root=True)
2. `generate()` 生成 AutotoolsDeps + AutotoolsToolchain, 默认静态 (`--disable-shared --enable-static`)
3. OHOS 下追加 `--build/--host=aarch64-unknown-linux-gnu` 兼容 2017 年 config.sub (vo-amrwbenc 前例)
4. `build()` 中将 configure 内 `umask 077` 放宽为 `umask 022` (HMDFS 任务根不可写, E011 模式)
5. `autotools.configure()`, `autotools.make(-j1)`, `autotools.make(check)`
6. `autotools.install()`, COPYING 拷贝至 licenses, 清理 *.la/*.dylib

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方滚动包无版本号, 无法锁定 917 | Citadel 使用 rolling release, easyinstall 只有最新包 | 使用 Debian 版本锁定 orig 包为主源, 官方 URL 保留最后回退, SHA256 双源校验 |
| 2 | 2017 年 config.sub 不认识 linux-ohos | 917 时代早于 OHOS 三元组 | --build/--host 覆盖为 aarch64-unknown-linux-gnu, 编译器仍为 Conan OHOS 工具链 |
| 3 | 本机 Windows 无法直连 Debian https | 环境 TLS 拦截, ftp.debian.org 不可达 | 配方提供 deb.debian.org + ftp.debian.org 双镜像, 真机预检验证可达性 |

## 依赖版本

- zlib/1.3.1 (制品仓 published, PureOS 记载 917 仅需 zlib1g-dev)
- 其余 Citadel 全家桶依赖 (Berkeley DB/libical/expat/curl/OpenSSL) 为 Citadel Server 依赖, 非 libcitadel 本体依赖, 不引入

## 验证结果

- 本地未运行 conan (按任务守则, 真机内执行)
- 待 HMBS 真机预检回填:
  - `HMBS_TEST_PACKAGE_RESULT` (test_citadel 真实计数)
  - `HMBS_UPSTREAM_TEST_RESULT` (make check 真实计数)
  - conan create 日志 SHA 与通过率
- 证伪计划: 检查测试输出非空, 必要时用 exit 1 桩确认 harness 能抓失败, 区分通过与静默跳过

## 源码修改

无补丁 (patches_applied 为空)

## 注意事项

- 本机 Windows 大小写不敏感导致 archives/l/libXext 与 libxext 目录合并显示脏状态, 与本任务无关, 未触碰
- 版本目录 917 为纯数字, 符合 conan slug (首字符允许数字)
- 库类型包, 无 commands.json (R38 仅工具包需要)
- PR 正文测试数字待真机 evidence 轮填写, 本轮不猜测

## 2026-09-16 preflight compile 失败复盘（第 2 次修复）

- 本轮失败证据（commentId -1789572162961）：`autotools.configure()`
  阶段 `configure: error: working directory cannot be determined`，前缀几百行
  getcwd 错误（连 `shell-init` 都报，说明 configure 实体工作开始前
  cwd 已不可用）；另有 `preflight.sh[306]: can't create temporary file
  /tmp/shbv9745.tmp: Read-only file system`（preflight 脚本自身，非配方）。
- 前次策略对比：失败预检跑的配方已含 `umask 077 -> 022`
  改写（E011），仍在同一位置失败，故 umask 不是本失败的
  唯一根因；本次采用不同策略，不再重复仅调 umask。
- 本次策略（复用 cyrus-sasl-login / zzuf 先例，无自创探测）：
  1. `layout()` 设 `self.folders.build = "."` 做 tree 内构建，绕开
     HMDFS 上脆弱的 out-of-source `build-release` 目录层级；
  2. configure/make/make-check 全程显式 `umask 022` + 可写 TMPDIR
     （HMBS 注入值优先，回退到源码树内 `tmp/`），
     不再碰只读 `/tmp`；
  3. 仅当 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 时前置 mktemp 影子脚本，
     其余情况零行为；
  4. `make check` 真实运行并解析输出，双通道输出
     `HMBS_UPSTREAM_TEST_RESULT`；test_package 输出
     `HMBS_TEST_PACKAGE_RESULT`（discovered=3，与test.c 的 3 行 contract
     PASS；MANIFEST assertion_count 由无依据的 10 修正为 3）。
- 若下轮预检仍报完全相同的 getcwd（且构建目录层级已是
  tree 内），则指向 preflight 基础设施（client 目录 GC / /tmp
  只读 / /proc 缺失均出现在 preflight.sh 自身），届时按守则报
  环境问题，不再 churn 配方。

## 2026-09-16 preflight loff_t compilation fix

- Failure: lib/libcitadel.c via lib/libcitadel.h:264-265 unknown type name loff_t on OHOS clang/musl.
- Fix: conanfile._fix_loff_t_for_musl inserts portable fallback after sys/types.h: typedef off_t loff_t guarded by !__GLIBC__ plus LIBCITADEL_LOFF_T_FALLBACK idempotence; called in build() before configure/make. No static patch, no test change.
- readonly_tmp platform note refers to preflight.sh itself (/tmp/sh*.tmp), recipe already uses injected TMPDIR; no recipe action.

## 2026-09-17 preflight upstream_test rc=2 修复（第 3 次修复）

- 本轮失败证据（commentId -1789578459251）：`HMBS_MAKE_CHECK_RC=2`，
  `HMBS_UPSTREAM_TEST_RESULT status:failed/discovered:1/executed:1`；
  preflight.sh 自身的 `/tmp/*.tmp: Read-only file system` 与
  `/proc/.../cmdline` 缺失为执行器脚本噪声（配方全程已用注入的
  TMPDIR），与本次失败无关。
- 根因（已证实）：917 顶层 Makefile.in 根本没有 `check` 目标
  （.PHONY 仅 buildlib/all/clean/distclean/install/uninstall；
  configure.in 无 TESTS 接线），故 `make check` 恒报
  `No rule to make target 'check'`、退出码 2；旧配方把“无目标”
  误判成“1 个用例失败”。佐证：上游镜像 tests/Makefile.in 含
  stringbuf/hashlist/mimeparser 等 9 个 CUnit 目标但顶层无 check；
  configure.in 仅 `AC_CONFIG_FILES(tests/Makefile)`。
- 修复（conanfile.py）：① `build_requirements()` 新增
  `tool_requires("cunit/2.1-3")`（本仓 archives/c 已发布，低成本补齐，
  仅构建期使用，不污染运行时依赖）；② 顶层 Makefile 含 check 目标
  时沿用旧路径，否则显式 `make -C tests`（CUnit 路径经
  `C_INCLUDE_PATH`/`LIBRARY_PATH` 注入，不动 configure 旗标；生成
  Makefile 若含 OHOS clang 不认的 `-dn` 则精确剔除该 token）；
  ③ 逐个运行构建出的测试二进制（CUnit 主程序无参直跑；mimeparser
  遍历 `testdata/mime`；xdg lookup 仅用树内文件；run_tests.sh 未调用
  的 socket IO helper 记 `omitted` 不计数、不算跳过）；④ 解析 CUnit
  `Run Summary`（优先 asserts 行）聚合 discovered/executed/passed/
  failed/skipped，双通道输出 marker，失败 raise；⑤ 交叉编译
  （`can_run==False`）仅编译不执行（barrier 前例），不伪造 marker，
  真机原生编译正常实跑。
- 待下轮预检验证：CUnit 工具依赖解析、tests/ 实际目标名与数量
  （917 包内容本地因 TLS 拦截无法直连 Debian 核对，以真机日志为准）、
  各二进制真实通过情况。若个别用例因 OHOS 缺失宿主文件失败，将按
  “缺什么”逐项处理，不跳过整个套件。

## 2026-09-17 upstream runner fidelity fix (same fingerprint, different strategy)

- Observed: preflight failed at `make check` rc=2 because the 917 top-level
  Makefile wires no `check` target; worktree already builds tests/ explicitly.
  Reviewing that pending fix against the real upstream runner
  (mingodad/citadel master libcitadel/tests/run_tests.sh + tests/Makefile.in)
  found fidelity gaps that would mis-fire on the next preflight.
- Root cause of gaps: plan ran mimeparser once per file (upstream runs
  -f, -p -f, -p -d -f plus a -P part loop), invented xdg -f inputs
  (upstream has two exact loops with -x/-i flags), omitted the piped
  `stringbuf_conversion_test -i` variant, and would have executed
  `stringbuf_stream_test` with no args (a stdin filter never invoked by
  run_tests.sh, would block until timeout).
- Fix (conanfile.py only): `_plan_upstream_test_runs` now mirrors
  run_tests.sh exactly (CUnit/manual no-arg mains, conversion plain +
  piped via testdata/emailaddresses, mimeparser triple matrix per
  testdata/mime file, xdg loops 1+2 with existence checks); missing
  sibling-webcit/host-icon inputs become logged `omitted`, not failures;
  stream/IO stay omitted with reasons. Execution feeds stdin files where
  needed, /dev/null otherwise (no blocking), and expands -P part runs
  dynamically by parsing `part=` lines like the shell sed. No test
  deleted, no asserts weakened, TMPDIR redirection kept.
- readonly_tmp diagnosis refers to preflight.sh itself (/tmp/sh*.tmp);
  recipe never touches raw /tmp (audited: no /tmp in tests/*.c runner
  paths). No recipe action beyond existing TMPDIR.

## 2026-09-17 preflight SSH drop keepalive fix

- Observed: preflight failed with Connection to 47.242.172.160 closed by remote host right after omitted lines, no test failure, no marker; preflight.sh /tmp and /proc warnings are executor-script noise (recipe uses injected TMPDIR).
- Root cause (recipe side): upstream runner buffered all test output until the end, leaving a long silent window on SSH; a slow/hung binary could look like a dead session (previous per-test timeout 180s worsened it).
- Fix (conanfile.py only): stream per-run start/done via output.info plus stdout flush (keepalive, no semantic change); per-test timeout 180s to 60s, timeouts still tallied as failures; -P part sub-runs stream the same way. No tests skipped, no asserts changed.

## 2026-09-17 preflight upstream_test 34 failed fix (112 discovered / 78 passed / 34 failed)

- Observed (commentId -1789588859378): HMBS_UPSTREAM_TEST_RESULT status failed,
  framework cunit, discovered 112 / executed 112 / passed 78 / failed 34.
  reason first-10: stripallbut_test (rc=0) + 9 mime_xdg_lookup_test -f ... -x
  (loop1 webcit siblings + loop2 bare names) + content run -f ./mimeparser_test.c.
  Omitted (8, honest, not counted): IO/stream helpers, conversion -i piped
  (no testdata/emailaddresses), mimeparser matrix (no testdata/mime), host icon
  dir, webcit sibling content inputs.
- Root cause A (mime, ~22 runs): 917 GuessMimeType/GuessMimeByFilename fall
  through to xdg_mime_* helpers; OHOS ships no /usr/share/mime database and no
  /etc/mime.types, helpers return NULL, tests printf("%s", NULL) then exit
  non-zero. Evidence: only mime-tagged binaries fail while CUnit mains using
  the same StartLibCitadel run fine; content run on existing file fails the
  same way (data path also hits xdg fallback). Upstream rolling already fixed
  this direction (hardcoded table + application/octet-stream fallback, never
  NULL) — verified in rolling tarball lib/mime_parser.c via local http fetch.
- Root cause B (stripallbut, 12 asserts): StrBufStripAllBut cuts at first '>'
  then cuts left unconditionally, while C stripallbut() only strips when first
  '>' sits at/after last '<'. Master-source simulation over the test's 12
  cases: C passes 12/12, old StrBuf passes 6/12 (cases 4,5,6,7,8,10 fail),
  guarded StrBuf passes 12/12. 12 asserts + 22 mime = 34, matches preflight.
- Fix (conanfile.py recipe-side source fixes, idempotent, logged, no static
  patch, no test weakened): _fix_mime_null_fallback_for_ohos wraps both xdg
  fallbacks with NULL -> "application/octet-stream" (LIBCITADEL_MIME_NULL_
  FALLBACK guard, no-op when patterns absent); _fix_strbuf_strip_guard_for_ohos
  mirrors C rb>=lb semantics in StrBufStripAllBut (LIBCITADEL_STRIP_GUARD,
  no-op when pattern absent). Both run in build() before configure/make.
- Falsification plan for next preflight: marker must show 112+/112+/0 failed;
  tail must contain real CUnit Run Summary + per-run Mimetype lines; if any
  mime run still rc!=0 the log line will show it (no silent skip added).

## 2026-09-17 preflight upstream_test xdg TIMEOUT fix (all mime_xdg_lookup_test rc=124)

- Observed (commentId -1789590641024): every mime_xdg_lookup_test run ends
  `rc=124` (`[TIMEOUT after 60s: ...]`) regardless of arguments, including
  `-x` by-extension runs on hardcoded extensions (test.txt/test.css/...) that
  never open any file; the SSH session then drops (`Connection closed by
  remote host`) because ~25 xdg runs x 60s each exceed the server idle window.
  No-arg CUnit mains pass; no marker is emitted.
- Root cause (verified against upstream source mingodad/citadel
  libcitadel/tests/mime_xdg_lookup_type.c L20/L38 and mimeparser_test.c
  L205/L221): both declare the getopt result as `char a` and loop
  `while ((a = getopt(...)) != EOF)`. On aarch64 the plain-char ABI is
  UNSIGNED, so EOF (-1) truncates to 255 and the loop never terminates: a
  busy infinite loop before any test logic runs. x86 (signed char) hides it,
  which is why upstream never noticed. Uniform hang on all xdg runs (even
  hardcoded-extension ones that never reach MIME/xdg code) is the signature;
  a MIME-data hang would differ between -x and content runs. mimeparser has
  the identical bug (unexposed: testdata/mime absent so no runs planned);
  stringbuf_IO_test.c / stringbuf_stream.c share it (built but omitted from
  the run plan). html_to_ascii_test.c and stringbuf_conversion.c already use
  `int a` (correct) and are untouched.
- Fix (conanfile.py recipe-side source fix, idempotent, logged): new
  `_fix_getopt_char_for_arm` rewrites lone `char a;` to `int a;` (getopt
  returns int by contract) in tests/{mime_xdg_lookup_type,mime_xdg_lookup_
  test,mimeparser_test,stringbuf_IO_test,stringbuf_stream}.c when the file
  contains getopt; verified against upstream master: exactly 4 files match
  (1 sub each), the 2 already-int files get 0 subs, `char chosen_part[128]`
  untouched, repeat application is a no-op. Called in build() with the other
  fixes. No test skipped, no assert weakened; 60s per-test timeout stays as
  safety net.
- Falsification for next preflight: xdg runs must finish in ~seconds with
  `Mimetype:` lines (not rc=124); marker expected back to counted
  pass/fail. If any xdg run still times out, the per-run start/done lines
  will show exactly which one (keepalive streaming already in place).

## 2026-09-17 test_package strbuf_plain FAIL fix

- Observed: HMBS_TEST_PACKAGE_RESULT executed true / passed false, discovered 3 / passedCount 0; log shows LIBCITADEL_TEST strbuf_plain FAIL then ConanException consumer test failed. Upstream suite already passed (112/112) so failure is isolated to test_package/test.c contract.
- Root cause (test bug, not library bug): test checked StrBufPlain(buf, citadel, 7) != 0, but upstream lib/stringbuf.c returns CopySize (7) on success and -1 only on error; return 7 therefore tripped the FAIL branch. Secondary latent bugs in same file: NewHash(1, Flathash) with string key len 7 (Flathash only valid for sizeof(int) keys, returns 0 otherwise) and Put of stack address with NULL destructor (DeleteHash would free() a stack pointer).
- Fix (test_package/test.c only, no recipe change): expect StrBufPlain == 7 with comment citing upstream return; NewHash(1, NULL) for string keys (hashlittle); heap-malloc marker owned by hash (NULL destructor frees it). PASS-line contract unchanged (3 lines), conanfile counting untouched.

## 2026-09-17 preflight evidence-incomplete fix (cache-hit, no rebuild)

- Observed (commentId -1789591755472): status incomplete / evidence stage,
  reason missing HMBS_UPSTREAM_TEST_RESULT, upstream 0/0/0/0/0, while
  `[preflight] conan create 通过` plus test_package 3/3 PASS. Stderr shows
  `libcitadel/917: Already installed!` for both zlib and libcitadel, i.e.
  conan reused the cached binary (RREV 70beddf7 unchanged: only
  test_package/test.c changed since the last build, which does not bump
  the recipe revision), so build() never re-ran and no fresh upstream
  marker was emitted. Not a code regression: the suite itself already
  passed 112/112 in the prior build.
- Root cause: upstream suite runs only in build(); cache-hit runs skip
  build() entirely, so the current-run stdout has no upstream marker and
  the hard gate reports incomplete. Any future test_package-only change
  would recur without a fix.
- Fix (honest, no asserts weakened, no skips added):
  1. conanfile.py `_write_upstream_result_json()` persists the real
     framework counts to hmbs-upstream-result.json in both marker paths
     (make-check and explicit tests/ cunit); package() copies it to
     share/libcitadel/hmbs-upstream-result.json. This also bumps RREV,
     forcing a fresh rebuild on the next preflight.
  2. test_package/conanfile.py test() re-emits the packaged build-time
     HMBS_UPSTREAM_TEST_RESULT (dual channel, validated discovered>0)
     after the real consumer run, with a log line stating the replay
     source; missing/invalid evidence fails honestly to force a rebuild
     instead of faking a pass.
- Falsification for next preflight: stdout must contain both markers;
  upstream numbers must equal the fresh build-time suite run (expected
  112+/112+/0 failed after prior mime/getopt/strip fixes); replay line
  must cite share/libcitadel/hmbs-upstream-result.json. If build reruns
  but counts differ, the fresh marker (not the replay) is authoritative.
