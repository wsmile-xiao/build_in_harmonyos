# libxslt 1.1.45.2 debugger compatibility notes

## Build environment

- Build system: CMake
- Evaluation date: 2026-08-17
- Compiler: `/storage/Users/currentUser/usr/local/bin/clang`
- Target: `aarch64-unknown-linux-ohos`
- Sysroot: `/storage/Users/currentUser/usr/local/sysroot`
- Current status: debugger-enabled Conan package and repository build/test verification passed

## Adaptation rationale

`libslax 3.1.6` requires the libxslt debugger APIs `xsltSetDebuggerStatus`, `xsltSetDebuggerCallbacks`, and `xslHandleDebugger`. The repository-published libxslt packages were built with debugger support disabled, so those symbols are absent.

Upstream libxslt 1.1.45 provides `LIBXSLT_WITH_DEBUGGER`, which is OFF by default. Enabling this upstream option is sufficient to provide the required debugger implementation on HarmonyOS.

## Recipe changes

- Keep `BUILD_SHARED_LIBS=OFF` by default.
- Keep `LIBXSLT_WITH_PROGRAMS=ON` so `xsltproc` remains available.
- Enable `LIBXSLT_WITH_DEBUGGER=ON`.
- Keep `LIBXSLT_WITH_CRYPTO=OFF`.
- Keep `LIBXSLT_WITH_PYTHON=OFF`.
- Keep `LIBXSLT_WITH_TESTS=OFF` in the Conan package build.
- Prefer an available OHOS CMake toolchain when present.
- When no `ohos.toolchain.cmake` is available, use the real OHOS compiler from Conan `tools.build:compiler_executables` instead of bypassing platform detection.
- Preserve the existing OHOS ELF signing behavior for packaged executables and shared libraries.

## Verification completed

- Official source SHA256 matched `023900618fbf789dba364f38f184a0fe2d3ebad2b2ab06003ffd2d1ee2d5461c`.
- Native HarmonyOS CMake configure with `LIBXSLT_WITH_DEBUGGER=ON` returned `CMAKE_RC=0`.
- Native HarmonyOS build returned `BUILD_RC=0`.
- Generated `libxslt.a` contains real definitions for all three required debugger symbols.
- Generated `xsltconfig.h` enables `WITH_DEBUGGER`.
- Recipe Python syntax check and Conan inspect passed.

## Verification completed in repository pipeline

- `conan create` for `libxslt/1.1.45.2` completed successfully.
- Consumer `test_package` executed successfully and printed `libxslt debugger probe ok: 10145`.
- Packaged `libxslt.a` contains `xsltSetDebuggerStatus`, `xsltSetDebuggerCallbacks`, and `xslHandleDebugger`.
- Packaged `xsltconfig.h` enables `WITH_DEBUGGER`.
- `xsltproc` transformation test executed successfully from `test_package`.
- Repository `build_and_test.sh` completed with `Success: 1`, `Failed: 0`, and 100% pass rate.
- L0, L1, L2, L4, and L5 quality gates passed.
