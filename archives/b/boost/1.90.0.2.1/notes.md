# Boost 1.90.0.2.1 Boost.Python dependency notes

## Scope

This package extends the existing Boost 1.90.0 CMake-based component recipe so
that downstream packages such as eigenpy can consume Boost.Python on OHOS.

The recipe keeps the previously validated compiled components and adds the
Boost.Python library for the target CPython ABI:

- `Boost::program_options`
- `Boost::filesystem`
- `Boost::system`
- `Boost::python`
- `Boost::python3`
- `Boost::python312`

The source is still the official Boost 1.90.0 CMake release asset. File scope is
limited to `archives/b/boost/1.90.0.2.1/**`.

Task hall record:

- Task ID: `4415`
- URL: `https://ohpcd.atomgit.com/contrib`
- Activity ID: `6`
- Claimer: `xuguowei`
- Required branch: `feat/boost-1.90.0.2.1`

## Knowledge Drafts

This adaptation adds seven Boost-specific draft knowledge entries:

- `knowledge/drafts/DRAFT-boost-python312-cmake-discovery.kv` / `.md`:
  pin Boost.Python CMake `FindPython` to the OHOS CPython 3.12 ABI expected by
  downstream consumers.
- `knowledge/drafts/DRAFT-boost-python312-test-runtime-libpython.kv` / `.md`:
  preserve Conan `VirtualRunEnv` while prepending the external CPython libdir for
  Boost.Python runtime tests.
- `knowledge/drafts/DRAFT-boost-cmake-hmdfs-versioned-soname-links.kv` / `.md`:
  suppress Boost CMake versioned shared-library install links on OHOS/HMDFS and
  validate the unversioned package layout through consumer targets.
- `knowledge/drafts/DRAFT-boost-ohos-gnu-ld-for-cmake-shared-links.kv` / `.md`:
  force GNU ld for Boost CMake shared-library and consumer links when official
  CI does not expose the OHOS SDK `lld` `libxml2.so.16` runtime dependency.
- `knowledge/drafts/DRAFT-boost-cmake-unversioned-dt-soname-on-ohos.kv` / `.md`:
  keep unversioned Boost CMake package outputs on OHOS while explicitly adding
  per-target `DT_SONAME` metadata required by the L5 quality gate.
- `knowledge/drafts/DRAFT-boost-python312-ohos-python-target-intl-linkage.kv` / `.md`:
  avoid `Python::Python` leaking an unresolved `-lintl` link item in official
  CI by using the already-discovered absolute `Python_LIBRARY` for OHOS
  Boost.Python smoke tests.
- `knowledge/drafts/DRAFT-boost-ohos-representative-upstream-tests.kv` / `.md`:
  record the review fix for Boost upstream test accounting: do not report the
  upstream suite as zero, and execute a focused upstream subset when the full
  Boost test matrix is outside the package scope.

## Versioning

`boost/1.90.0.2` is already published with a different recipe revision. The
CI R37 gate rejects modifying a published recipe under the same version, so the
Boost.Python rebuild is carried as `boost/1.90.0.2.1`.

## Python ABI

The OHOS runner currently provides CPython 3.12 under `~/usr/local`. The recipe
locks Boost.Python discovery to Python 3.12 because downstream eigenpy is built
against that runtime. During `generate()`, the recipe queries the selected
interpreter's `sysconfig` and passes these hints to CMake FindPython:

- `Python_EXECUTABLE`
- `Python_ROOT_DIR`
- `Python_INCLUDE_DIR`
- `Python_LIBRARY`

`libpython3.12.so` is resolved from the interpreter's loaded mapping or from the
interpreter prefix.

## OHOS linker

The official CI build #31668 failed in `cmake.build()` while linking Boost shared
libraries because clang tried to execute the OHOS SDK `lld`, whose runtime
`libxml2.so.16` dependency was not visible in the CI environment:

```text
Error loading shared library libxml2.so.16: (needed by .../ohos/native/llvm/bin/lld)
Error relocating .../ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found
clang-15: error: unable to execute command: No such file or directory
```

