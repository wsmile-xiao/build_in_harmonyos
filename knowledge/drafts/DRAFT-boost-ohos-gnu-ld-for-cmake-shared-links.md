# DRAFT: Boost CMake shared links should use GNU ld on OHOS CI

> Status: Draft | Updated: 2026-08-26
> Source event: `boost/1.90.0.2.1` official CI #31668 link failure
> Task hall: `4415`
> PR: https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/6712

## Summary

Boost's CMake release can build several shared libraries in one superproject. On
HarmonyOS PC CI, those links should not depend on the SDK `lld` executable being
able to find its own `libxml2.so.16` runtime dependency through shell startup
environment.

For Boost.Python dependency packages, force GNU ld through CMake linker flags in
both the package recipe and the `test_package` consumer build.

## Symptoms

The failure happens before Boost symbols are resolved. The build reaches
`cmake.build()`, starts linking a Boost shared library, and clang reports that
the SDK `lld` executable cannot start:

```text
Error loading shared library libxml2.so.16: (needed by .../ohos/native/llvm/bin/lld)
Error relocating .../ohos/native/llvm/bin/lld: xmlFreeDoc: symbol not found
clang-15: error: unable to execute command: No such file or directory
```

In `boost/1.90.0.2.1`, official CI #31668 failed while linking Boost shared
libraries during `cmake.build()`, even though earlier shadow CI had passed with a
more helpful shell environment.

## Root Cause

The OHOS SDK `lld` binary is dynamically linked and needs `libxml2.so.16` at
runtime. A developer shell or setup script may make that library visible, but
official CI should be treated as a sanitized environment. If the recipe relies
on ambient `LD_LIBRARY_PATH`, clang can compile sources successfully and then
fail as soon as it asks `lld` to link a shared object.

This is a toolchain executable startup failure, not a Boost source failure and
not a missing dependency of the packaged Boost libraries.

## Adaptation Pattern

For OHOS, make linker selection part of the Conan/CMake recipe:

```python
gnu_ld_flag = "-fuse-ld=/data/service/hnp/bin/ld"
for linker_flag in (
    "CMAKE_EXE_LINKER_FLAGS",
    "CMAKE_SHARED_LINKER_FLAGS",
    "CMAKE_MODULE_LINKER_FLAGS",
):
    tc.variables[linker_flag] = gnu_ld_flag
```

Apply the same pattern in `test_package/conanfile.py`. The package build validates
Boost shared-library links, and the test package validates the downstream CMake
consumer executable link. Both need the same CI-portable linker selection.

## Validation

Use an official-CI-shaped command on the device:

```bash
CI_PACKAGES="archives/b/boost/1.90.0.2.1" \
CI_BRANCH="feat/boost-1.90.0.2.1" \
CI_PR_NUMBER="6712" \
zsh ci/conan/build_and_test.sh
```

The generated build log should show Boost libraries linking without any
`llvm/bin/lld` `libxml2.so.16` loader errors, then proceed into the normal
Boost.Python consumer test.

## Do Not

- Do not rely only on `~/.zshrc` or an interactive `LD_LIBRARY_PATH`.
- Do not copy `libxml2` into the Boost package to satisfy a toolchain executable.
- Do not patch Boost source around XML symbols; the XML symbols belong to the
  linker executable's runtime dependency.
