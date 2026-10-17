# RapidJSON 1.1.0 upstream logical test inventory (upstream source v1.1.0)

The upstream correctness suite is a single gtest executable, `unittest`,
built from 25 sources under `test/unittest/`. All registered cases run in
that one executable; CTest wraps it once. The identifiers below are counted
once.

**Static vs runtime count:** the 738 declarations below are a static
grep inventory for review convenience — it includes lines that are
macro-generated, `#if`-guarded out, or not registered as runnable cases.
The authoritative executed-case count is the gtest runtime report of the
`unittest` binary: **343 tests from 29 test suites**. All doc numbers
(MANIFEST.yml, manifest.yaml) use the runtime figure.

## Static TEST/TEST_F/TEST_P declaration inventory per source (total 738)

| Source | Declarations |
|---|---:|
| allocatorstest.cpp | 4 |
| bigintegertest.cpp | 6 |
| documenttest.cpp | 11 |
| dtoatest.cpp | 50 |
| encodedstreamtest.cpp | 4 |
| encodingstest.cpp | 4 |
| filestreamtest.cpp | 2 |
| fwdtest.cpp | 1 |
| istreamwrappertest.cpp | 8 |
| itoatest.cpp | 4 |
| jsoncheckertest.cpp | 1 |
| namespacetest.cpp | 2 |
| ostreamwrappertest.cpp | 7 |
| pointertest.cpp | 36 |
| prettywritertest.cpp | 8 |
| readertest.cpp | 277 |
| regextest.cpp | 77 |
| schematest.cpp | 112 |
| simdtest.cpp | 4 |
| strfunctest.cpp | 1 |
| stringbuffertest.cpp | 9 |
| strtodtest.cpp | 1 |
| valuetest.cpp | 50 |
| writertest.cpp | 59 |
| unittest.cpp | 0 (utilities only) |

The exact executed/passed counts come from the gtest run report produced by
`ctest --test-dir build -R '^unittest$' --output-on-failure`.

## Upstream exclusions (not counted)

- `test/perftest/` — performance benchmark suite (`misctest`, `perftest`,
  `platformtest`, `rapidjsontest`, `schematest`); measures throughput, not
  correctness. It is not built. No correctness case is excluded.
- `valgrind_unittest` — the same `unittest` binary re-run under valgrind
  (memory-check tooling); valgrind is not available on HarmonyOS. The
  underlying cases are already counted in the `unittest` run.
- `symbol_check` — a Debug-build-only developer tool that greps the
  `namespacetest` archive symbol table; not a logical test case, and not
  registered in Release builds.
- `example/` — tutorial programs; not tests. Builds disabled via
  `RAPIDJSON_BUILD_EXAMPLES=OFF`.

## Dependency note

Upstream test CMake resolves gtest through `FindGTestSrc.cmake`, which
searches for gtest *sources* (`thirdparty/gtest`, a git submodule that
release tarballs do not contain, or a system `/usr/src/gtest`). With no
sources found the whole suite silently skips. Patch 0002 replaces that
lookup with `find_package(gtest CONFIG REQUIRED)` against the packaged
`gtest/1.17.0` and adds a local `gtest_main` shim (patch adds
`test/gtestmain.cpp`), so the full suite actually builds and runs.
