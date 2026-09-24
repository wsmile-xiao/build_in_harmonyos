# ViennaRNA 2.7.2 adaptation notes

## Scope

- Package: viennarna/2.7.2 (The ViennaRNA Package — RNAlib C library + standalone programs)
- Upstream source: ViennaRNA 2.7.2 release tarball (official GitHub release asset)
- Source URL: https://github.com/ViennaRNA/ViennaRNA/releases/download/v2.7.2/ViennaRNA-2.7.2.tar.gz
- Source SHA-256: `4cb7aaca00dfac92cb36b030c9111487c170b90568759bd4ffedd8318cc9384f`
- Build system: autotools (configure + make), mandatory C++17 (bundled dlib-20.0)
- Delivered: static `libRNA.a` (upstream `libRNA_la_LDFLAGS = -static`) + RNAlib headers (include/ViennaRNA) + pkg-config `RNAlib2.pc` + executable programs (RNAfold, RNAcofold, RNAalifold, ...)
- Reference recipes: archives/l/libuuid/2.42.2 (autotools OHOS: config.guess patch + E011 in-recipe umask + awk/TMPDIR), archives/g/gsl/2.7-2.8 (config.sub ohos), archives/c/check/0.15.2 (check framework dep)

## Adaptation

- Conan Autotools recipe, static library (upstream forces static; shared rejected in validate).
- Requires `check/0.15.2` — only to link the 10 C-library unit tests (`PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])`). The checkmk-generated `.c` files are already shipped in the tarball, so no checkmk build tool is needed.
- Configure flags (see conanfile.py):
  - `--build`/`--host` derived from Conan settings (aarch64-unknown-linux-gnu)
  - `--without-python --without-perl --without-swig` (scripting interfaces are separate deliverables)
  - `--without-gsl --disable-mpfr` (optional numeric deps kept off, lean build)
  - `--without-svm` (avoids `-lstdc++` which does not resolve on OHOS libc++)
  - `--without-forester --without-kinfold --without-rnalocmin` (sub-packages out of scope)
  - `--disable-lto --disable-openmp --disable-vectorize --disable-simd` (toolchain stability)
  - `--without-doc` (E: reference manual build; see below)
  - C-library unit tests + executable tests stay ON (defaults)

### Reference manual build break (patches/0003-Makefile.in-no-doc.patch)

- Symptom (real-device preflight): top-level `make -j1` fails in
  `doc/doxygen` with
  `make[2]: *** No rule to make target 'xml/*', needed by 'all-am'.  Stop.`
- Root cause: `doc/doxygen/Makefile.am` lists `noinst_DATA = xml/*` inside
  the `if WITH_REFERENCE_MANUAL` block. With no `doxygen` binary the nested
  `WITH_REFERENCE_MANUAL_BUILD` conditional is false, so the rule that builds
  `xml/*` is never emitted -> "No rule to make target 'xml/*'".
- Why `--without-doc` is NOT enough (verified empirically: after
  `configure --without-doc`, `config.status` still has
  `WITH_REFERENCE_MANUAL_TRUE=""` i.e. the conditional stays TRUE, and the
  generated `doc/doxygen/Makefile` still contains `REFERENCE_MANUAL_FILES_XML
  = xml/*`). configure only toggles the `with_doc_pdf`/`with_doc_html`
  sub-drivers and the code path that would set `with_doc=no` is guarded by
  `if test "x$with_doc" = "xyes"`, which is already false once `--without-doc`
  has set it to `no`, so that re-affirmation never runs.
- Fix: `patches/0003-Makefile.in-no-doc.patch` removes `doc/doxygen` and
  `doc` from the top-level `Makefile.in` `SUBDIRS` list, so `make` never
  recurses into the documentation directories at all. `--without-doc` is kept
  (harmless) so configure does not attempt to regenerate the manuals. The
  reference manual is not part of the delivered C-library + programs package
  anyway (requires doxygen/sphinx-build/pdflatex, all absent on the OHOS build
  host). Unit tests (make check, live in `tests/`) are unaffected.
- Verified locally: after patching Makefile.in, `configure` + `make` complete
  and no `doc` directory is entered (no `xml/*` failure).

