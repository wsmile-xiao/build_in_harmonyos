# Conan test_package host executable suffix must be explicit

## Symptom or adaptation scenario

A CMake-based Conan `test_package` compiles and links its consumer, then the
`test()` method reports that the executable is missing on Windows. The build
directory contains the generated program, but the recipe searched for a
suffix-less name.

## Root cause

Conan binds the consumer output directory, while the executable spelling is
host-platform specific. A Windows linker emits `test_eigen.exe`; an OHOS ELF
target is normally suffix-less. Treating the two host environments as one name
causes a false L0 runtime failure after a valid compile and link.

## Repair steps

1. Derive the executable name from Conan's host OS (`.exe` for Windows and no
   suffix for the OHOS device path).
2. Join that name to the bound `cpp.build.bindirs[0]` and require a regular
   file before running it.
3. Keep an explicit `self.run(binary, env="conanrun")` when `can_run(self)` is
   true. For cross builds, skip host execution under `can_run(self)` and keep
   target execution as a separate W3 gate.

## Verification

Eigen 5.0.1 first reproduced the missing `test_eigen` error in
`evidence/conan-create.log`. After selecting `test_eigen.exe` for the Windows
host, the same private Conan cache completed with `CONAN_CREATE_RERUN_RC=0` and
the consumer output `eigen smoke test: PASS (matmul + norm OK)` in
`evidence/conan-create-rerun.log`. The suffix-less branch remains reserved for
OHOS ELF execution.

## Reusable scope and safety boundary

This applies to Conan consumers whose build and target platforms use different
executable naming conventions. It fixes only output discovery and explicit
consumer invocation; it does not establish loader, signing, device runtime,
upstream test, or W3 success. The derived path must stay inside the task-owned
build directory, and target execution must retain its own endpoint and
same-snapshot evidence.
