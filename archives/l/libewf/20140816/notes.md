# libewf 20140816 adaptation notes

- Upstream is the legacy libewf line (`libyal/libewf-legacy`); 20140816 is the
  last stable legacy release and is still the pinned version in Homebrew and
  Debian/Ubuntu. The release archive hash below is cross-confirmed against the
  Homebrew formula (`6b2d078f...7025a9`), not just the download page.
- The project uses Autotools and builds the static/shared `libewf` library plus
  the `ewftools` command-line tools (`ewfinfo`, `ewfexport`, `ewfverify`,
  `ewfacquire`, `ewfacquirestream`, `ewfmount`, `ewfrecover`).
- Every libyal support library (`libcerror`, `libbfio`, ...) is bundled in-tree
  as configure SUBDIRS, so the recipe declares no Conan `requires`. Only zlib
  (write support) and OpenSSL EVP (hash support) are optional system
  dependencies and both are auto-detected from the toolchain sysroot.
- The bundled 2014 `config.sub` knows `aarch64` but no `ohos` OS triplet, so on
  OHOS the recipe passes `--build/--host=aarch64-unknown-linux-gnu`
  (a52dec/0.7.4 precedent for pre-2015 configure scripts). No committed patch
  is needed. `--with-libfuse=no` matches Homebrew (no FUSE on OHOS); python
  bindings stay at the upstream default (`--enable-python=no`).
- `make check` is invoked during `build()`. The automake universe is 17 TESTS
  scripts at most: 7 unconditional (`test_library`, `test_glob`, `test_seek`,
  `test_read`, `test_ewfverify`, `test_ewfverify_logical`, `test_ewfinfo`),
  9 write suites gated on zlib write support, and 1 pyewf suite gated on
  `--enable-python`. The 33 `ewf_test_*` C programs are harnesses driven from
  inside the shell suites. The recipe parses `test-suite.log` TOTAL/PASS/FAIL/
  SKIP for the `HMBS_UPSTREAM_TEST_RESULT` marker, so the evidence counts are
  truthful whether or not zlib is present.
- HMDFS/autoconf mitigations are applied at build time only (darts/0.32
  pattern, generated `configure`/`config.status`, no committed patch): writable
  `TMPDIR` injection (E002), `pwd` fallback to `$PWD` plus `umask 022`
  (shell_getcwd, E011), and `config.status` mktemp redirect (E114).
- The consumer test links the installed `libewf` and checks the public ABI:
  `libewf_get_version()` equals `"20140816"`, the read access flag equals
  `LIBEWF_ACCESS_FLAG_READ`, the handle initialize/free lifecycle works, and
  `libewf_check_file_signature()` returns 0 for a generated plain-text fixture.

## Watch items for the preflight round

- `C compiler cannot create executables` root cause, 4th round: the profile
  `tools.build:compiler_executables:c=/data/service/hnp/bin/clang` does not
  exist on this worker (`inaccessible or not found`, SMOKE_LINK_FAILED), so
  all prior configure-arg/env/log forensics were moot. The recipe now keeps
  the conf path only when it is present+executable and otherwise falls back
  to PATH `clang/cc/gcc` (bwm/0.6.3 pattern) with matching `clang++`/`g++`
  derivation: generate layer saves `libewf-fallback-cc` build script, build
  layer sets `os.environ CC/CXX`, and the manual configure + smoke commands
  carry an inline `CC=.. CXX=..` prefix so the fallback wins independent of
  conanbuild merge order (same reason as the CONFIG_SHELL prefix).
- VPATH generated-header failure, 5th round: with the compiler fixed,
  configure passed but `make` died in `libcthreads` on
  `fatal error: 'libcerror_definitions.h' file not found`. The 2014 libyal
  tree never supported out-of-source builds; sibling Makefiles only search
  `-I.`/`-I$(srcdir)` while `*_definitions.h` is generated into the build
  tree. Kept Conan's out-of-source layout and appended bundled-lib `-I`
  for both source and build trees to `tc.cflags` (single channel, no
  CPPFLAGS clobber). Also fixed the fallback smoke `CC=.. CXX=.. if ...`
  prefix (invalid before the `if` keyword under dash) to export-chaining.