### OHOS specifics

- In-recipe content-anchored OHOS recognition (conanfile.py `_apply_ohos_gnu_config_patches`): teach config/config.sub the `ohos*` basic OS and `linux-ohos*` kernel-OS combos (recognizes `aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`, verified locally) and add a HarmonyOS branch to config/config.guess (defensive; --build/--host are explicit). Replaces the former `0001`/`0002` unified-diff patch files (removed after a drifted-source patch-abort, see Round 2026-09-19 (2)).
- E011: configure `umask 077` → `umask 022` in-recipe sed so HMDFS temp dirs are writable; TMPDIR additionally pointed at `<build_folder>/tmp`.
- E052/shell_getcwd: conan cache parent directories are inaccessible to `getcwd()` on HMDFS, causing bash's `pwd` to fail with "working directory cannot be determined". Fix: (1) `os.chdir(self.build_folder)` + set `os.environ["PWD"] = self.build_folder` before configure runs, (2) patch configure's `ac_pwd=\`pwd\` && test -n "$ac_pwd"` check to fallback to `$PWD` when `pwd` fails. Same pattern as aribb24/libuuid.
- AWK / DIFF located explicitly (configure requires awk; executable tests require diff).

## Upstream tests

tests/Makefile.am registers (automake TAP harness, `make check`):

