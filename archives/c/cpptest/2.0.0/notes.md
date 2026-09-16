# cpptest 2.0.0 adaptation notes

- Upstream: https://github.com/cpptest/cpptest, tag 2.0.0 (Autotools, LGPL-2.1).
- Source: `https://github.com/cpptest/cpptest/archive/refs/tags/2.0.0.tar.gz`,
  sha256 `09d35d6ecc0e801925579b18efa0adfaa18e8fed19b2f4f743ec7a53f510e409`
  (fetched 2026-09-10, 141505 bytes).
- No dependencies (W0: nothing to check).
- Tag archive has no generated `configure`; recipe bootstraps via
  `Autotools.autoreconf()` when `configure` is missing, then standard
  Autotools configure/make/install.
- Bootstrap toolchain: `build_requirements()` provides automake/1.18 and
  libtool/2.5.4 via tool_requires + VirtualBuildEnv; autoconf/m4/perl come
  from the SDK (/data/service/hnp/bin) to keep the perl XS ABI consistent
  (accel-config 4.1.9 precedent). Declaring autoconf/2.72 would pull
  OHOS-built perl/5.42.2 whose Cwd.so breaks SDK autoreconf with
  `Perl_my_cxt_init: symbol not found`.
- HMDFS tmp handling: build() redirects TMPDIR/TMP/TEMP to the
  HMBS-provided writable dir (incl. autoreconf), `_build_environment()`
  carries all three, and generated `configure` gets umask 077 -> 022
  (gengetopt/cyrus-sasl/buildtorrent precedent).
- Upstream test audit (falsification applied):
  - `Makefile.am` SUBDIRS = src test (+doc); no TESTS/check_PROGRAMS.
  - `test/Makefile.am` builds only `noinst_PROGRAMS = mytest`.
  - `test/mytest.cpp` main() always returns EXIT_SUCCESS even though it
    contains intentional failures (TEST_FAIL, 0==1, throw mismatches) and
    ignores the `Suite::run()` return value. Exit 0 is NOT a pass signal.
  - 2026-09-10 evidence gate rejects no_tests/0: inventory scan sees
    TEST_ASSERT/TEST_FAIL in test/mytest.cpp and demands real execution
    (acf-lib-lua5.4 precedent). Fix: build() really executes the 7
    TEST_ADD sites as behavior verification (mytest --text-verbose output
    content gate + verdict gate proving run()==true/false detection),
    emits passed 7/7, persists res/hmbs_upstream.json, test_package
    re-emits every round; MANIFEST upstream_tests_exist true.
  - Recipe asserts the no-TESTS contract at build time so a future upstream
    harness cannot silently keep the stale verdict.
- test_package: CMake consumer `test_cpptest` with 2 suites (MathSuite,
  ThrowSuite, 7 asserts) using TextOutput::Verbose and returning the
  `Suite::run()` verdict; emits HMBS_TEST_PACKAGE_RESULT (2/2) and re-emits
  the no_tests upstream marker.
- Preflight 2026-09-09 failed at autoreconf: `Can't exec "aclocal"` plus
  autom4te `can't create temporary file /tmp/shXXXXXX.tmp: Read-only file
  system`. Fixed per above (unverified locally; awaiting HMBS preflight).
- Preflight 2026-09-10: autoreconf now succeeds in source_folder, but
  `Autotools.configure()` fails from the default build_folder cwd with
  `getcwd: cannot access parent directories` -> `working directory cannot
  be determined`. Prior raw `os.chdir` re-anchor to build_folder did not
  help. New route (unverified): in-source build via
  `conan.tools.files.chdir(self, self.source_folder)` for
  configure/make/check and for `package()` install, avoiding the broken
  `.../b/build-release` cwd entirely while keeping TMPDIR redirect,
  README touch, umask patch, and the no_tests verdict unchanged.
- Preflight 2026-09-10 (round 2, same log): root cause re-diagnosed as the
  CONFIG_SHELL x hnp-bash HMDFS getcwd storm
  (knowledge/drafts/DRAFT-autoconf269-config-shell-unset-not-empty:
  `shell-init: error retrieving current directory` storm + `configure:
  error: working directory cannot be determined`), not just a bad cwd.
  The helper's `Autotools.configure()` without `build_script_folder` runs
  in the default build_folder cwd, discarding the outer chdir. Fix: unset
  CONFIG_SHELL (never empty -- empty leaks via AC_SUBST as `SHELL =` ->
  `make: -c` Error 127) + seed PWD=source_folder (juise precedent) in
  build() and package(); pass
  `build_script_folder=self.source_folder` to configure; `_build_environment()`
  now prefers the HMBS TMPDIR and defines SHELL=/bin/sh. Awaiting HMBS
  preflight (round-2 fix verified for the getcwd storm; see next bullet).
- Preflight 2026-09-10 (round 3, new failure domain): getcwd storm gone,
  configure now executes, but config.guess 2024-07-27 fails with `unable
  to guess system type` (UNAME_SYSTEM=HarmonyOS) ->
  `configure: error: cannot guess build type; you must specify one`.
  Fix (zzuf 0.15 precedent): explicit native `--build/--host` triplets via
  AutotoolsToolchain when os==OHOS (`_ohos_gnu_triplet()`, arch-mapped;
  aarch64-unknown-linux-gnu is canonical to stock config.sub so no guess
  patch is needed -- the aarch64-linux-ohos route would additionally need
  a config.sub patch per aalib 1.4p5 and is avoided). Awaiting HMBS
  preflight.
- Preflight 2026-09-10 (round 4, new failure domain): build() compiles and
  links OK (`ar cr .libs/libcpptest.a` + `make check` no-op + no_tests
  marker emitted), but package() `Autotools.install()` fails at
  `src/Makefile:429 install-libLTLIBRARIES`: libtool runs the HMBS-shimmed
  `.../runtime/cpptest-2.0.0/bin/install -c .libs/libcpptest.a
  .../p//lib/libcpptest.a` (exit 0) yet the file never materializes, so the
  next libtool step `chmod 644 .../p//lib/libcpptest.a` dies with
  `No such file or directory` (Error 1/2, package() line 224). Platform caps
  `install_shim:true, chmod:0` implicate the shim/chmod chain, not the
  compile. Fix (argp-standalone/binn manual-install precedent, goffice
  tolerant-shim rationale): package() no longer calls `make install`;
  `_manual_install()` replicates the exact upstream layout -- 10
  include_HEADERS from src/Makefile.am -> include/, built lib(s) from the
  real build tree (`src/.libs`, searched under build_folder, its parent,
  and source_folder) -> lib/, generated libcpptest.pc (top Makefile.am
  pkgconfig_DATA, `@prefix@`-unsubstituted guard) -> lib/pkgconfig/ with
  the existing prefix relocate; no chmod issued. Awaiting HMBS preflight.
