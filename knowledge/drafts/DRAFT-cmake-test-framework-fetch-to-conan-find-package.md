# DRAFT - Feed the upstream CMake test framework in as a packaged dependency

> Status: DRAFT | Source: optional 1.1.0 PR #7324 (`archives/o/optional/1.1.0/`), tl-expected 1.3.1 PR #7289 (merged)

## Problem shape

Header-only C++ libraries in this repository are expected to run their **real
upstream test suite**, not only a `test_package`. Many of those upstreams wire
their test framework through `FetchContent`, inside the same option branch that
enables the suite:

```cmake
# optional 1.1.0 upstream CMakeLists.txt (before patch)
set(CATCH_BUILD_TESTING OFF)
set(CATCH_INSTALL_DOCS OFF)
FetchContent_Declare(Catch2 URL
  https://github.com/catchorg/Catch2/archive/v2.9.2.zip)
FetchContent_MakeAvailable(Catch2)
```

Enabling `OPTIONAL_BUILD_TESTS`/`BUILD_TESTING` therefore makes *configure*
reach an external code host. The repository already publishes the framework as
a Conan package, so the input should come from there instead.

## What was actually observed

Be precise about the evidence, because the naive framing is wrong.

- **Not observed:** a CI failure caused by the GitHub download itself. The
  `FetchContent` removal is a **preventive** change justified by the reproducibility
  argument above, not by a captured red pipeline log. Do not cite it as one.
- **Observed and re-reproduced on 2026-09-01** on HarmonyOS PC aarch64
  (CMake + `/data/service/hnp/bin/clang++` 15.0.4): after replacing the fetch
  with `find_package(Catch2 REQUIRED)` but **before** adding `CMakeDeps`,
  configure aborts:

```text
CMake Error at CMakeLists.txt:3 (find_package):
  By not providing "FindCatch2.cmake" in CMAKE_MODULE_PATH this project has
  asked CMake to find a package configuration file provided by "Catch2", but
  CMake did not find one.

  Could not find a package configuration file provided by "Catch2" with any
  of the following names:

    Catch2Config.cmake
```

The load-bearing half of the fix is therefore the generator call, not the patch.
A recipe that ships the patch without `CMakeDeps` is strictly worse than the
unpatched upstream, because it removes the only mechanism that could locate the
framework.

## Recommended repair

Three steps that only work together:

1. **Patch only the fetch lines** into `find_package`, through the recipe patch
   pipeline so the change is reviewable and re-appliable
   (`python3 scripts/ohc-run.py refresh-patch <name> <version> --auto`). No test
   logic changes:

```cmake
+ find_package(Catch2 REQUIRED)
```

2. **Require the packaged framework, gated on the upstream-test option**, so the
   shipped package keeps zero dependencies:

```python
def requirements(self):
    if self.options.run_upstream_tests:
        self.requires("catch2/2.13.10-r0")
```

3. **Generate the CMake config package** before the toolchain:

```python
def generate(self):
    CMakeDeps(self).generate()
    tc = CMakeToolchain(self)
    ...
```

Keep `package_id()` clearing and the `run_upstream_tests` default as they are;
for a `header-library` the test requirement must not leak into the consumer
graph.

## Full-suite fallback

If the framework is not published in the package repository, do not fall back to
`BUILD_TESTING=OFF`. Keep the upstream CMake logic verbatim and redirect the
fetch to an approved, checksum-verified local source tree:

```bash
cmake -DFETCHCONTENT_SOURCE_DIR_CATCH2=<approved-local-catch2-source> <source>
ctest --output-on-failure
```

Record where that tree came from, since the reproducibility claim now rests on it.

## Related knowledge, not new entries

- **E300** covers a Conan dependency whose *custom* `Find<Foo>.cmake` ignores
  Conan-generated targets and needs cache-variable bridging. Here there is no
  Find module at all; the gap is that Conan emits no config package without
  `CMakeDeps`.
- **E321 draft** (`E321-draft-ASP1-proj-test-bootstrap-offline`) covers the same
  configure-time download shape but recommends `BUILD_TESTING=OFF` plus a real
  consumer test. That is the right call when the framework is unavailable; this
  draft is the preferred branch when the repository already publishes it, since
  it preserves the upstream suite instead of replacing it.
- **E292** covers layered migration of large upstream CTest suites; it assumes
  the framework is already resolvable.
- **E298** covers running `test_package` under its generated run environment,
  which is a different execution path from building the upstream suite in `build()`.

## Prohibited variants

- Do not report `BUILD_TESTING=OFF` as an upstream test pass in order to dodge
  the fetch.
- Do not ship the `find_package` patch without `CMakeDeps(self).generate()`.
- Do not `sed -i` the upstream `CMakeLists.txt` in `source()`; only
  `patches/` + `conandata.yml` are reproducible.
- Do not describe the FetchContent removal as a fix for an observed CI failure.
- Do not add `tool_requires` for a build tool to work around the missing config;
  CI rule L0i/R36 rejects `tool_requires("cmake/...")`-style additions in recipes.

## Evidence

| 包 | PR | 状态 | 说明 |
|---|---|---|---|
| tl-expected 1.3.1 | #7289 | merged 2026-09-01 | 首个实例：Catch2 v2.9.2 fetch → `catch2/2.13.10-r0` + `find_package` |
| optional 1.1.0 | #7324 | open | 复用同一打法；`notes.md` 问题表记录了缺 `CMakeDeps` 时的 configure 失败 |