| category | switch | test entries | TAP assertions | source |
|----------|--------|--------------|----------------|--------|
| C-library unit tests (Check) | WITH_CHECK | 10 | 0 (check's own non-TAP format) | energy_evaluation, constraints, constraints_soft, ensemble_defect, fold, utils, eval_structure, walk, neighbor, hash_table |
| executable-program tests | WITH_EXECUTABLE_TESTS | 9 | **83** | RNAfold/{general,partfunc,special,long}, RNAcofold/{general,partfunc}, RNAalifold/{general,partfunc,special} |
| **native total** | | **19** | **83** | |
| Perl interface tests | WITH_PERL_TESTS | 14 | — | not packaged (separate Perl binding component) |
| Python2 interface tests | WITH_PYTHON2_TESTS | 15 | — | not packaged |
| Python3 interface tests | WITH_PYTHON_TESTS | 17 | — | not packaged |

- The 10 C-unit `.c` files are pre-generated by checkmk and shipped in the tarball (build-time checkmk not needed; only the check library at link time via `@CHECK_LIBS@`).
- The 9 executable TAP scripts run the built programs against `tests/data` and diff against `tests/RNA*/results` reference outputs; they require `DIFF` and `RNAfold --version` == CURRENT_VERSION (2.7.2). Their TAP assertion plans sum to **83** (14+3+21+2+14+6+17+2+4).
- Python/Perl interface tests (46+14) belong to the separately-delivered scripting-binding components and are auto-disabled here (`--without-python/perl/swig`).
- **统计单位（round 3 修正）**: the HMBS rule4 evidence gate measures this `make check` at the **TAP-assertion unit**, so `upstream_test_total = 83` (the 83 TAP `ok`/`not ok` result lines from the 9 executable scripts). `make check` also registers 19 test entries (10 Check C-programs + 9 TAP scripts), but the 10 Check programs report in check's own non-TAP format and add no TAP assertion lines; the gate's real-device ground truth is `发现 83 / 执行 83 / 通过 83` (0 failed, 0 skipped), matching upstream_test_total=83. Earlier rounds wrongly declared 19 (test-entry口径 of `test-suite.log # TOTAL`), which the rule4 gate rejected as "数量不一致" (19 ≠ 83).

### Local run

`make check` executes in `build()` during `conan create` (Layer 1). After `make check`, the recipe emits the `HMBS_UPSTREAM_TEST_RESULT` marker by counting the TAP `ok`/`not ok` result lines in the per-test `.log` files that automake's tap-driver writes under the tests build dir (a single deterministic source; we never count stdout or derive numbers by subtraction). This yields `discovered=83, executed=83, passed=83, failed=0, skipped=0` for the passing suite, matching the rule4 ground truth. The 10 Check-framework programs emit no TAP `ok` lines; a Check failure makes `make check` return nonzero and aborts build() before the marker runs, so `status:"passed"` here implies the whole suite passed. If no per-test `.log` files are found, the recipe reports the marker truthfully (`status:"failed"`, zeroed counts, a specific reason) and aborts instead of inventing numbers.

The test_package consumer also emits `HMBS_TEST_PACKAGE_RESULT` (`discovered:1`, `passedCount:1`) after the single `test_viennarna` binary self-reports its 4 assertions and exits nonzero on failure.

## test_package

CMake CONFIG-mode consumer test (test_viennarna.c): links the installed static libRNA.a via the C++ linker (LINKER_LANGUAGE CXX, since dlib C++ objects are embedded), and calls the real RNAlib v2 API — `vrna_fold_compound` + `vrna_mfe` folds `CGCAGGGAUACCCGCG` and checks 4 invariants (structure length, valid dot-bracket chars, negative MFE, reference fold `(((.(((...))))))`). Prints `RESULT: N/N assertions passed`, exits nonzero on failure.

## Local Validation

- `python3 -m py_compile` for conanfile.py + test_package/conanfile.py.
- Both patches verified with `git apply --check` on the pristine ViennaRNA-2.7.2 tarball.
- `./config/config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos` (patched config works).
- Real-device preflight (conan create on HarmonyOS aarch64) is executed by the HMBS backend.

## 依赖版本

- `check/0.15.2`（仅 C 库单元测试链接用）
- 无其它外部运行依赖（GSL/MPFR/SVM/Python/Perl/SWIG 均禁用）

## Round 2026-09-19 preflight failure — NOT a recipe defect (environment issue)

Real-device `conan create` failed during compile stage with:

    Error in Conan initialization: [conf] 'tools.env:defines' does not exist
    in configuration list. Run 'conan config list' to see all the available confs.

Diagnosis (evidence-based):

1. "Error in Conan initialization" is raised ONLY by ConanAPI() construction
   (conan/cli/cli.py -> ConanAPI() try/except) while loading the CONAN_HOME
   global configuration (global.conf / default profile / remotes) at CLI
   startup — BEFORE any conanfile/generate()/build() code runs. Verified in
   both Conan 2.29.1 (local) and 2.30.0 source.
2. `tools.env:defines` is a LEGACY Conan 1.x env-conf name. It is NOT
   referenced anywhere in Conan 2.29.1 or 2.30.0 source, and it is NOT in the
   BUILT_IN_CONFS registry of either version. The recipe (viennarna
   conanfile.py) likewise never reads or writes `tools.env:defines`; it only
   uses `tools.build:compiler_executables` (registered conf, dict access — the
   E6340-approved form).
3. Therefore the conf line must live in the HMBS CONAN_HOME global config
   (global.conf or default profile) on the real device. The deployed conan 2.x
   rejects it at initialization.

Conclusion: this is an environment/config issue in the HMBS conan-home
(legacy `tools.env:defines` conf present in its global.conf/profile), NOT a
viennarna recipe problem. No recipe change can influence a conan start-of-
command global-config load. Action: leave working tree unchanged (no
fabricated patch); the conan-home global config must be cleaned of the
`tools.env:defines` line (or recreated fresh) before conan create can run at
all. re-run preflight after conan-home config fix.


## Round 2026-09-19 (2) config patch fragility — "Failed to apply patch 0001-config.sub-ohos.patch"

Real-device preflight `conan create` aborted in `build()` at
`apply_conandata_patches` (line 169) with:

    WARN: .../0001-config.sub-ohos.patch:   actual  : b'\t\t;;'
    .../0001-config.sub-ohos.patch: source file is different - b'config/config.sub'
    ConanException: Failed to apply patch: .../0001-config.sub-ohos.patch

Evidence / diagnosis:

1. The source archive is pinned by sha256
   `4cb7aaca00dfac92cb36b030c9111487c170b90568759bd4ffedd8318cc9384f`. We
   downloaded the exact official release asset, verified the sha, and both
   GNU `patch -p1` and conan's `patch_ng` (strip=0, root=source_folder, the
   exact semantics `apply_conandata_patches` uses) apply 0001 cleanly to its
   `config/config.sub`, producing `sh config/config.sub aarch64-linux-ohos` ->
   `aarch64-unknown-linux-ohos`.
