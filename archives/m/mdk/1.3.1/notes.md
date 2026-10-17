# mdk 1.3.1 adaptation notes

- Upstream: https://www.gnu.org/software/mdk/ (GNU MIX Development Kit)
- Source: https://ftp.gnu.org/gnu/mdk/v1.3.1/mdk-1.3.1.tar.gz
- SHA256: `ebb963938c688c150ff6aaedc29f30d09020a1e31d55b30c2101f08773516d19`
  (computed from the downloaded release tarball, 1218078 bytes)
- Build system: Autotools (`configure.ac` / `Makefile.am`, generated
  `configure` + `Makefile.in` shipped in the tarball)
- Deliverable: `bin/mixasm` + `bin/mixvm` command-line tools.
  `mixlib/libmix.a` is a `noinst_LIBRARIES` convenience library that
  upstream does not install, so this is an application package
  (`package_type = "application"`), same shape as the adcli recipe.

## Key adaptations

1. **No bootstrap needed**: the release tarball already contains the
   generated `configure` and `Makefile.in` files, so `build()` does not run
   `autoreconf` (unlike GitLab tag archives such as adcli).
2. **Platform triplet**: config.guess cannot identify HarmonyOS
   (`uname -s = "HarmonyOS"`), so configure gets an explicit
   `--build/--host=aarch64-unknown-linux-ohos` (same as adcli).
3. **Optional features disabled** (all are opt-out upstream flags):
   `--disable-gui` (gmixvm needs GTK+ 3 / Pango, unavailable on OHOS),
   `--without-guile` (mixguile shell needs Guile; mixasm/mixvm, libmix and
   the test suite do not), `--without-readline` (mixvm falls back to plain
   stdin; avoids readline/ncurses devel on the worker).
4. **Single dependency**: `glib/2.84.0.1` (configure `PKG_CHECK_MODULES`
   hard requirement), wired through `PkgConfigDeps` + `VirtualBuildEnv`,
   the most widely required glib revision in this repository (177 recipes).
5. **HMDFS**: drop `umask 077` from the shipped configure so config.status
   can create its temp dir (E114/E011, adcli pattern); `make` serialized
   with `-j1` (E074 jobserver fifo); `PWD` pinned and `TMPDIR/TMP/TEMP`
   pointed at a writable dir for configure/make/check/install.

## Upstream tests

`make check` runs 6 automake `check_PROGRAMS` in `mixlib/testsuite`
(`TESTS = $(check_PROGRAMS)`), driven entirely by local `.mixal`
fixtures, no network required:

- mixtypest (mix_types_t.c): MIX word/field-spec type tests
- mixinstest (mix_ins_t.c): instruction encode/decode tests
- mixvminstest (mix_vm_ins_t.c): VM instruction tests
- mixparsertest (mix_parser_t.c): MIXAL parser tests
- mixdevtest (mix_device_t.c): device emulation tests
- mixevaltest (mix_eval_t.c): expression evaluator tests

`samples/tests/*.mixal` are data files (`EXTRA_DIST`, not automake TESTS).
Result counts are read from the real `test-suite.log`
(`# TOTAL/PASS/FAIL/SKIP/XFAIL/XPASS/ERROR`) and emitted as
`HMBS_UPSTREAM_TEST_RESULT` (framework=automake, command="make check").

## test_package design (R34)

No public library is installed, so verification is binary-level (3 checks):

1. `mixasm --help` prints `Usage:` and exits 0.
2. `mixvm --help` prints `Usage:` and exits 0.
3. `mixasm` assembles the vendored `hello.mixal` fixture (verbatim copy of
   upstream `samples/hello.mixal`) into a non-empty `hello.mix` file.

Counts are emitted as `HMBS_TEST_PACKAGE_RESULT` (discovered=3).

## Local verification status

Workstation is Windows without the OHOS toolchain; per task rules no local
conan build was attempted. Verification is delegated to the HMBS true-machine
preflight after this round (conan create on HarmonyOS aarch64, which runs
`make check` + `test_package` and produces both HMBS markers).

## True-machine preflight rounds

