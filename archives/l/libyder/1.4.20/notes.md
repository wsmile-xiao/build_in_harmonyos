Tested on HarmonyOS PC (OHOS 6.0, aarch64) with conan 2.29.1 + clang 15.

## Upstream

- Name: yder (packaged as libyder, matching the upstream project/package name
  `libyder` used by the CMake/CPack/pkg-config artifacts)
- Version: 1.4.20
- Tag: `v1.4.20`
- URL: https://github.com/babelouest/yder
- License: LGPL-2.1-or-later (LICENSE file)

## Build system

CMake 3.5+ upstream, C99. Upstream CMake options:

- BUILD_SHARED / BUILD_STATIC (mutually exclusive; default BUILD_SHARED=ON)
- WITH_JOURNALD (default ON on Linux; OFF for OHOS)
- BUILD_YDER_TESTING (default OFF; needs Check; on Linux/OHOS upstream also
  hard-requires Subunit)
- BUILD_YDER_DOCUMENTATION / BUILD_RPM / INSTALL_HEADER

This recipe produces the static archive (BUILD_SHARED=OFF / BUILD_STATIC=ON)
that downstream consumers (ulfius chain) link directly.

## OHOS platform notes

1. **journald**: no systemd on OHOS → `WITH_JOURNALD=OFF` at configure time.
   `yder-cfg.h` gets `Y_DISABLE_JOURNALD`, `y_init_logs` rejects
   `Y_LOG_MODE_JOURNALD`, and the upstream journald test case expects exactly
   that failure path (return 0) — the upstream-defined behaviour for a
   journald-less build (same mechanism upstream uses for non-systemd Linux).
2. **syslog**: OHOS libc exports `openlog/syslog/closelog`, so
   `Y_LOG_MODE_SYSLOG` works unmodified; the upstream syslog test passes.
3. **/tmp is read-only** (E002): the upstream `test_yder_init_file` case
   hard-codes `/tmp/test.log`. The portability patch routes the fixture
   through `$TMPDIR` when set (`__OHOS__`/`__MUSL__` guarded), falling back
   to `/tmp/test.log` unchanged on regular Linux. The `Y_LOG_MODE_FILE`
   semantics under test (fopen append + write + close) are untouched.

## Runtime vs. test-build dependencies

- **Runtime**: yder depends on libc + orcania (hard requirement: `o_malloc`,
  `o_strdup`, `o_free`, `split_string`, `o_strnullempty`, `o_strlen` used
  throughout `src/yder.c`; upstream CMake hard-requires
  `Orcania >= 2.3.3`). `orcania/2.3.3` is published on ohpcd (W0 verified
  with `conan download orcania/2.3.3 -r=ohpcd --only-recipe`).
- **Test-build stage**: the unmodified upstream check suite needs the Check
  framework. The recipe pulls `check/0.15.2` from ohpcd as a **test-only**
  (`test_requires`) dependency — available while building/running the
  upstream tests, never propagated to consumers, not part of the package_id.
  Same pattern as the repo precedents `orcania/2.3.3` and `libwbxml/0.11.10`.

## Why upstream tests are enabled (rule 4)

Upstream v1.4.20 ships one CTest test program (`test/yder_test.c`, 15
`START_TEST` cases registered into a single `yder_test` executable) built
with `BUILD_YDER_TESTING=ON`. It is registered as EXCLUDE_FROM_ALL and
executed here inside `conan create` (via `ctest`), so the official tests
genuinely pass 15/15 on OHOS aarch64 (`100%: Checks: 15, Failures: 0,
Errors: 0`).

Case list (all pass): init_console, init_file, init_syslog, init_journald
(expect-failure path under Y_DISABLE_JOURNALD), init_error_file,
init_multiple_error, init_multiple_ok, init_close_multiple, callback,
level_debug, level_info, level_warning, level_error, date_format,
newline_split.

## Patches

`0001-ohos-portability.patch` (portability, CMakeLists.txt +
test/yder_test.c wiring only):

1. CMakeLists: accept `Orcania_VERSION_STRING` (camel case, what Conan
   CMakeDeps exports) in the version gate in addition to the upstream
   `ORCANIA_VERSION_STRING`. The version gate is still enforced by
   `find_package(Orcania 2.3.3 REQUIRED)` via `OrcaniaConfigVersion.cmake`.
2. CMakeLists: `find_package(Check)` → `find_package(Check MODULE)`. The
   conan toolchain sets `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`; without this
   the config-mode `check-config.cmake` resolves first (`Check_FOUND` /
   `Check::check`) and upstream's bundled `FindCheck.cmake`
   (`CHECK_FOUND` / `Check::Check`) never runs, silently dropping the CTest
   tree.
3. CMakeLists: `find_package(Subunit REQUIRED)` → `find_package(Subunit)`
   and link `Subunit::Subunit` only `if (SUBUNIT_FOUND)` — same relaxation
   as orcania 2.3.3 (the ohpcd libcheck is self-contained and yder_test
   uses only `check.h`).
4. CMakeLists: test link list uses `Orcania::Orcania-static` when that is
   the exported target (Conan CMakeDeps static spelling), mirroring the
   library link block that already handles both spellings.
5. test/yder_test.c: `Y_TEST_LOG_FILE` resolves the log fixture through
   POSIX `getenv("TMPDIR")` when set, falling back to `/tmp/test.log`
   unchanged on regular Linux. No platform ifdefs (R8: platform
   conditional macros are forbidden; plain POSIX getenv behaves
   identically on Linux when TMPDIR is unset). The `test_yder_init_file`
   case additionally verifies the written log content (app name + message
   present in the file), so a silently-failing write can no longer
   masquerade as a pass. No assertion's expected result is modified.

## Notes

The header ships as `yder.h` + generated `yder-cfg.h`, both public. The
recipe exposes `Yder::Yder-static` (cmake target), `libyder` (pkg-config
name). `build()` deliberately seeds `CHECK_INCLUDE_DIR`/`CHECK_LIBRARY`
with the conan check package paths instead of `CMAKE_PREFIX_PATH` (same
rationale as orcania: keep find_package(Check) in MODULE mode).

test_package adds a 5-group HarmonyOS consumer check (console init/close,
file mode into `$TMPDIR`, callback level filtering, date format
accept/reject, newline split) that links `Yder::Yder-static` and runs on
OHOS aarch64.