2. `patch_ng` with `fuzz=False` treats "already patched" as success (returns
   True) and only reports "source file is different" as a hard error when the
   file's content at the hunk offsets genuinely differs from the patch's
   context. The device's `config/config.sub` therefore differs from the
   pinned official archive (i.e. the source tree the real device downloads
   carries a drifted / different-generation config script).
3. Conclusion: the two OHOS config scripts (config.sub + config.guess) were
   keyed to the exact line offsets / context of the official tarball, so any
   config-script drift in the fetched archive makes the unified-diff patch
   application abort and kill the whole build — before compile and tests.

Fix (implemented in conanfile.py):

- Removed `0001-config.sub-ohos.patch` and `0002-config.guess-ohos.patch`
  from conandata.yml (deleted the files), keeping only
  `0003-Makefile.in-no-doc.patch` (verified to apply cleanly via patch_ng).
- Added `_apply_ohos_gnu_config_patches()`, called from `build()` right after
  `apply_conandata_patches()`. It applies the OHOS recognition to
  config/config.sub and config/config.guess with **content-anchored,
  idempotent, generation-aware** string replacements (keyed on stable
  substrings present across 2023-era and 2024+ config scripts, not on line
  offsets):
  - config.sub: add `ohos*` to the basic-OS list AND `linux-ohos*` to the
    kernel-OS combo list (both generations supported). Both are required for a
    correct `aarch64-unknown-linux-ohos` (knowledge
    DRAFT-autotools-config-sub-silent-ohos-triplet).
  - config.guess: insert the `*:HarmonyOS:*:*` -> `<mach>-unknown-linux-ohos`
    branch after the main case selector (same output as the old 0002 patch).
  - Each edit is guarded by a marker so a re-run never duplicates it.
- Because the recipe forces explicit `--build/--host = *-unknown-linux-gnu`
  triplets (libuuid pattern), configure never passes an `ohos` value, so OHOS
  recognition in config.sub/config.guess is *defensive*; a missing anchor is
  therefore logged as informational, never as a build failure. This is what
  turns the previous hard patch-abort into a non-fatal, self-adapting edit.
- Locally verified: patched pinned files give `config.sub aarch64-linux-ohos`
  -> `aarch64-unknown-linux-ohos` (exit 0); `config.guess`/`config.sub` pass
  `sh -n`/`bash -n`; re-running the patcher is a no-op (idempotent); a
  synthesized drifted config.sub (no anchor matches) is left untouched and the
  build proceeds (non-fatal).


## Round 2026-09-20 (2) make check tap-driver fd-3 failure (E553) — SHELL=/bin/sh override

Real-device `conan create` failed at the upstream test stage (compile phase,
Layer 1 `make check`) with the automake TAP-driver fd-3 breakage:

    config/tap-driver.sh: line 141: 3: Bad file descriptor
    sh: >&3 : bad file descriptor
    gawk: cmd. line:391: (FILENAME=- FNR=3) fatal: print to "cat >&3" failed: Broken pipe
    tap-driver.sh: fatal: I/O or internal error
    make[4]: *** [Makefile:1371: RNAfold/general.log] Error 1
    make: *** [Makefile:740: check-recursive] Error 1

Root cause (matches knowledge DRAFT-E553-ohos-bash-fd3-pipeline-tap-driver):
the conan profile buildenv injects the OHOS hnp GNU bash 5.3
(aarch64-unknown-linux-ohos port) as `$(SHELL)`. That bash port has a
file-descriptor inheritance defect: a group-command fd redirection does NOT
propagate into the command's pipeline elements, so the automake tap-driver
main structure `{ (test) | awk '{ print | "cat >&3" }' } 3>"$logfile"` fails —
awk's `cat >&3` dies, no TAP output reaches the .log, and tap-driver flags the
test ERROR ("missing test plan"). `make check` aborts (Error 1), the
ConanException surfaces before the test marker is emitted, and the whole
`conan create` fails at the compile stage.

Fix: run `make check` with a command-line variable override so it executes
under `/bin/sh` (mksh, correct fd inheritance):

    autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])

