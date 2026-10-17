# lensfun-tools 0.3.4 adaptation notes

## Scope

Platform task `lensfun-tools 0.3.4` is the distro-style *tools* subpackage of the
Lensfun project v0.3.4 (github.com/lensfun/lensfun). Upstream apps installed by
this package: `lenstool` (C++), `lensfun-update-data` / `lensfun-add-adapter`
(python3, `import lensfun`), `g-lensfun-update-data` (sh wrapper). `tools/`
contains development-only scripts and is not installed by upstream.

The `lensfun` library archive (`archives/l/lensfun/0.3.4`, status built,
2026-05-21) has no published Conan recipe and `conan install
--requires=lensfun/0.3.4 -r=ohpcd --build=never` reports *Unable to find
'lensfun/0.3.4' in remotes* (w0 logs). PF4 forbids smuggling a dependency
recipe into this PR, so the package builds the in-tree library statically
(`BUILD_STATIC=ON`) and ships only the tool binaries + database; the library
recipe/publish remains a separate upstream work item.

## Dependency selection (W0)

- `glib2/2.88.0.1` — liblensfun core runtime; binaries available on ohpcd.
- `libpng/1.6.39` — lenstool image I/O (`FIND_PACKAGE(PNG REQUIRED)` when
  `BUILD_LENSTOOL=ON`). libpng 1.6.58/1.6.58.x pin zlib/1.3.2 (or 1.3.1.1),
  which conflicts with glib2/2.88.0.1's `zlib/1.3.1`; libpng/1.6.39 pins
  zlib/1.3.1 and resolves the graph cleanly. The conflict is reproducible with
  `conan graph info --requires=<ref>` against the ohpcd remote (recorded in the
  task W0 logs); the final W0 check passed on the selected pair.
- zlib/pcre2 stay transitive (libpng, glib2).

## Build configuration

- `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` — upstream declares
  `cmake_minimum_required(VERSION 2.8.12)`; device CMake is 4.1.2
  (same switch as archives/l/lensfun historical notes).
- `BUILD_LENSTOOL=ON` gates the whole `apps/` tool set; `BUILD_TESTS=OFF`
  (upstream glib test programs in `tests/` exercise the library API, not the
  tools); `BUILD_DOC=OFF`.
- glib discovery: upstream consumes glib through its own FindGLIB2 variables
  (`GLIB2_INCLUDE_DIRS`, `GLIB2_LIBRARIES`, fed into INCLUDE_DIRECTORIES and
  TARGET_LINK_LIBRARIES). CMakeDeps publishes `glib2Config.cmake`, and on the
  case-insensitive HMDFS the package name also satisfies
  `find_package(GLIB2)` config mode (`GLIB2_DIR` points into the CMakeDeps
  generators folder), so FindGLIB2 never runs and the variables stay empty —
  the recipe therefore sets the three GLIB2 cache variables explicitly
  (glib-2.0 include dir, glibconfig.h dir, and the static library list in
  link order: libglib-2.0.a, libpcre2-8.a, libffi.a, libintl.a), which is
  deterministic on any filesystem. The published glib2 package is static-only.
- libpng/zlib discovery: patched to CMake config mode
  (`FIND_PACKAGE(libpng CONFIG REQUIRED)` + the `libpng::libpng` target, which
  carries zlib transitively) so the Conan CMakeDeps generators resolve them;
  the generated config names are the lowercase package names
  (libpng-config.cmake / zlib-config.cmake), not the FindPNG module names.

## Patches

1. `0001-honor-install-python-module-option.patch` — upstream defines the
   `INSTALL_PYTHON_MODULE` option but never consults it: the `apps/` python
   block runs whenever `python3` exists and `python3 setup.py build` fails on
   OHOS (`ModuleNotFoundError: setuptools`, verified on the device). The patch
   gates the block on the existing option; the recipe sets it OFF.
2. `0002-png-config-mode.patch` — see above.
3. `0003-cmake-minimum-version-range.patch` — declares the minimum CMake
   version with the `2.8.12...3.5` range syntax; CMake >= 4 removes plain
   `< 3.5` compatibility and the toolchain-variable route did not take effect
   before `cmake_minimum_required` (first finish round).