### 2026-10-01 compile failure: intltool too old (fixed, pending re-verify)
- Evidence: `configure[10639]: intltool-update: inaccessible or not found`,
  `checking for intltool >= 0.37... found`,
  `configure: error: Your intltool is too old. You need intltool 0.37 or later.`
  Also `checking whether to use NLS... yes` +
  `where the gettext function comes from... included intl directory`.
- Root cause: configure.ac calls `AM_GNU_GETTEXT` + unconditional
  `IT_PROG_INTLTOOL([0.37],[no-xml])`. Old intltool.m4 probes
  intltool-update even with `--disable-nls` (launchpad 904647/398572),
  and the worker has no runnable intltool-update, so the version check
  fails before any compilation. NLS was also still enabled (included
  intl), which OHOS cannot use (no system libintl, E027).
- Fix: `build_requirements(): tool_requires("intltool/0.51.0")`
  (published pure-perl tool; pslib/dbustest/l3afpad precedent;
  `[no-xml]` already skips the XML::Parser check) +
  `configure --disable-nls` (E027, drops po/included-intl build) +
  OHOS-only intltool perl-shebang wrappers in `_fs_env()`
  (pslib precedent, package kept immutable; best-effort if perl or
  the build-requirement is absent).
- Files: conanfile.py, manifest.yaml (this notes.md).

### 2026-10-01 round 2: intltool package script ENOENT (fixed, pending re-verify)
- Evidence: `.../p/intlt0c19effe85f57/p/bin/intltool-update: No such file
  or directory` then `checking for intltool >= 0.37... found` and the
  same `Your intltool is too old` error. The tool_requires WAS found on
  PATH, but exec fails: classic stale perl-shebang ENOENT (kernel
  reports the script path when its `#!` interpreter is missing), not a
  missing file. Last round's perl-exec wrappers never reached
  configure (default-scope env) and lived on the HMDFS build tree.
- Root cause: two compounding issues. (1) Scope: `_fs_env().vars(self)`
  without `scope="build"` does not reach configure's build context, so
  AC_PATH_PROG ignored our INTLTOOL_*/PATH and re-found the broken
  package script. (2) Location/interpreter: perl-shebang scripts need a
  device perl that may not exist, and HMDFS tree files cannot rely on
  chmod +x.
- Fix: sh shims under the HMBS scratch tmpdir (`mdk-intltool-shim/`,
  `#!/bin/sh`, no perl shebang) answering `--version` truthfully as
  `intltool-update (intltool) 0.51.0` (dbustest msgmerge-stub
  precedent); any other invocation delegates to the real script via
  device perl when available, else exits 0 (safe: --disable-nls means
  po/ never uses them beyond the probe). Prepended to PATH ahead of
  the tool_requires bin AND exported via INTLTOOL_UPDATE/MERGE/EXTRACT;
  build()/package() now use `scope="build"`. Probes extended to log
  INTLTOOL_* and shim `--version` for next-round forensics.
- Files: conanfile.py (this notes.md).

### 2026-10-01 round 3: bare intltool-update probe ignores INTLTOOL_UPDATE (fixed, pending re-verify)
- Evidence: same `.../p/bin/intltool-update: No such file or directory` +
  `Your intltool is too old` after round 2 shims, plus `mdk-probe CC=''`.
  Shipped `configure:10639` runs a bare `intltool-update --version | head -1
  | cut -d" " -f3` BEFORE consulting $INTLTOOL_UPDATE (verified against the
  1.3.1 release tarball), so only PATH order decides it; the PATH-resolved
  published package script fails with stale-perl-shebang ENOENT and yields an
  empty version. The `CC=''` probe line is expected (CC lives in the
  AutotoolsToolchain file, not os.environ) and the `-lcposix` link error is a
  non-fatal AC_SEARCH_LIBS/isc-posix iteration, not the fatal error.
- Root cause: two gaps. (1) The version probe bypasses $INTLTOOL_UPDATE, so
  the round-2 INTLTOOL_* exports alone cannot save it. (2) PATH precedence:
  Conan's aggregated conanbuild.sh can place the tool_requires bin ahead of
  the shim for that bare probe (activity-log precedent: live os.environ
  re-assertion required).
