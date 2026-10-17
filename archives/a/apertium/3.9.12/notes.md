# apertium 3.9.12 — Adaptation Notes

## Context

- Task: adapt apertium core engine 3.9.12 (github.com/apertium/apertium, tag v3.9.12).
- Previous round left no `archives/a/apertium/` tree at all, so the HMBS
  preflight gate reported `incomplete / 无法读取当前 archive 代码树`.
  This round creates the full recipe tree from scratch.
- P0 chain: `configure.ac:71 PKG_CHECK_MODULES(LTTOOLBOX, [lttoolbox >= 3.7.2])`
  is satisfied by the already-published `lttoolbox/3.7.6` (same autotools
  family; this recipe reuses its proven patterns: CPPFLAGS/LDFLAGS +
  PKG_CONFIG_PATH injection, `umask 077 → 022` E011 fix,
  `ACLOCAL/AUTOMAKE/... = ":"` missing-automake guard).

## Source identity

- Release asset (stable, `make dist` output with pre-generated `configure`):
  `https://github.com/apertium/apertium/releases/download/v3.9.12/apertium-3.9.12.tar.bz2`
- sha256 `34a1756d33e4d968bcf3ddbbf7f2315da88893ad7b7ad041d7595a2c4178b302`
  cross-checked against the PureOS `.dsc` Checksums-Sha256 for the
  576841-byte `apertium_3.9.12.orig.tar.bz2` (same size as the release asset).
- conandata keeps the single official GitHub URL (CI auto-adds mirror
  fallback); sha256 unchanged.

## Build analysis (from upstream configure.ac / Makefile.am @ v3.9.12)

- Hard configure requirements: `flex`, `xmllint`, `xsltproc` (AC_PATH_PROG +
  AC_MSG_ERROR). `apertium/apertium/Makefile.am` generates ~30 flex scanners
  at build time via `xsltproc deformat.xsl ... && flex ...`.
  Provided as `tool_requires`: `flex/2.6.4`, `libxml2/2.15.3.1` (xmllint,
  PROGRAMS=ON), `libxslt/1.1.45.2` (xsltproc, WITH_PROGRAMS=ON).
- Library deps: `lttoolbox/3.7.6`, `libxml2/2.15.3.1`, `icu4c/77`,
  `utf8cpp/4.1.1` (all transitive_headers; apertium headers expose them).
  No boost requirement in apertium's own configure.ac (unlike lttoolbox).
- C++ standard auto-probed (17 minimum, tries 23/2b/20/2a first);
  OHOS clang 15 is fine.
- Python bindings left disabled (`--disable-python-bindings`, upstream
  default; avoids swig/python-dev); `AM_PATH_PYTHON` is warning-only and
  `run_tests.py` only needs a plain python3, which the workers provide.
- OHOS fix (guarded `replace_in_file` in `source()`, no patch file):
  `apertium/apertium-header.sh: locale_utf8()` exits 1 when no UTF-8 locale
  exists; minimal OHOS rootfs may lack `locale`/locale data. Now warns and
  assumes UTF-8 (no-op on systems with a proper locale).

## Upstream tests

- `make check` covers: `tests/run_tests.py` (8 unittest modules),
  `deshtml-alt/run`, `deslatex/run`, `sh/run`, `odt/run`, plus
  `tests/tagger` C++ `check_PROGRAM`.
- Tool-gated, evidence-based selection in `build()` (no test sources patched):
  `sh/run` runs only if `shellcheck` exists (Haskell linter, no OHOS build);
  `odt/run` runs only if `zip`+`unzip`+`zipcmp` all exist (plain `zip` has no
  Conan package in this repo). Exclusions are recorded in the
  `HMBS_UPSTREAM_TEST_RESULT` marker `reason` field.
- Falsification guards in `build()`: refuses PASS when `test-suite.log`
  files are missing/empty, when the built `apertium-destxt` is missing/empty,
  or when fixtures (`unicode.tsx`, `expected.odt`) are empty.

## test_package

