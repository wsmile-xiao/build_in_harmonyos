# DRAFT: Boost.Python OHOS Python::Python `-lintl` linkage

> Status: Draft | Updated: 2026-08-26
> Source event: `boost/1.90.0.2.1` official CI #31708
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

Boost.Python smoke tests on OHOS should keep proving the CPython 3.12 runtime
path, but they should not blindly inherit every optional system link item from
CMake's `Python::Python` imported target. In official CI, that target can expose
a bare `-lintl` while the default linker search path does not contain libintl.

## Symptoms

The main Boost package builds, signs, and packages successfully. The failure
appears later while linking the `test_package` executable:

```text
/data/service/hnp/bin/ld: cannot find -lintl: No such file or directory
clang-15: error: linker command failed with exit code 1
```

The configure log shows `Python_EXECUTABLE`, `Python_INCLUDE_DIR`, and
`Python_LIBRARY` were discovered under the official CI CPython 3.12 HNP layout.

## Root Cause

`Python::Python` is a convenient imported target, but its interface can carry
extra system libraries from the Python build configuration. On the official OHOS
CI worker, `-lintl` is exposed without a matching default search directory.

For this Boost dependency package, the test only needs to link the target
CPython shared library that the recipe already discovered and passed as
`Python_LIBRARY`. Pulling the full imported target interface adds avoidable
environment-specific link requirements.

## Adaptation Pattern

Keep `find_package(Python 3.12 COMPONENTS Interpreter Development REQUIRED)` for
headers and artifact validation. For OHOS, link the absolute `Python_LIBRARY`
cache value instead of `Python::Python`:

```cmake
set(_boost_test_python_library Python::Python)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  set(_boost_test_python_library "${Python_LIBRARY}")
  if(NOT _boost_test_python_library AND Python_LIBRARIES)
    list(GET Python_LIBRARIES 0 _boost_test_python_library)
  endif()
endif()
```

Also add the discovered Python include directory explicitly for the target, and
use the absolute library path to derive `BUILD_RPATH` when available.

## Validation

Run the OHOS package CI:

```sh
CI_PACKAGES="archives/b/boost/1.90.0.2.1" CI_BRANCH="feat/boost-1.90.0.2.1" CI_PR_NUMBER="6712" zsh ci/conan/build_and_test.sh
```

The expected link command uses the absolute `libpython3.12.so*` path and does
not include a bare `-lintl` for the smoke executable.

## Do Not

- Do not add gettext/libintl to the Boost package only because the smoke test
  inherited `Python::Python`'s optional interface libraries.
- Do not remove `Python.h`, `Py_Initialize`, or the Boost.Python runtime check;
  downstream packages still need proof that Boost.Python works against CPython
  3.12 on OHOS.
- Do not rely on an interactive shell's library path to fix a test_package link
  command in official CI.
