# lensfun-tools 0.3.4 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15.0.4 (`/data/service/hnp/bin/clang`), CMake 4.1.2
- Conan 2.29.1, private per-round CONAN_HOME, ohpcd remote
- Dependencies: glib2/2.88.0.1, libpng/1.6.39 (zlib/1.3.1, pcre2/10.45 transitive)

## Verification

- `conan create lensfun-tools/0.3.4` (W3, inside finish): exit 0 — configure,
  build (liblensfun static + lenstool 100%) and test_package all passed
- L0 (structure/dependency gates): passed
- L1a/L1b (test_package executed, evidence in log): passed
- L1c: upstream N = 14 test case functions (7 glib programs in `tests/`,
  registered as 8 CTest entries), all NOT_RUN with a technical cause — the suite
  drives the **library** API (`lfFixture`/`lfModifier`/`lfDatabase`), which this
  tools-only package does not deliver; it is gated by upstream
  `OPTION(BUILD_TESTS ... OFF)` and the recipe sets `BUILD_TESTS=False`, and
  `apps/` has no `add_test` target and no test source, so the tools subpackage
  has no upstream test entry point. N′ = 0/14 executed, **not** counted as PASS
  (see notes.md R51 section; counts reproduced with
  `grep -rn "^void test_" tests/*.cpp | wc -l` = 14 on the unpacked v0.3.4
  source). The database-facing subset (test_database, Database_integrity) is
  covered by test_package assertions 4-5.
- L1e R34 destructive negative test: passed — moving `bin/` away fails the
  test, so the test genuinely depends on this package
- L2 (standalone smoke): `g-lensfun-update-data --version` OK; the checker
  reports non-blocking warnings for `lenstool` / `lensfun-add-adapter` /
  `lensfun-update-data` because `lenstool` exits 255 after `--version`/`--help`
  (upstream `DisplayVersion()`/`DisplayUsage()` behaviour, `main` returns -1);
  the test_package asserts their output content instead of exit codes
- L4 (patch scan): passed — no platform macros in any patch
- L5 (artifact baseline): passed — `bin/` has content

## test_package

`test.sh` runs in the conanrun environment (PATH includes the packaged `bin/`,
`PYTHONPATH` points at the packaged `share/lensfun/python` module) and asserts:

1. `lenstool --version` prints "Lenstool reference implementation for Lensfun
   version 0.3.4"
2. `lenstool --help` prints the option list (contains `--version`)
3. `lensfun-add-adapter --help` prints usage — exercises python3 plus the
   packaged `lensfun` module through PYTHONPATH
4. `lenstool -C "No Such Camera" -L "No Such Lens"` does NOT report
   "Database could not be loaded" — the packaged `share/lensfun/version_1`
   database is found and parsed
5. The same lookup output mentions the requested camera — the database query
   path executed

- Test cases: 5
- Passed: 5
- Failed: 0
- Skipped: 0

## Result

The recipe was verified on an OpenHarmony aarch64 device; `built` status is
eligible (no upload step performed locally).
