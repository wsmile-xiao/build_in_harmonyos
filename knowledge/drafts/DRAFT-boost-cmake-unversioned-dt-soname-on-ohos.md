# DRAFT: Boost CMake unversioned DT_SONAME on HarmonyOS PC

> Status: Draft | Updated: 2026-08-26
> Source event: `boost/1.90.0.2.1` shadow CI L5 SONAME failure
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

Boost's CMake install helper can be patched to suppress versioned
`libboost_*.so.*` outputs on OHOS, but the resulting unversioned `.so` files
still need ELF `DT_SONAME`. A package may pass `conan create` and its consumer
test while still failing the CI L5 SONAME quality gate.

## Symptoms

The build log shows the package and test package succeeded, followed by L5
messages like:

```text
L5a: libboost_python312.so 缺少 DT_SONAME
L5_RESULT=fail: soname_gate_failed
```

The same pattern can affect every compiled Boost shared library in the package,
including `atomic`, `chrono`, `filesystem`, `program_options`, and
`python312`.

## Root Cause

BoostInstall.cmake normally sets a `VERSION` property for shared-library
targets. That makes CMake add SONAME metadata, but it can also produce versioned
library outputs or install aliases. If an OHOS patch gates that whole block with
`BOOST_INSTALL_NO_VERSIONED_LIBS`, CMake stops emitting SONAME as well.

## Adaptation Pattern

Keep the unversioned install layout, but add a target-scoped link option before
the gated `VERSION` block:

```cmake
if(TYPE STREQUAL "SHARED_LIBRARY" AND BOOST_INSTALL_NO_VERSIONED_LIBS)
  if(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG)
    target_link_options(${LIB} PRIVATE "${CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG}$<TARGET_FILE_NAME:${LIB}>")
  else()
    target_link_options(${LIB} PRIVATE "-Wl,-soname,$<TARGET_FILE_NAME:${LIB}>")
  endif()
endif()
```

`$<TARGET_FILE_NAME:${LIB}>` keeps the SONAME aligned with each actual
unversioned output, for example `libboost_python312.so`.

## Validation

Run the normal OHOS shadow CI and inspect L5:

```sh
CI_PACKAGES="archives/b/boost/1.90.0.2.1" CI_BRANCH="feat/boost-1.90.0.2.1" CI_PR_NUMBER="6712" zsh ci/conan/build_and_test.sh
```

The expected result is `L5_RESULT=pass`. For a direct spot check, inspect a
packaged library with `readelf -d` and confirm the SONAME is the unversioned
library file name.

## Do Not

- Do not treat `conan create` success alone as enough when L5 reports missing
  SONAME metadata.
- Do not re-enable the full Boost `VERSION` behavior without checking whether
  it reintroduces versioned files or symlink-style install entries on OHOS.
- Do not patch generated package files after signing unless a target-level CMake
  fix is unavailable.