A make command-line variable assignment wins over the Makefile builtin and the
env aggregate; no Makefile or global profile change is needed. Command-line
override is preferred over `os.environ["SHELL"]="/bin/sh"` because the env
aggregate order could re-inject the profile bash.

The test marker (`_emit_upstream_test_marker`) parses only tests/
test-suite.log `# TOTAL / # PASS / # FAIL / # SKIP` block (deterministic single
source), matching declared upstream_test_total=83 (autotools_tests, TAP-assertion口径
after round 3; the 9 executable TAP scripts emit 83 ok/not ok lines). With all tests
run under /bin/sh the expected result is discovered=83, executed=83, passed=83,
failed=0, skipped=0, status=passed (this supersedes the earlier test-suite.log # TOTAL
test-entry口径 of 19, which the rule4 gate rejected as 数量不一致 against its measured 83).

## Source download reliability fix (2026-09-20)

Real-device preflight: compile stage failed at source() because the recipe
downloaded the official release tarball directly from github.com, which timed
out on the device:
  HTTPSConnectionPool(host='github.com', port=443): Connection to github.com timed out. (connect timeout=30)
and after a 5s retry the single-connection preflight was rejected by the SSH
gateway (global circuit-breaker 60s).

Root cause: conandata.yml had a single scalar `url:` pointing only at the
official GitHub release asset. conanfile.py.source() tries each URL at most
once, so a github.com connect timeout = source() failure -> compile-stage
failure with no fallback.