- `test_apertium.sh` (3 assertions): `apertium -V` version string,
  `apertium-destxt` tagged output (non-empty + markup), destxt|retxt
  round-trip restoring input. `conanfile.py` captures the script output,
  counts real `PASS:` lines / `PASS_COUNT=x/3`, and emits
  `HMBS_TEST_PACKAGE_RESULT`; it also re-emits and validates the persisted
  `HMBS_UPSTREAM_TEST_RESULT`.

## Status

- Recipe tree created this round, uncommitted (per event-round discipline).
  Awaiting HMBS preflight (real compile + test numbers from HarmonyOS
  aarch64 hardware) before any commit/push.

## 2026-09-12 preflight fix (autoreconf perl XS breakage)

- True-machine `conan create` failed in `build()._run_autoreconf`:
  `".../perl" ".../autoreconf" -fi` died with
  `Cwd.so: Perl_my_cxt_init: symbol not found` — the Conan perl 5.42.2
  package cannot even load its own XS `Cwd.so`, so forcing the Conan
  perl+autoreconf pair cannot work.
- Fix (this round, uncommitted): removed `tool_requires("perl/5.42.2")`;
  `_run_autoreconf` now scrubs all `PERL*` env vars (`PERL5LIB` etc.) and
  runs `autoreconf -fi` directly so its shebang uses the system perl
  (ABI-matched); Conan autoconf/automake/libtool/m4 bindirs stay first on
  PATH. If the release tarball already ships `configure`, the branch is
  skipped and no perl is needed at all.

## 2026-09-12 preflight fix round 2 (PERL5LIB re-injection)

- Same XS failure persisted after round 1 (`Cwd.so: Perl_my_cxt_init:
  symbol not found`, now failing at `/data/service/hnp/bin/autoreconf`):
  conanbuild.sh re-injects a PERL5LIB pointing at the conan perl arch dir
  at `self.run` time, so scrubbing `os.environ` beforehand is overwritten;
  an empty PERL5LIB would also lose the Automake/Autom4te pure-Perl modules.
- Fix (this round, uncommitted; reuses DRAFT-6049/libnxml-0.18.5 proven
  pattern): `_run_autoreconf` now runs
  `PATH="<autoconf>/bin:<m4>/bin:$PATH" PERL=perl
  PERL5LIB="<automake>/share/automake-1.18:<autoconf>/share/autoconf"
  TMPDIR/TMP/TEMP="<writable-tmp>" autoreconf -fi` with `env="conanbuild"`.
  PERL=perl routes the autoconf wrapper onto the system perl; the two
  share dirs supply only pure-Perl modules while core XS (Cwd) falls back
  to the system perl @INC; TMPDIR covers the OHOS read-only /tmp.
## 2026-09-12 preflight fix round 3 (RO /tmp + HMDFS getcwd)

- True-machine `conan create` failed at `autotools.configure()`:
  `can't create temporary file /tmp/shckisgw.tmp: Read-only file system`
  followed by cascading `getcwd: cannot access parent directories` and
  `configure: error: working directory cannot be determined`.
- Root cause: recipe exported writable TMPDIR only via
  `tc.environment()` (conanbuild script) and the autoreconf command
  line; `configure`'s autoconf secure-tmp (`./confXXXXXX`) and its
  `ac_pwd=`pwd`` probe still hit RO /tmp and HMDFS getcwd failure.
- Fix (this round, uncommitted; adapts cryptopant/1.3.2 proven pattern,
  minimal FS-subcapability scope, no test changes):
  (1) `generate()` persists TMPDIR/TMP/TEMP/SHELL/CONFIG_SHELL plus
  HMBS_* passthrough via `Environment().save_script("hmbs_env")`;
  (2) `build()` calls `_fs_env()` first (ensure build dir, chdir,
  set PWD/TMPDIR/SHELL); (3) `_patch_configure_for_ohos()` patches
  `configure`/`config.status` AFTER autoreconf (TMPDIR-aware mktemp,
  umask 022, `pwd || echo $PWD`) and re-patches `config.status`
  after `configure()`.
- conandata: dropped the hand-written `gh-proxy.com` mirror URL
  (PF7-blacklisted; CI `build_and_test.sh` auto-adds mirror fallback);
  official GitHub URL kept, sha256 unchanged.

## 2026-09-12 preflight fix round 4 (config.guess vs HarmonyOS uname)