- Fix (conanfile.py, build-time edits of the generated configure only, no
  patch file, no platform macro): `_harden_intltool_version_check()` rewrites
  the probe to `(intltool-update --version 2>/dev/null || echo
  "intltool-update (intltool) 0.51.0") | head -1 | cut -d" " -f3` so an
  unrunnable script falls back to the tool_requires version; `build()` also
  re-asserts the shim dir directly on os.environ PATH plus INTLTOOL_* inside
  the scope="build" block and records the dir via `self._mdk_shim_dir`.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-01 round 4: pkg-config missing (fixed, pending re-verify)
- Evidence: `checking for pkg-config... no`, `checking for glib-2.0 >= 2.0...
  no`, `configure: error: The pkg-config script could not be found or is too
  old`. Intltool shim now resolves (`.../tmp/mdk-intltool-shim/intltool-update`
  in stderr), so round-3 fix worked; the build now stops at the next
  PKG_CHECK_MODULES probe. The `-lcposix` link error and clang `-V` noise are
  non-fatal autoconf iterations, not the fatal error.
- Root cause: recipe runs PKG_CHECK_MODULES(GLIB) but declares no pkg-config
  provider; HMBS only injects cmake/make/ninja/python3, worker has no system
  pkg-config (xmlsec/1.3.12 precedent, identical error text).
- Fix: `build_requirements(): tool_requires("pkgconf/3.0.5")` (xmlsec/ctpl/
  burp2/fcft precedent); manifest.yaml dependencies updated; PKG_CONFIG added
  to _dump_config_log probe list. No test-scope change.
- Files: conanfile.py, manifest.yaml, notes.md (this entry).

### 2026-10-01 round 5: pkgconf tool alone insufficient, explicit bridge (fixed, pending re-verify)
- Evidence: `pkgconf/3.0.5: Not found in local cache` then still
  `checking for pkg-config... no` + `The pkg-config script could not be found`.
  Round-4 tool_requires resolved the graph but did not satisfy the probe.
- Root cause: different from round 4 assumption. The in-repo pkgconf package
  only ships a `pkgconf` binary with no `pkg-config` alias (package() even
  errors on an unexpected alias), and nothing exported PKG_CONFIG/PATH, so the
  bare `pkg-config` and triplet-prefixed probes both miss (xmlsec/1.3.12
  2026-09-16 same-fingerprint lesson).
- Fix (new strategy, not repeating round 4): keep tool_requires, add
  _is_runnable_pkg_config/_write_exec_shim helpers (os.open 0o755, no chmod
  dependency for HMBS_CAP_CHMOD=0) + resolve PKG_CONFIG env/tool-bin/PATH/HNP
  fallback with --version verification; expose `pkg-config` and
  `aarch64-unknown-linux-ohos-pkg-config` shims under the HMBS scratch tmpdir,
  export PKG_CONFIG via _fs_env Environment and live os.environ re-assertion
  in build(). No test-scope change.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-02 round 6: make check 6/6 FAIL, no per-test reason (fixing, pending re-verify)
- Evidence: `make check` reached the test phase (configure/pkg-config/intltool
  fixed) but `# FAIL: 6` in `mixlib/testsuite/test-suite.log`, then
  `ConanException: Error 2` at `autotools.make(target="check")`, so the
  `HMBS_UPSTREAM_TEST_RESULT` marker never emitted (backend records 0/0).
  Only the summary survives; per-test .log content was never dumped.