Fix (conandata.yml only, reuses the repo's maintained mirror mapping):
- Changed the scalar `url:` to an ordered list, mirror first then official:
    1. https://gh-proxy.com/https://github.com/ViennaRNA/.../ViennaRNA-2.7.2.tar.gz
    2. https://github.com/ViennaRNA/ViennaRNA/releases/download/v2.7.2/ViennaRNA-2.7.2.tar.gz
- gh-proxy.com is exactly the mirror that ci/conan/build_and_test.sh
  get_mirrors() selects for github.com URLs (verified '2026-08-06: only
  gh-proxy.com usable'), so this matches what the CI mirror-rewrite would
  produce.
- sha256 (4cb7aaca...) is UNCHANGED for every mirror.
- conanfile.py.source() already iterates the list and returns on first
  success; raising ConanInvalidConfiguration only after all mirrors fail. No
  conanfile.py change needed.

## Round 2026-09-20 (3) make install pkginclude header batch — host install shim Error 64

Real-device `conan create` now passes build + upstream `make check` (E553
SHELL=/bin/sh override), but `package()` failed at `autotools.install()` in
`install-pkgincludeHEADERS`:

    make[4]: *** [Makefile:2805: install-pkgincludeHEADERS] Error 64
    ... <~40 RNAlib headers> ... '/storage/.../p//include/ViennaRNA'
    make: *** [Makefile:740: install-recursive] Error 1
    ERROR: viennarna/2.7.2: Error in package() method, line 419
        autotools.install()
        ConanException: Error 2 while executing

Root cause (matches the postgresql-18.3 / cracklib2 / cyrus-sasl knowledge):
the OHOS host `PATH` is fronted by an `install` shim (in `$HOME/usr/local/bin`)
that mishandles autotools' install argument forms. `install-pkgincludeHEADERS`
issues one batch `$(INSTALL_HEADER)` call with all the RNAlib headers and a
single trailing `dir/` destination; the shim cannot handle the multi-source
batch and returns Error 64, killing `make install`.

Fix: bypass the host install shim by driving `make install` with the INSTALL*
variables pointed at the automake-bundled `config/install-sh` (same proven
pattern as cracklib2/2.9.6 and cyrus-sasl/2.1.28.1):

    make install DESTDIR=<package_folder> -j1 \
      MKDIR_P="/bin/sh <install-sh> -c -d" \
      INSTALL="/bin/sh <install-sh> -c" \
      INSTALL_PROGRAM="/bin/sh <install-sh> -c" \
      INSTALL_DATA="/bin/sh <install-sh> -c -m 644"

Note (cracklib2 pitfall, honored): use `/bin/sh`, NOT `/system/bin/sh` — old
libtool (ViennaRNA 2.7.2 era) only recognizes `/bin/sh .../install-sh -c` as an
install command and otherwise mis-parses install-sh itself as a file to
install. The modern automake-1.16 install-sh (ViennaRNA 2.7.2 bundle) handles
the multi-file header batch correctly (installs every file, unlike the vintage
X11R5 single-file one, cf. E574).

- Added `_find_install_sh()` (walks source_folder / base_source_folder /
  build_folder for `install-sh`).
- `package()` now uses the install-sh-driven `make install` when an install-sh
  is found, else falls back to `autotools.install()`.
- `*.la` cleanup and `license.txt` copy unchanged.

The E553 fix (SHELL=/bin/sh on `make check`) from the previous round is retained
and is what let the upstream tests actually run in this round (PASS lines for
RNAfold/special etc. appeared before the install failure).

## Round 2026-09-20 (4) rule4 上游计数不一致 — 改用 TAP-assertion 口径（83）

真机预检（evidence 阶段）连续多次被 rule4 拒绝，原因“上游计数缺失、非法或执行/通过/失败数量不一致”，
真机摘要固定为“上游测试：发现 83，执行 83，通过 83，失败 0，跳过 0”（命令 make check）。

根因（源码 + 本地 automake 复现实证）：
1. ViennaRNA 的 `make check` 是“双框架”混跑：9 个可执行 TAP 脚本（RNAfold/RNAcofold/RNAalifold）
   输出 **83** 条 TAP `ok`/`not ok` 断言行；10 个 Check 框架 C 程序（energy_evaluation 等）输出
   check 自己的非 TAP 格式（“100%: Checks: N...”），不产生 `ok` 行。
2. 早期球次的标记读取 automake `test-suite.log` 的 `# TOTAL/# PASS/# FAIL/# SKIP` 汇总块，得到的是
   **测试条目**数 19（10 Check + 9 脚本）；并在 MANIFEST 声明 upstream_test_total=19。
3. 本地用 automake 1.16.5 最小工程复现确认：`test-suite.log` 的 `# TOTAL` 统计的是测试条目数
   （3 个 TESTS 项 → TOTAL: 3），而不是 TAP 断言数。
4. 但 HMBS rule4 门禁对这条 make check 的“发现数”以 **TAP 断言**为单位实测为 83。于是
   marker/声明（19）与真机地面真值（83）不一致 → rule4 判“数量不一致”，本轮前连续否决。

修复（本轮，与既往球次不同的策略）：
- conanfile.py `_emit_upstream_test_marker()` 不再读 test-suite.log 的 `# TOTAL`，改为统计
  automake tap-driver 写入的**逐测试 `.log` 文件**里的 TAP `ok`/`not ok` 结果行（唯一确定性来源，
  非 stdout 计数字样、无减法推导）；通过 make check 后的确定性结果为
  discovered=83, executed=83, passed=83, failed=0, skipped=0, status=passed。
  - Check 框架 C 程序不产生 TAP `ok` 行 → 对计数贡献 0；若其失败，`make check` 返回非零，
    `autotools.make(target="check")` 使 build() 中止，标记根本不会走到，故此处 `status:"passed"`
    隐含整套 make check 通过。
  - TAP `ok ... # SKIP` 计入 skipped，不计 passed；ViennaRNA 无跳过。
- test_package/MANIFEST.yml：`upstream_test_total` 19 → **83**，`upstream_test_count_method`
  保持 autotools_tests，并在注释里说明 NOTE：make check 同时注册 19 个测试条目，但 rule4 以
  TAP 断言为统计单位，故声明 83。
- notes.md / manifest.yaml / .hmbs/pr-body.md 同步把上游总数与口径改为 83。

本地验证：py_compile 通过；用合成 per-test .log（9 脚本按 14/3/21/2/14/6/17/2/4 的 ok 行 +
10 个 check 风格 .log + test-suite.log + config.log）复现计数逻辑，得到 passed=83 failed=0
skipped=0 discovered=83 executed=83，恒等式成立。生效与否以下一轮真机 rule4 为准。