No platform macros are introduced (`__OHOS__` absent from all patches).

## Python helper module

The scripts `import lensfun`; upstream installs the module via
`setup.py install` into `lib/python3.X/site-packages`. The recipe copies
`apps/lensfun/__init__.py.in`, substitutes the configured paths
(`CMAKE_INSTALL_FULL_DATAROOTDIR` → `<package>/share`,
`CMAKE_INSTALL_LOCALSTATEDIR` → `<package>/var`, `LENSFUN_DB_VERSION` → `1`)
into `share/lensfun/python/lensfun/__init__.py`, and exports `PYTHONPATH`
through `runenv_info`, so the scripts work without a system setuptools.

## Lens database

`lenstool` resolves the database through `lfDatabase::Load()`, which reads the
compile-time `CONF_DATADIR` (`<CMAKE_INSTALL_PREFIX>/share/lensfun`) plus
XDG user dirs. Conan builds with the package folder as prefix, so the packaged
`share/lensfun/version_1` database is found at consumer runtime. `lenstool`
returns `LF_NO_DATABASE` ("ERROR: Database could not be loaded") when the
database is missing — test.sh asserts this does not happen.

## L5 baseline re-establishment

`reports/baseline.json` was re-established (deleted and re-captured) after two
conan-verify rounds of otherwise identical sources. Both changed artifacts are
per-round by construction:

- `bin/lenstool` — ELF build-id/embedded build paths change with every round
  because each verification round uses a randomly named private CONAN_HOME.
- `share/lensfun/python/lensfun/__init__.py` — the recipe substitutes the
  absolute package prefix (`CMAKE_INSTALL_FULL_DATAROOTDIR` → package folder)
  into the module, which is the relocation mechanism for the helper scripts.

No source or recipe semantic change is involved (the conan-verify hint
sanctions re-baselining in exactly this situation).

## Upstream tests (R51)

Upstream `tests/` holds **14 test case functions** in 7 glib programs
(test_database, test_modifier, test_modifier_color, test_modifier_subpix,
test_modifier_coord_scale, test_modifier_coord_distortion,
test_modifier_coord_geometry — 2 cases each, the `_parallel` variants
included), registered as 8 CTest entries (`ctest -N`: Database, Modifier,
Modifier_color, Modifier_subpix, Modifier_coord_scale,
Modifier_coord_distortion, Modifier_coord_geometry, Database_integrity).
Counts reproduced on the unpacked v0.3.4 source:

    grep -rn "^void test_" tests/*.cpp | wc -l          # 14 (cases — the N used)
    grep -rn "ADD_TEST" tests/CMakeLists.txt | wc -l    #  8 (CTest registrations)
    ls tests/test_*.cpp | wc -l                         #  7 (programs)
    grep -rn "g_assert\|assert(" tests/*.cpp | wc -l    # 34 (assertion sites)

`N = 14` is the case-function count (one unit, per R51's "do not mix the four
counting units"); 7/8/34 are disclosed above with their units but are not used
as N. **N′ = 0 of 14 executed — NOT_RUN with a technical cause, not a PASS**:
the suite drives the **library** API (`lfFixture`/`lfModifier`/`lfDatabase`),
which this tools-only package does not deliver; it is gated by upstream
`OPTION(BUILD_TESTS ... OFF)` (CMakeLists.txt:53/177) and the recipe sets
`BUILD_TESTS=False` (conanfile.py, "upstream glib tests target the library, not
the tools"), and `apps/` carries no `add_test` target and no test source, so the
tools subpackage has no upstream test entry point. Only `test_database` and
`Database_integrity` touch the lens database data that this package does ship —
that surface is covered by test_package assertions 4-5 (the packaged
`share/lensfun/version_1` database loads and answers a camera/lens query); the
other 12 cases are library-algorithm coverage outside this package's delivery
scope. The consumer test_package exercises the real binaries (5/5) instead — see
test_package/MANIFEST.yml.

## commands.json (R38)

All four `bin/` entries are declared in `archives/l/lensfun-tools/commands.json`
(type tool). `g-lensfun-update-data` runs `lensfun-update-data` bare (a network
update) and would exceed the smoke-test scope, so test.sh exercises the two
other tools plus the packaged database; the wrapper stays packaged as shipped.