- Previous round 3 fix verified: configure now runs past the RO /tmp +
  getcwd stage, but fails with `config.guess: unable to guess system
  type` (`UNAME_SYSTEM="HarmonyOS"`, guess 2024-07-27) ending in
  `configure: error: cannot guess build type; you must specify one`.
- Fix (this round, uncommitted; adapts cryptopant/1.3.2, no test
  changes): `generate()` appends explicit
  `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
  when `os==OHOS` (guarded against duplicates). The linux-gnu triplet
  is only the string config.sub normalizes; OHOS targeting still comes
  from the HNP clang flags. `aarch64-linux-ohos` is NOT used because
  2023-2024-era config.sub rejects `ohos` as OS.

## 2026-09-12 preflight fix round 5 (VPATH apertium_config.h not found)

- True-machine make failed after a successful configure: apertium/endian_double_util.cc:21 fatal error apertium/apertium_config.h file not found.
- Root cause: AC_CONFIG_HEADER([apertium/apertium_config.h]) writes the header into top_builddir (build-release/apertium/), but apertium/Makefile.am sets AM_CPPFLAGS=-I(top_srcdir) only, so the out-of-source Conan build has no -I pointing at the generated header. Upstream never supported VPATH for this header.
- Fix (this round, uncommitted, minimal include-scope only, no test changes): generate() prepends -I(build_folder) and -I(source_folder) to CPPFLAGS so <apertium/apertium_config.h> resolves in either tree.

## 2026-09-12 preflight fix round 6 (VPATH xslt/flex inputs, different strategy)

- Previous round 5 (-I build/source roots) verified: libapertium.a now builds
  and links (log shows ranlib .libs/libapertium.a + apertium-cleanstream link),
  but make then fails in build-release/apertium at
  `xsltproc deformat.xsl html-format.xml` with
  `failed to load external entity "deformat.xsl"`.
- Root cause differs from round 5: apertium/Makefile.am flex/xslt generator
  rules use bare filenames valid only for in-source builds; out-of-source
  cwd lacks those inputs. Not an include-path problem, so a new strategy.
- Fix (this round, uncommitted, build-only mirror, no upstream patch, no test
  change): after autotools.configure(), copy static generator inputs
  (*.xsl, *-format.xml, *.l, *-header.sh, *.dtd, *.rnc) from
  source/apertium/ into build/apertium/ so bare names resolve; generated
  outputs stay in the build tree.

## 2026-09-12 preflight fix round 7 (VPATH tagger LDADD, link failure)

- True-machine `make check` failed at link time in tests/tagger/:
  `ld.lld: error: unable to find library -lapertium` with
  `-L<source-base>/apertium/.libs/ -lapertium` (source tree path, no
  build-release segment; that directory is never populated).
- Root cause (confirmed against upstream v3.9.12 tests/tagger/Makefile.am):
  `test_find_similar_ambiguity_class_LDADD =
  -L$(top_srcdir)/$(PACKAGE_NAME)/.libs/ -l$(PACKAGE_NAME)` — valid only
  for in-source builds. Conan builds out-of-source, so the just-built
  libapertium.a lives under top_builddir/apertium/.libs. Different defect
  from rounds 5/6 (include path / generator inputs); new one-line scope.
- Fix (this round, uncommitted, no test logic changed, falsification kept):
  (1) source(): guarded replace top_srcdir -> top_builddir in
  tests/tagger/Makefile.am before autoreconf regenerates Makefile.in;
  (2) build(): belt-and-suspenders patch of the generated
  build/tests/tagger/Makefile after configure() for pre-generated
  tarballs where autoreconf is skipped. Static-only build kept (R26);
  -lapertium resolves to libapertium.a once the directory is correct.
  In-source builds unaffected (top_builddir == top_srcdir).

## 2026-09-12 preflight fix round 8 (Signal 9 / SIGKILL during compile)

- True-machine `conan create` failed in compile phase with bare
  `Signal 9` and empty stdout/stderr tails (no compiler error line).
  Signal 9 = SIGKILL, the OOM-killer signature on the shared true
  machine; all prior configure/VPATH stages had already passed
  (rounds 5-7 verified libapertium.a + cleanstream link), so the kill
  hits the `make -j1` compile of libapertium plus ~30 flex-generated
  scanners whose huge switch tables spike cc1plus memory even at -j1.
- Fix (this round, uncommitted, build-config only, no source patched,
  no test skipped/changed): `generate()` appends `-O1 -g0` via
  `tc.extra_cflags/cxxflags` (last -O wins over the default -O2/-O3;
  -g0 drops debug bloat and disk pressure). `make -j1` kept.
  Optimization level does not affect test semantics; falsification
  guards and full `make check` selection unchanged.

## 2026-09-12 preflight fix round 9 (TESTS quoting + check TMPDIR export)

- True-machine `make check TESTS='./run_tests.py deshtml-alt/run deslatex/run'`
  reported `TOTAL=1 / FAIL=1` instead of 3: `Autotools.make(args=["TESTS=a b c"])`
  joins without shell quoting, so make saw `TESTS=./run_tests.py` plus stray
  targets `deshtml-alt/run deslatex/run` and ran only run_tests.py.
- run_tests.py itself failed via tests/tagger/__init__.py `tmp()` which uses
  `tempfile.NamedTemporaryFile` without dir (defaults to $TMPDIR else RO /tmp);
  deshtml/deslatex shell runs also use bash here-string temp files. HMBS
  flagged `[readonly_tmp]`.
- Fix (this round, uncommitted, minimal temp-root scope, no test patched or
  deleted): `_run_upstream_tests` resolves the writable tmpdir via
  `_resolve_writable_tmpdir()`, exports TMPDIR/TMP/TEMP to os.environ, and runs
  `TMPDIR=... TMP=... TEMP=... make check TESTS='...'` via `self.run` with
  explicit single-quote so all TESTS entries reach recursive sub-makes.

## 2026-09-12 preflight fix round 10 (VPATH test-script mirror)

- Round 9 verified for quoting (TOTAL 1->3) but all 3 TESTS still FAIL with
  readonly_tmp retained. New evidence: builddir tests/ holds only generated
  Makefiles, so automake check-TESTS falls back to $(srcdir)/TESTS; those
  scripts cd to dirname($0) in the source tree and exec
  ../../apertium/apertium-* (unbuilt sources). Different defect from rounds
  5-7 (header/include, flex inputs, tagger LDADD) and from round 9 (quoting,
  TMPDIR export which is kept).
- Fix (this round, uncommitted, build-only mirror, no upstream patch, no test
  change): after configure, walk source/tests and copy missing scripts/data
  (run_tests.py, base_test.py, */__init__.py, deshtml-alt/run, deslatex/run,
  data files) into build/tests without overwriting generated Makefiles, best
  effort chmod; so ./TESTS resolves in builddir and relative binary paths hit
  build-release/apertium built binaries.

## 2026-09-12 preflight fix round 11 (TESTS_ENVIRONMENT export + forensics)

- Round 9 (quoting + shell-prefix TMPDIR) verified TOTAL 1->3; round 10
  (VPATH tests mirror) kept 3 but still 0 passed. Different strategy: GNU
  make does not reliably re-export parent env into recipes, so the
  shell-prefix TMPDIR may never reach python tempfile/bash here-strings.
- Fix (this round, uncommitted, no test logic changed): pass the writable
  root also via automake TESTS_ENVIRONMENT (prepended to EVERY test command,
  performs export INSIDE the test shell) plus make command-line
  TMPDIR/TMP/TEMP assignments for recursive sub-makes via MAKEFLAGS; keep
  the shell export prefix and VPATH mirrors.
- Forensics (bounded, log-only): on every run print resolved TMPDIR/TMP/TEMP,
  python tempfile.gettempdir() probe, and last 80 lines of
  tests/test-suite.log + tests/tagger/test-suite.log so the next preflight
  summary carries the real failure text.

## 2026-09-12 preflight fix round 13 (exec-bit loss exit 126 + bash PATH + fail-excerpt)

- True-machine `make check TESTS='./run_tests.py deshtml-alt/run deslatex/run'`
  reached TOTAL=3 but 0 passed; stderr shows `FAIL deslatex/run (exit status:
  126)` and HMBS kept `[readonly_tmp]`. Exit 126 = test script found but not
  executable. Round-10 VPATH mirror used `shutil.copyfile + os.chmod`, but the
  true machine reports `HMBS_CAP_CHMOD=0`: chmod is unsupported, so mirrored
  `run`/`run_tests.py` stayed 644 and automake exec failed before any TMPDIR
  code ran. Different defect from rounds 9/11 (quoting + TMPDIR export, kept).
- Fix (this round, uncommitted, no test logic changed, falsification kept):
  (1) VPATH test mirror now symlinks first (`HMBS_CAP_SYMLINK=1`), needing no
  chmod so the tarball +x bit is preserved; copy+chmod is only a fallback.
  (2) `_run_upstream_tests` also prepends `/data/service/hnp/bin` (true-machine
  bash location) to PATH in both the shell prefix and `TESTS_ENVIRONMENT`, and
  probes `command -v bash` + `ls -l $TMPDIR` before `make check`, so a missing
  `env bash` or RO tmpdir is visible in the head of the log, not just the tail.
  (3) Failure forensics now embeds the first FAIL/exit-status line (bounded
  400 chars) into the `HMBS_UPSTREAM_TEST_RESULT` reason, so the next focused
  summary carries the real error even when mid-log tails are omitted.

## 2026-09-12 preflight fix round 12 (source download timeout -> mirror list)

- True-machine `conan create` failed in `source()`: `get()` on the single
  official URL
  `https://github.com/apertium/apertium/releases/download/v3.9.12/apertium-3.9.12.tar.bz2`
  hit `ConnectTimeoutError (connect timeout=30)` twice with 5s retry, then
  `ConanException: Error downloading file ...`. Direct evidence in preflight
  stdout/stderr tails (2x WARN network + ERROR in source() line 128).