- Root cause (two systemic gaps + one reporting gap, verified against upstream
  sources http://git.savannah.gnu.org/cgit/mdk.git/plain/mixlib/testsuite/):
  (1) `mixlib/testsuite/Makefile.am` compiles
  `-DMIX_TEST_SAMPLES_DIR="$(top_srcdir)/samples"` and `mix_parser_t.c` opens
  `SAMPLES_DIR/name` for `MIXAL_FILES = tests/bt, ..., hello, ...`; an
  out-of-source Conan build can leave the build-tree `samples/tests`
  missing, failing file-dependent tests. (2) Stronger signal: `mixtypest`
  (`mix_types_t.c`, fetched 2026-10-02) is pure word-arithmetic with no file
  I/O, yet it also FAILs — so fixtures alone cannot explain 6/6. The 6 test
  binaries link glib dynamically (`-lglib-2.0` in the failing link line) but
  the build-scope env never puts conan host package lib dirs on
  LD_LIBRARY_PATH, so every test binary can die at exec with a missing .so.
  (3) Reporting: `build()` raised before `_emit_upstream_test_result()`,
  hiding real counts.
- Fix (no test-logic change, no skips, no assertion edits): `_fs_env()`
  prepends every host dep `lib/` dir to LD_LIBRARY_PATH;
  `_sync_test_fixtures()` mirrors `samples/` + `mixlib/testsuite/tests/`
  into the build tree when missing (no-op in-source);
  `build()` wraps `make check` so failure first calls `_dump_test_logs()`
  (test-suite.log + per-test .log tails + fixture-dir listing) and emits the
  marker from the real test-suite.log counts before re-raising;
  `_emit_upstream_test_result()` searches both build and source trees.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-02 round 7: compile Signal 9 with empty logs (fixed, pending re-verify)
- Evidence: preflight `failed` at stage `compile`, `Signal 9` in stderr,
  empty stdout, upstream 0/0/0. No compiler TU identified: classic
  constrained-device OOM-killer signature (traildb/0.6 2026-09-29 precedent:
  `Signal 9 + empty logs even at -O1`).
- Root cause (two compounding gaps, verified against recipe source):
  (1) `generate()` never touched `tc.extra_cflags/extra_cxxflags`, so the
  profile `-O3` (config.log conftest shows `-O3 -DNDEBUG`) drove every TU
  at peak clang memory on the small device. (2) `build()` called
  `autotools.make` directly with no OOM-only retry, so a transient
  memory spike was fatal. Incidental: `_dump_test_logs()` fixture loop
  was missing the outer closing `)` (9 opens / 8 closes), a SyntaxError
  that would have broken the next recipe load; fixed in the same round.
- Fix (additive only, no test-scope/logic change, no skips, no assertion
  edits; libgridxc/2.1.02.0.2 + traildb/0.6 precedent, adapted to
  autotools): `generate()` appends `-O1 -g0` to `tc.extra_cflags` and
  `tc.extra_cxxflags` when absent (tail wins over profile `-O3/-g`,
  idempotent); `build()` runs both `make` and `make check` through
  `_make_with_oom_retry()` (max 3 attempts, `gc.collect()` + 15s cooldown,
  retries ONLY `Signal 9/Killed/Out of memory/Cannot allocate memory/
  exit 137`, all other errors re-raise immediately); fixed the missing
  `)` in the fixture-dir loop.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-02 round 8: GNU gettext tools not found (fixed, pending re-verify)
- Evidence: `checking for msgfmt... (cached) :`, `checking for gmsgfmt...
  (cached) :`, `configure: error: GNU gettext tools not found; required
  for intltool`, `autotools.configure()` Error 1. The `-lcposix` link
  error and clang `-V/-qversion` noise are non-fatal autoconf iterations,
  not the fatal error.
- Root cause: `IT_PROG_INTLTOOL([0.37],[no-xml])` unconditionally requires
  msgfmt/gmsgfmt/msgmerge/xgettext with GNU `--version`, even with
  `--disable-nls` (launchpad 904647). The worker PATH has none of them;
  OHOS SDK splits them (libgda5/5.2.10 lesson: xgettext/msgfmt in
  `/data/service/hnp/bin` on some hosts, msgmerge under
  `gettext.org/*/bin`), and the recipe never put them on PATH.
- Fix (no new dependency, no test-scope change; libgda5 PATH-prepend +
  dbustest stub hybrid): `_fs_env()` prepends
  `glob("/data/service/hnp/gettext.org/*/bin")` to PATH, then stubs any
  still-missing tool under `mdk-gettext-shim/` answering `--version` as
  `(GNU gettext-tools) 0.22.5` (safe: `--disable-nls` means po/ never
  builds); `build()` re-asserts the shim dir on live `os.environ` PATH
  (same aggregated-conanbuild.sh precedence issue as intltool/pkg-config
  shims); `_dump_config_log()` now logs each gettext tool resolution.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-02 round 9: gettext shims existence-only check kept broken tools (fixed, pending re-verify)
- Evidence: after round 8, still `checking for msgfmt... (cached) :` +
  `configure: error: GNU gettext tools not found`, but probes now show
  `msgfmt=/.../.harmonybrew/bin/msgfmt rc=127: Error relocating
  libgettextsrc-1.0.so: libintl_gettext: symbol not found` (same for
  msgmerge/xgettext) while `gmsgfmt=<tmp>/mdk-gettext-shim/gmsgfmt rc=0`
  passes. Only gmsgfmt was stubbed. HMBS adds `[stale_runtime_library]`
  diagnosis (glib proxy-libintl shadowing system libintl; gtkspell3 lesson).
- Root cause (different from round 8 assumption): round 8 used
  `shutil.which` existence only, so PATH-present but unrunnable harmonybrew
  tools were kept. IT_PROG_INTLTOOL requires ALL of msgfmt/msgmerge/
  xgettext to answer `--version` with `(GNU`; one broken tool fails the
  whole check. The `-lcposix`/clang `-V` noise remains non-fatal.
- Fix (new strategy, not repeating round 8): require rc==0 plus `(GNU` in
  `--version` output for each of msgfmt/gmsgfmt/msgmerge/xgettext, stub
  anything else under `mdk-gettext-shim/` (safe: `--disable-nls`, dbustest
  precedent); shim dir stays frontmost on PATH with live re-assertion.
  No new dependency, no test-scope/logic change.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-02 round 10: unconditional gettext shims (fixed, pending re-verify)
- Evidence: round 9 still only stubbed gmsgfmt; probes show
  msgfmt/msgmerge/xgettext at `.../.harmonybrew/bin/* rc=127 Error
  relocating libgettextsrc-1.0.so: libintl_gettext: symbol not found`
  with `[stale_runtime_library]` diagnosis, and
  `checking for msgfmt... (cached) :` + `GNU gettext tools not found`.
- Root cause (different from rounds 8/9): the runnable check runs inside
  `_fs_env()` BEFORE the host glib lib dir is prepended to
  LD_LIBRARY_PATH later in the same function, so harmonybrew binaries
  look healthy at check time but break under configure's full env where
  glib proxy-libintl shadows system libintl (gtkspell3 lesson). Probing
  at either point gives the wrong answer.
- Fix (new strategy): stop probing; always shadow all four tools
  (msgfmt/gmsgfmt/msgmerge/xgettext) with sh shims frontmost on PATH
  (safe: `--disable-nls`, dbustest precedent). No new dependency,
  no test-scope/logic change.
- Files: conanfile.py, notes.md (this entry).

### 2026-10-02 round 11: make install Error 64 on install-binPROGRAMS (fixed, pending re-verify)
- Evidence: `make check` now passes (`HMBS_UPSTREAM_TEST_RESULT passed,
  discovered 6, executed 6, passed 6`), but `package()` fails at
  `install-binPROGRAMS` with `.../runtime/mdk-1.3.1/bin/install -c mixasm
  mixvm '.../p//bin'` then `make[2]: *** [Makefile:402:
  install-binPROGRAMS] Error 64`.
- Root cause: HMBS install shim accepts only single-file two-arg calls
  (`[ $# -eq 2 ] || exit 64`, EX_USAGE), while automake batches both
  binaries into one `$(INSTALL_PROGRAM) mixasm mixvm DEST` call. Same
  fingerprint as zurl/1.12.0 notes #35, lzop/1.04 (E098/E174),
  myman/4.0.116 (E182/E188), adms/2.3.7. Not a compiler/shell/umask
  issue; the absolute `/install` path baked into Makefiles at configure
  time also means a PATH shadow alone cannot fix it.
- Fix (adapted zurl/adms precedent, OHOS-only, no test-scope change):
  `_write_install_shim()` writes a cp/mkdir shim (parses -c/-m/-d,
  chmod best-effort for HMBS_CAP_CHMOD=0, os.open 0o755 so no chmod
  dependency; multi-source DEST is mkdir -p'd as a directory);
  `_redirect_install_to_shim()` rewrites `INSTALL`/`INSTALL_DATA`/
  `INSTALL_PROGRAM`/`INSTALL_SCRIPT` lines carrying an absolute
  /install path in every generated Makefile under build_folder;
  `package()` creates the shim and redirects before
  `Autotools.install()`. Linux zero-change.
- Files: conanfile.py, notes.md (this entry).
