# E339 - OHOS Test Package CMake PATH Closure

> Contributor: codex | Status: DRAFT | Created: 2026-08-25

## Scope

Use this pattern when a Conan package builds on OHOS but its CMake-based
`test_package` fails before compiling the consumer test because `cmake` is not
visible in PATH.

The draft comes from `libunwind/1.6.2`, where the package recipe's Autotools
environment was already fixed and the library packaged correctly, but the
consumer test failed at `CMake.configure()`.

## Symptom

Representative failure:

```text
libunwind/1.6.2 (test package): RUN: cmake ...
/system/bin/sh: cmake: inaccessible or not found
ConanException: Error 127 while executing
```

The main package build can still be green up to packaging. The problem is
specifically in the separate test package recipe context.

## Root Cause

Conan 2 runs `test_package` with its own generators and environment scripts.
Environment setup performed in the main package recipe does not guarantee that
`CMake.configure()` in `test_package/conanfile.py` can find OHOS-native tools.

On the observed shadow CI device, clang, cmake, make, and related tools were
available under `/data/service/hnp/bin`, but the runner's baseline PATH did not
make `cmake` visible to the test package shell.

## Recommended Solution

Add an OHOS-specific `generate()` method to the test package:

1. Read `tools.build:compiler_executables` from Conan conf.
2. Derive `tool_dir` from the configured C compiler path.
3. Fall back to `/data/service/hnp/bin` if no compiler directory was provided.
4. Use `Environment().prepend_path("PATH", tool_dir)`.
5. Save the environment script before `CMake.configure()` runs.

This keeps the fix with the consumer validation code and avoids changing shared
CI runner state.

## Verification

After adding the test-package-local PATH closure, `libunwind/1.6.2` passed
single-package shadow CI:

```text
run_id=codex-libunwind-libunwind-1.6.2-shadow-20260825-192940-conan-watch-r4-20260825-221014-20260825-221637-7273
exit-code.txt=0
test_package output: libunwind walked 3 frame(s)
Build Summary: Success 1, Failed 0
```

## Forbidden Shortcuts

- Do not skip `test_package` just because CMake is missing from PATH.
- Do not assume the main package recipe's generated build environment is
  inherited by the test package.
- Do not patch shared CI scripts for one package's consumer validation issue.
- Do not replace `CMake.configure()` with a fake passing command.

## Relation To Existing Knowledge

E338 covers the package recipe's Autotools-side native toolchain closure. This
draft records the separate validation-side closure required for CMake consumer
tests on the same OHOS runner.