- VPATH -I backstop proved insufficient, 6th round: same
  `libcerror_definitions.h` failure at build line 578 with the new recipe
  active, so extra `-I` flags alone are not the cure (whether the header
  was never generated or the flags never reached libtool is undecided).
  Different route per second-policy-cycle: build in-source like upstream
  consumers do (`folders.build = src`, `make V=1`), keeping the `-I` set
  only as a backstop; make failure now dumps decisive forensics (header
  find hits, libcthreads Makefile include lines, toolchain CFLAGS check).

- `C compiler cannot create executables` triage (3rd round): the recipe now
  runs a pre-configure `$CC` smoke test (link + run a trivial program,
  diagnostic only) and, on configure failure, dumps the `config.log`
  sections around the compiler-works test instead of the tail (the tail
  only holds cache variables + exit code). Smoke FAIL => driver/env fault
  (TMPDIR writability, lld runtime, sysroot); smoke OK + configure FAIL =>
  bisect the manual invocation delta vs stock `Autotools.configure()`
  (unset prefix, /bin/sh interpreter, configure patches).
- If the OHOS sysroot lacks zlib, the 9 write suites stay unregistered
  (`HAVE_WRITE_TESTS` false); the marker then reports discovered 7 with a
  non-empty reason. If a fuller run is wanted, a `zlib` requirement can be
  added once its registry presence is confirmed with `conan download`.
- If the static consumer link misses transitive system libs (e.g. `-lz`,
  `-lcrypto`, `-lm`), add them to `package_info()` `system_libs` from the
  preflight link log.

- 2nd policy cycle (7th round): retired the shebang-rewrite + POSIX-harness route after 3 consecutive failures. Source audit of the 20140816 tarball refutes the old hypothesis: none of the 19 scripts under tests/ hardcodes /tmp (all use relative TMPDIR="tmp$$"), the failure signature moved from exit 127 to FAIL test_glob.sh exit 1 while Testing: ... (PASS) lines prove the runner executes, and collapsing INPUT_FILES/OPTIONS/ARGUMENTS arrays to strings corrupts upstream iteration semantics. New route keeps upstream logic pristine: read-only interpreter probe (no file changes), minimal tool-compat normalization only (sed <script> -i <file> to sed -i <script> <file>, egrep to grep -E; identical on GNU), narrowed /tmp redirect (TMPDIR assignments only), truthful marker aggregation across both trees with .trs fallback and failing-suite names, and removed the test_package hardcoded upstream re-emit (evidence fabrication). Next preflight decides: green falsifies nothing further; still-red log now names the exact sub-case.

- 3rd fingerprint fix, two-tier upstream tests (libbde/20240502 precedent, same libyal harness and same env-bash-127): last round's read-only probe proved NO runnable bash exists worker-wide (ls denies /bin/bash, env exec fails), so the revert-plus-probe route is falsified and pristine scripts exec-fail 16/16 at the shebang. New route: tier-1 native make check only when a runnable bash (exec-probed, not just X_OK: the profile HNP bash exists but cannot run from HMDFS) AND non-empty tests/input* fixtures both exist, with bbin staging for env-bash resolution; tier-2 direct otherwise (release-tarball case): make check TESTS= builds check_PROGRAMS, then driver-identical runs -- 25 no-arg library binaries, 32 write-matrix invocations, 20 python-replicated glob fixture cases (odometer ported from test_glob.sh, byte-exact trailing-newline comparison with CRLF normalization) = 77 assertions, exactly CI-with-bash executable coverage since 12 input-dependent suites SKIP by upstream design with zero assertions. Marker payload persisted to res/upstream_test_result.json and re-emitted by test_package (missing file = hard error, no silent pass). Unverified, awaiting next preflight verdict.

- 4th fix, off-by-one in direct tier (this round): preflight reached 77/78 with the single failure `direct FAIL: ewf_test_write rc=1 out=Missing EWF image filename`. Upstream audit refutes the 26-count: test_library.sh defines 23 LIBRARY_TESTS + 2 LIBRARY_TESTS_WITH_INPUT (handle/support, no-arg fallback when input2 absent) = 25 no-arg binaries; ewf_test_write is driven only by test_write.sh with -B/-c/-S plus filename (main() exits 1 without filename by design). The slice `_need[:26]` therefore misclassified ewf_test_write as no-arg. New route keeps the two-tier structure but corrects the partition to 25 + 32 + 20 = 77 driver-identical assertions (no test deleted, matrix/glob untouched). Awaiting next preflight verdict.