The recipe now sets CMake executable, shared-library, and module linker flags to
`-fuse-ld=/data/service/hnp/bin/ld` on OHOS. The same flag is applied in
`test_package` so the consumer executable does not depend on interactive shell
`LD_LIBRARY_PATH` setup. While touching the CI path, `numeric_conversion` was
also corrected to Boost CMake's nested module spelling, `numeric/conversion`,
removing the configure warning where Boost ignored the misspelled module name.

## OHOS SONAME

Shadow CI follow-up `r10` passed `conan create`, built and executed the
Boost.Python `test_package`, then failed the L5 quality gate because the
packaged unversioned `libboost_*.so` files had no `DT_SONAME`.

The previous HMDFS patch gated BoostInstall.cmake's `VERSION` block to avoid
versioned library outputs or install aliases. That kept the package layout
unversioned, but also removed the CMake path that normally emits SONAME. The
patch now adds a target-scoped link option for OHOS unversioned installs:

```cmake
target_link_options(${LIB} PRIVATE "-Wl,-soname,$<TARGET_FILE_NAME:${LIB}>")
```

This preserves the unversioned library layout while letting each compiled Boost
shared object advertise its own file name, such as `libboost_python312.so`, as
the SONAME.

## Conan metadata

`package_info()` scans packaged libraries for `boost_python*` and exports aliases
for the actual ABI library. With Python 3.12 this exposes:

- `Boost::python`
- `Boost::python3`
- `Boost::python312`

This keeps consumers that request generic Boost.Python names and consumers that
request the ABI-specific component both covered.

## test_package

The consumer test still verifies the previously required compiled components and
header-only modules. It now also requires `Boost::python312`, links
the absolute `Python_LIBRARY` on OHOS, initializes CPython, and exercises
`boost::python::dict` plus `boost::python::extract<int>()` at runtime. The
absolute library avoids official CI's `Python::Python` imported target adding a
bare `-lintl` link item without a matching default library path.

On OHOS, the executable is signed before execution and the CPython libdir is
prepended to `LD_LIBRARY_PATH` for the test run. Without that, the loader finds
Boost libraries from `conanrun` but cannot resolve `libpython3.12.so.1.0` and the
`Py_*` symbols used by Boost.Python.

## Upstream Component Tests

Boost 1.90.0 contains a large upstream test tree. In the CMake release source
used by this recipe, `libs/*/test` contains 16590 test-related files by the
counting policy used for this PR (`*.cpp`, `*.hpp`, `*.h`, `*.py`,
`Jamfile*`, and `CMakeLists.txt`). The component trees directly relevant to this
package contain 380 such files:

- `filesystem`: 53
- `program_options`: 22
- `system`: 118
- `python`: 187

The full Boost all-library test matrix is not run in this dependency PR because
this package publishes a selected component set for downstream eigenpy. After
review comment `186800536`, the recipe no longer uses the former 4-item
representative subset. `build()` now collects 356 selected-component upstream
evidence items, covering 356/380 test-related files by the PR counting policy:

- Boost.System and Boost.ProgramOptions: a second CMake build tree enables
  `BUILD_TESTING=ON`, builds selected upstream test targets, signs build-tree
  ELF files, then runs 171 matching CTest entries with
  `ctest -R '^(run|run-fail|compile-fail|link-fail)-boost_(system|program_options)-'`.
- The same CMake inventory includes 2 compile/link-only upstream checks.
- Four Boost.System `error_code_test` CTest entries are skipped because OHOS
  libc error message/category semantics differ from the upstream host
  expectations seen in official CI #32493.
- Boost.Filesystem has no upstream `test/CMakeLists.txt` in the 1.90.0 CMake
  source, so the recipe compiles 15 Jamfile-derived C++ tests from
  `libs/filesystem/test` and `libs/filesystem/example`, and runs 14 of them.
  `operations_unit_v4` is compile-only on OHOS because its upstream query test
  inspects `/`, which returns `Permission denied` for HNP users in CI #32663.