- Root cause: worker network cannot reach github.com directly (timeout, not
  404/auth); recipe offered no fallback URL so one slow host fails the build.
- Fix (this round, uncommitted, download-reliability only, sha256 unchanged
  `34a1756d...4178b302`): `conandata.yml` url becomes an ordered list reusing
  the exact `ci/conan/build_and_test.sh` GitHub mapping — `gh-proxy.com`
  prefix first, official GitHub URL last as fallback. Conan 2.x `get()` tries
  each in order. Same-file mirrors so L0j source-key comparison stays stable.
  `manifest.yaml` keeps the single official URL (manif/0.0.5 precedent).
  This is the守则-authorized source-timeout exception (PF7 normally wants a
  single official URL; CI auto-adds the same fallback at CI time, but the
  hmbs preflight runs `conan create` directly so the list must be baked in).

## 2026-09-12 preflight fix round 14 (absolute python shebang bad interpreter)

- Comparison vs round 13: round 13 symlink plus PATH worked as forensics (first-fail excerpt now in marker) but check still 0/3. New direct evidence in reason: test-driver ././run_tests.py /usr/bin/python3 bad interpreter No such file or directory, exit 126. Minimal OHOS rootfs has no /usr/bin/python3; HMBS python3 lives on tool PATH. Different strategy from round 13, not a repeat.
- Fix (this round, uncommitted, no test logic changed): build adds _fix_test_interpreters after VPATH mirror, rewriting only absolute first lines in build-tree tests to env form (python to /usr/bin/env python3, absolute bash/sh to env), replacing symlinks with patched copies so source cache stays pristine; plus shebang probes in log head.

