Tested on HarmonyOS PC (OHOS 6.0, aarch64) with conan 2.29.1 + clang 15.

## Upstream

- Name: hoel (packaged as libhoel, matching the upstream pkg-config name
  `libhoel` used by the CMake/CPack artifacts)
- Version: 1.4.29
- Tag: `v1.4.29`
- URL: https://github.com/babelouest/hoel
- License: LGPL-2.1-or-later (LICENSE file)

## Build system

CMake 3.14+ upstream, C99. Upstream CMake options:

- WITH_SQLITE3 / WITH_MARIADB / WITH_PGSQL (default all ON; MariaDB and
  PostgreSQL client libraries are not available on the OHOS PC conan
  registry, so this recipe disables those backends and keeps sqlite3 —
  W0 checked, mariadb/pgsql absent from ohpcd)
- BUILD_STATIC (default OFF; recipe uses ON — static archive for the
  ulfius chain, same as libyder 1.4.20)
- BUILD_HOEL_TESTING (default OFF; needs Check + Subunit — Subunit relaxed
  by the portability patch, ohpcd libcheck is self-contained)
- BUILD_HOEL_DOCUMENTATION / BUILD_RPM / INSTALL_HEADER

The upstream CMakeLists always builds the shared `hoel` target alongside
`hoel_static` (unlike yder which guards the shared target behind
BUILD_SHARED). The recipe's package() only installs what INSTALL_HEADER
places; both targets are built but only the requested flavour is packaged
(hoel_static -> libhoel.a; the shared libhoel.so produced in the build tree
is not installed because BUILD_STATIC=ON puts hoel_static in the install
TARGETS list and the shared target's install rule is unconditional BUT the
package step strips it — see the conanfile rmdir/package handling).

## OHOS platform notes

1. **/tmp is read-only** (E002): the upstream tests hard-code
   `/tmp/test.db` (test/core.c DEFAULT_BD_PATH, test/multi.c
   SQLITE_BD_PATH). The portability patch routes the fixture through
   `$TMPDIR` when set (pure POSIX getenv, no platform ifdefs), falling back
   to /tmp/test.db unchanged on regular Linux.
2. **sqlite3 CLI missing**: the upstream CI seeds the fixture with
   `sqlite3 /tmp/test.db < test/test.sqlite3.sql`. OHOS has no sqlite3
   CLI; the recipe's _run_upstream_ctests applies the same schema through
   python's sqlite3 module (identical result: an empty test_table with the
   upstream columns).
3. **CMakeDeps case mismatch**: conan's CMakeDeps exports jansson as the
   lowercase `jansson::jansson` target while hoel's upstream gate links
   `Jansson::Jansson` from its bundled cmake-modules/FindJansson.cmake.
   The portability patch forces `find_package(Jansson MODULE)` so the
   bundled module runs (seeded with JANSSON_INCLUDE_DIR/JANSSON_LIBRARY
   from the conan package), same pattern as Check.
4. **SQLite3**: conan sqlite3/3.53.4 CMakeDeps file is lowercase
   (sqlite3-config.cmake, target sqlite3::sqlite3); hoel calls
   `find_package(SQLite3)` with CMake's bundled FindSQLite3.cmake (target
   SQLite::SQLite3). The portability patch forces MODULE mode and the
   recipe seeds SQLITE3_INCLUDE_DIR/SQLITE3_LIBRARY; the bundled module
   then defines SQLite::SQLite3 which HOEL_LIBS links.
5. **MariaDB/PostgreSQL backends trimmed**: WITH_MARIADB=OFF /
   WITH_PGSQL=OFF (W0: no mariadb/postgres client lib on ohpcd). The
   portability patch additionally degrades the REQUIRED lookups so a
   missing backend is not a configure error (upstream already has the
   degradation branch; REQUIRED just made it unreachable). sqlite3
   backend provides full DB coverage for the upstream test suite (both
   core and multi run sqlite).
6. **rt library**: upstream appends `rt` to TEST_LIBS on non-Apple
   non-Windows. OHOS musl provides rt stubs; the link works unmodified.

## Runtime vs. test-build dependencies

- **Runtime**: hoel depends on orcania (o_malloc/o_free/split_string used
  throughout src/hoel.c), yder (y_log_message error paths; hoel.h includes
  <yder.h>), jansson (json_t query language) and sqlite3 (the enabled
  backend). All published on ohpcd (W0 verified with conan download).
- **Test-build stage**: the unmodified upstream check suites (core 12
  cases + multi 9 cases) need the Check framework. The recipe pulls
  check/0.15.2 from ohpcd as a **test-only** (test_requires) dependency —
  same pattern as orcania 2.3.3 and libyder 1.4.20.

## Why upstream tests are enabled (rule 4)

Upstream v1.4.29 ships two CTest test programs (test/core.c and
test/multi.c, 12 + 9 = 21 START_TEST cases) built with
BUILD_HOEL_TESTING=ON. They are registered as EXCLUDE_FROM_ALL and
executed here inside `conan create` (via ctest), so the official tests
genuinely pass 21/21 on OHOS aarch64 (sqlite3 backend).

Case list (all pass) — core: hoel_init, escape_string,
escape_string_with_quotes, insert, update, delete, json_insert,
json_update, json_delete, json_select, json_escape,
json_generate_where_clause; multi: escape_string,
escape_string_with_quotes, insert, update, delete, json_insert,
json_update, json_delete, json_select.

## Patches

`0001-ohos-portability.patch` (portability, CMakeLists.txt +
test/core.c + test/multi.c):

1. CMakeLists: force MODULE mode for Jansson/SQLite3/Check lookups so the
   bundled find-modules stay in charge under
   CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON (conan CMakeDeps config-mode
   targets would otherwise bypass the upstream gates).
2. CMakeLists: degrade MariaDB/PostgreSQL REQUIRED lookups to backend OFF
   (client libs unavailable on the OHOS PC conan registry).
3. CMakeLists: accept the camel-case Orcania/Yder VERSION_STRING that
   Conan CMakeDeps exports in the upstream version gates (gate still
   enforced through the *ConfigVersion.cmake files).
4. CMakeLists: relax the Subunit hard requirement for the test tree
   (ohpcd libcheck is self-contained) and link the tests against the
   actual library target (hoel_static) under BUILD_STATIC.
5. test/core.c + test/multi.c: resolve the /tmp/test.db fixture through
   POSIX $TMPDIR when set, falling back to /tmp/test.db unchanged on
   regular Linux. No platform ifdefs; upstream test assertions keep their
   expected results.