- Boost.Python compiles 89 top-level `libs/python/test/*.cpp` sources, skipping
  only 9 documented negative, Windows-only, or `std::auto_ptr` conditional
  entries. `copy_ctor_mutates_rhs.cpp` remains counted; the standalone compile
  check force-includes `boost/mpl/bool.hpp` so the private `is_auto_ptr.hpp`
  header sees `mpl::false_`, matching the upstream build context exposed by
  official CI #32568. `pointee.cpp` is skipped because it directly names
  removed `std::auto_ptr`, matching the OHOS C++17 failure in CI #32606.
- Boost.Python compiles 72 `libs/python/test/*.py` scripts with
  `python -m py_compile` and `PYTHONPYCACHEPREFIX` redirected into the build
  tree.
- Boost.Python also builds 7 core extension modules (`dict`, `list`, `tuple`,
  `str`, `long`, `object`, `slice`) and verifies ELF magic, `.codesign`,
  `PyInit_*_ext`, and `NEEDED` metadata.

On OHOS the recipe signs the build-tree Boost shared libraries and generated
test executables/modules before executing them, and prepends the build-tree
library directory plus the CPython libdir to the runtime environment. Official
CI builds `#32306` and `#32328` confirmed that HNP Python rejects Conan-cache
extension modules with `Permission denied` even after self-signing; the current
recipe therefore records Python live-import tests as E212-limited and keeps
them separate from runtime pass counts.

## Validation status

Local static checks performed in the boost-python worktree:

- Python `ast.parse` passed for `conanfile.py` and `test_package/conanfile.py`.
- YAML parse passed for `manifest.yaml`, `conandata.yml`, and `test_package/MANIFEST.yml`.
- `git diff --check -- archives/b/boost/1.90.0.2.1` passed.

OHOS shadow CI status:

- Run dir: `/storage/Users/currentUser/ohos-test-runs/codex-boost-1.90.0.2.1-pr6712-gnu-ld-r1-20260826-1645`
- Log: `shadow-ci-r14-representative-upstream-tests.log`
- Result: `r14` passed before official HNP CI exposed E212 user-path `dlopen`
  limits, using the old 4-item runner. This result is superseded by the expanded
  357-item upstream component runner and requires a fresh official CI result.
- SONAME spot check: `llvm-readelf -d .../libboost_python312.so` reports
  `Library soname: [libboost_python312.so]`.
- `conan-test-lintl-r2.log` rebuilt only `test_package` against the cached Boost
  package and confirmed the link command uses the absolute
  `libpython3.12.so` path with no bare `-lintl`.
- Official review comment `186766151` failed the PR because the earlier
  description under-reported the upstream test tree and did not record upstream
  execution evidence. Follow-up review comment `186800536` rejected the 4-item
  representative subset as too small. This revision records the upstream
  test-tree scale and adds the expanded component runner above to the recipe
  build phase.

Earlier shadow iterations caught two issues that are fixed in this directory:

- `boost/1.90.0.2` could not be modified because it was already published; this
  package uses the suffix version `1.90.0.2.1`.
- The first `1.90.0.2.1` run built `libboost_python312.so` but test execution
  failed until the Python libdir was added to the OHOS test runtime environment.
- Official CI build `#31668` failed because SDK `lld` could not load
  `libxml2.so.16`; the OHOS recipe and test package now force
  `/data/service/hnp/bin/ld` through CMake linker flags.
- Shadow CI `r10` then exposed missing `DT_SONAME` on the unversioned
  `libboost_*.so` files; `r11` passed after BoostInstall.cmake added
  per-target unversioned SONAME link options.
- Official CI build `#31708` passed the main package build and failed only in
  `test_package` link with `/data/service/hnp/bin/ld: cannot find -lintl`; the
  OHOS smoke test now links the absolute discovered `Python_LIBRARY` instead of
  the full `Python::Python` imported target.
- Official CI builds `#32306` and `#32328` failed only when HNP Python tried to
  import a self-signed user-path `dict_ext.so`; the recipe now uses the existing
  E212 guidance and verifies the Boost.Python upstream module by ELF metadata in
  that environment.