## 2026-09-12 preflight fix round 15 (shebang in place plus relink, keep exec bit)

- Comparison vs round 14: round 14 rewrote bad-interpreter shebang but replaced build symlinks with 644 copies; with HMBS_CAP_CHMOD equal 0 the next run regressed to test-driver line 119 Permission denied on ././run_tests.py and ./deshtml-alt/run, still 0/3. New direct evidence, same fingerprint, different strategy.
- Fix (this round, uncommitted, no test logic changed): _fix_test_interpreters patches source tests in place by truncate plus write on the same inode so tarball plus-x is preserved with no chmod, then converts any regular build-tree file back to a symlink and keeps good symlinks; env-form interpreters retained plus shebang probes.

## 2026-09-12 preflight fix round 16 (tagger tool resolver + lxml stdlib fallback)

- Comparison vs rounds 10/13/15: those fixed WHERE tests execute (VPATH mirror, symlink exec bit, shebang env form) and verified TOTAL 1->3 with 2 passing; this round fixes WHAT the tests resolve, a different strategy on the same fingerprint (2nd same-fingerprint fix, not a repeat).
- New direct evidence (focused summary 2026-09-12T17:40Z): run_tests.py FAIL exit 2 with mixed-tree tracebacks in ONE run - adaptdocx/__init__.py loaded from SOURCE (.../b/tests/...) while extract_docx.py ran from BUILD (.../b/build-release/tests/...); tagger FileNotFoundError x2 for .../b/apertium/apertium-tagger (source-relative, missing build-release segment) plus lxml ModuleNotFoundError x2 (CorrectBoundaries, SameText).
- Root cause: (a) tests/tagger/__init__.py rel() is dirname(abspath(__file__))-based; symlinked modules can report source-__file__ while binaries live under build-release/apertium/; (b) extract_docx.py hard-imports lxml.etree, absent from minimal OHOS python, with no Conan lxml package available.
- Fix (this round, uncommitted, no assertions removed): source() guarded _resolve_tool() search (original rel path first, then cwd-relative build candidates, then PATH, else original loud error) and lxml try/except stdlib shim (XMLParser/fromstring only; identical path when lxml present); build() post-make symlink bridge for apertium/* tools both directions plus C++ helper into source tests/tagger/ when missing (no chmod, never overwrites).

## 2026-09-12 preflight fix round 17 (helper call-site via resolver)

- Comparison vs round 16: round 16 routed only the APERTIUM_* constants
  through _resolve_tool and bridged binaries pre-check; verified this round
  (transfer tests now ok) but run_tests.py still FAILs with
  FileNotFoundError x2 for
  .../b/tests/tagger/test-find-similar-ambiguity-class (source tree, no
  build-release segment). Same fingerprint, 3rd fix, different strategy.
- Root cause, two gaps in round 16: (1) the C++ helper call site
  rel('test-find-similar-ambiguity-class') in changing_class_impl was never
  routed through _resolve_tool, still source-__file__-relative; (2) the
  pre-check bridge structurally cannot cover check_PROGRAMS - the
  `-o test-find-similar-ambiguity-class` link line appears inside the
  make check output, i.e. the helper is built DURING check after the bridge
  ran, so isfile(helper) was False and nothing was linked.
- Fix (this round, uncommitted, no assertions removed): source() 17a extends
  _resolve_tool candidates with cwd-relative tagger/ and tests/tagger/
  locations (cwd at check time is build/tests); 17b routes the helper call
  site through _resolve_tool; both idempotent no-ops when already applied.
  Recipe-level strings validated locally by AST extraction + compile of the
  assembled resolver function and the new call-site expression.

## 2026-09-12 preflight fix round 18 (install phase: staged install wrapper copies nothing)

- Comparison vs rounds 5-17 (all configure/build/check stages): this round
  `make check` fully passed on the true machine (marker
  `HMBS_UPSTREAM_TEST_RESULT` passed 3/3, automake TOTAL/PASS verified, no
  falsification trip), and the failure moved to `package()`:
  `make install` died in `apertium/install-libLTLIBRARIES` with
  `libtool: install: <...>/runtime/apertium-3.9.12/bin/install -c
  .libs/libapertium.a <...>/p//lib/libapertium.a` followed by
  `chmod: cannot access '.../p//lib/libapertium.a': No such file` (Error 1).
- Root cause: configure's AC_PROG_INSTALL picked the HMBS-staged `install`
  wrapper; the preceding `$(MKDIR_P)` step printed no error (dest dir
  existed), yet the copy produced no file, so libtool's follow-up
  `chmod 644` failed on the missing file. Different stage from all prior
  rounds (install, not configure/build/check); E543's empty-arg libtool
  signature does not match (filenames are present here).
- Fix (this round, uncommitted, install-scope only, no test logic touched):
  `package()` pre-creates lib/bin/include/share dirs, exports the writable
  HMBS tmpdir + SHELL, and runs `make install` with
  INSTALL/INSTALL_PROGRAM/INSTALL_SCRIPT/INSTALL_DATA overridden to
  upstream's own portable `install-sh` (freshly regenerated by autoreconf
  from automake 1.18; plain copies need only POSIX sh+mkdir+cp), falling
  back to the configured INSTALL when install-sh is absent; fails fast with
  a clear error when lib/libapertium.a is still missing after install.

## 2026-09-12 preflight fix round 19 (compile fork-OOM: step -O1 down to -O0)

- Comparison vs round 18 (install stage: staged `install` wrapper copied
  nothing; fix unvalidated — build died before package() this round) and
  vs round 8 (Signal 9 SIGKILL fixed by stepping down to -O1 -g0, verified
  for several rounds): same fingerprint family (memory exhaustion in
  `make -j1` compile) but harder evidence on the SAME `-O1` flags
  (compile line still shows `-O3 -O1 -g0`): repeated
  `../libtool: fork: Out of memory`, `/data/service/hnp/bin/bash: fork:
  Out of memory`, ending at `apertium_interchunk.o Error 126`.
- Root cause: cc1plus peak RSS on the huge flex-generated TUs still
  exhausts the shared true machine at -O1; fork() itself fails. The
  accompanying `test: xyes: unary operator expected`, `ignoring unknown
  tag CXX`, `mv: Operation not permitted` lines are cascading symptoms of
  failed forks/execs, not independent defects — identical build() code
  compiled these same TUs fine in earlier rounds. Platform caps this round
  confirm hardlink=0/chmod=0/symlink=1 (existing workarounds already match).
- Fix (this round, uncommitted, build-config only, no source patched, no
  test skipped/changed; different strategy from round 8's -O1): step the
  appended opt flags down to `-O0 -g0` (last -O wins over default -O3).

## 2026-09-13 preflight fix round 20 (quote INSTALL overrides for make)

- Comparison vs round 19 (-O0 step-down: VERIFIED this round — full
  compile passed, upstream marker passed 3/3, `Package built`) and vs
  round 18 (install-sh override: FAILED at the `autotools.install(args=`
  call itself, `ConanException: Error 2`, stderr tail is GNU make's
  `--what-if/--warn-undefined-variables` usage text). Same install
  fingerprint, different defect: not the installer binary but make's
  argv parsing.
- Root cause: round 18 passed the values unquoted
  (`INSTALL=/path/install-sh -c`); Conan joins args with spaces, so GNU
  make saw the trailing `-c`/`-m 644` as make options, printed usage and
  exited 2 before running any install rule.
- Fix (this round, uncommitted, install-scope only, no test logic
  touched): shell-quote each override (`INSTALL="/path/install-sh -c"`)
  so every `VAR=value with spaces` arrives as one argv that make treats
  as a variable assignment.

## 2026-09-13 preflight fix round 21 (VPATH README-MODES for install-data-local)

- Comparison vs rounds 18/20 (install wrapper + quoting): round 20's
  quoting is VERIFIED this round — make now runs install rules with
  `install-sh -c -m 644 README-MODES .../share/apertium/modes/README`
  instead of dying with usage text. The failure moved past argv parsing
  to a NEW defect: `install-sh: README-MODES does not exist`
  (Error 1 in install-am/install-recursive). Round 19's -O0 is also
  VERIFIED (full compile + upstream 3/3 passed). Neither prior root
  cause is reused.
- Root cause: top-level `Makefile.am install-data-local` uses the bare
  filename `README-MODES` (confirmed against upstream v3.9.12
  `Makefile.am`: `$(INSTALL_DATA) README-MODES $(DESTDIR)$(modesdir)/README`),
  valid only for in-source builds. Conan builds out-of-source, so the
  rule runs with cwd=build_folder where the file is absent (it lives in
  source_folder). Same VPATH family as rounds 5/6/10 but a new file and
  a new phase (install, not build/check).
- Fix (this round, uncommitted, install-scope only, no source patched,
  no test touched): `package()` mirrors the single static input
  `README-MODES` from source_folder into build_folder before
  `autotools.install()` (symlink first, copy fallback, never
  overwrites), reusing the rounds 6/10 build-only mirror pattern.
