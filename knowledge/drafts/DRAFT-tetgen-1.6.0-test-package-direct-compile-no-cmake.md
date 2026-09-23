# DRAFT - tetgen test_package direct compile without cmake

> Contributor: codex | Status: DRAFT | Created: 2026-09-21

## Scope

Use this when a Conan package builds on OHOS shadow CI but its CMake-based
`test_package` fails at `CMake.configure()` because `cmake` is not on PATH, and
the consumer test is a small single-file C/C++ program.

## Symptom

Representative failure:

```text
tetgen/1.6.0 (test package): RUN: cmake -G "Unix Makefiles" ...
/system/bin/sh: cmake: inaccessible or not found
ConanException: Error 127 while executing
```

The main package build was already green up to packaging (source download,
compile, ELF signing, upstream smoke test). Only the separate test_package
recipe context failed.

## Root Cause

OHOS shadow-CI runners expose `clang`/`clang++` through the Conan conf
`tools.build:compiler_executables`, but do not put `cmake` on the baseline
PATH. The `CMake` helper in `test_package/conanfile.py` invokes a bare `cmake`
command, so it fails with Error 127.

## Recommended Solution

Compile the consumer test directly, without the `CMake` helper:

1. Read `tools.build:compiler_executables` as a single dict and index `"cpp"`
   (fall back to `/data/service/hnp/bin/clang++`). Do **not** use the
   `tools.build:compiler_executables:cpp` subkey form — conan 2.30 rejects it.
2. Compile the consumer source against the tested package's
   `cpp_info.includedirs` / `cpp_info.libdirs`:
   `clang++ -std=c++11 -I<inc> test.cpp -L<lib> -ltet -lm -o test`
3. Sign the ELF with `binary-sign-tool -selfSign 1` so OHOS will execute it.
4. Run it through `bash` (`CONFIG_SHELL` fallback `/data/service/hnp/bin/bash`)
   because OHOS `/system/bin/sh` (mksh) cannot exec ELF binaries directly.

## Verification

After switching `test_package` to direct compile, tetgen/1.6.0 passed
single-package shadow CI:

```text
exit-code.txt=0
test_package output: TetGen consumer test passed: 4 points, 1 tetrahedra
L0_RESULT=pass  L1_RESULT=pass  L2_RESULT=pass  L4_RESULT=pass  L5_RESULT=pass
Build Summary: Total 1, Success 1, Failed 0
```

## Forbidden Shortcuts

- Do not skip `test_package` just because cmake is missing from PATH.
- Do not modify shared CI scripts (`ci/conan/build_and_test.sh`) to add cmake.
- Do not assume the main package recipe's environment is inherited by the
  test_package context.

## Relation To Existing Knowledge

E307 covers "test_package cmake not found" (compile-only fallback). E339 covers
the "add a generate() that prepends the tool dir to PATH" closure. This draft
records a third, simpler option: **drop the CMake helper entirely and compile
the consumer directly** — suitable when the consumer test is a single file and
does not need CMake-generated configuration.
