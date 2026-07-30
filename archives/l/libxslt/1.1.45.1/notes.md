# libxslt 1.1.45.1 xsltproc adaptation notes

## Build environment

- Build system: CMake
- Evaluation date: 2026-07-28
- Compiler: `/storage/Users/currentUser/usr/local/bin/clang-15`
- Target: OHOS aarch64, sysroot `/storage/Users/currentUser/usr/local/sysroot`
- Status: built and tested on the real OHOS runner

## Adaptation rationale

Morpheus 2.4.1 uses `xsltproc` during its build:

```cmake
FIND_PROGRAM(XSLTPROC "xsltproc" ...)
IF( NOT XSLTPROC )
    message(FATAL_ERROR "Unable to locate 'xsltproc' executable")
ENDIF()
```

The existing `libxslt/1.1.45` recipe sets `LIBXSLT_WITH_PROGRAMS=OFF`, so it
does not provide the build-time `xsltproc` tool Morpheus needs. This `1.1.45.1`
revision enables `xsltproc` while keeping EXSLT crypto disabled because the
Morpheus rule generation path does not require `libgcrypt`.

## Recipe details

- `BUILD_SHARED_LIBS=OFF` by default. This avoids HMDFS permission failures when
  CMake install creates versioned shared-library symlinks, while still producing
  the required `xsltproc` executable and static libxslt/libexslt libraries.
- `LIBXSLT_WITH_PROGRAMS=ON`: installs `xsltproc`.
- `LIBXSLT_WITH_CRYPTO=OFF`: avoids a new `libgcrypt` dependency.
- `LIBXSLT_WITH_PYTHON=OFF` and `LIBXSLT_WITH_TESTS=OFF` in the Conan package
  build. Release-source upstream tests are run separately.
- `package_info()` exposes `bin/` through build and run environments so build
  consumers can find `xsltproc`.
- On OHOS, `package()` signs package ELF files under `bin/` and `lib/*.so*`.
  The signer/objcopy paths are resolved from the compiler directory, PATH, or
  explicit `BINARY_SIGN_TOOL` / `LLVM_OBJCOPY` environment variables. This is
  required because the active real-device environment provides signing tools in
  `$HOME/usr/local/bin`, not `/data/service/hnp/bin`.

## Verification

- Local static checks:
  - `python -m py_compile archives/l/libxslt/1.1.45.1/conanfile.py archives/l/libxslt/1.1.45.1/test_package/conanfile.py`
  - `git diff --check`
- OHOS Conan/test_package:
  - run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-libxslt-libxslt-1.1.45.1-20260727-r2-conan-r8-sign-bin-20260727-235301-12939`
  - result: `L0=pass`, `L1=pass`, `L2=skip` for `xslt-config/xsltproc --version/--help`, `L4=pass`, `L5=pass`, build summary `Total=1 / Success=1 / Failed=0`
  - consumer coverage: `test_probe` compiles, links, and runs against libxslt;
    `xsltproc test.xsl test.xml` produces `morpheus-xslt-ok`
- Release-source upstream tests:
  - run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-libxslt-libxslt-1.1.45.1-20260727-r2-upstream-r1-ctest-20260728-001300-24657`
  - command shape: configure release source with `LIBXSLT_WITH_TESTS=ON`, build
    `runtest`, `testThreads`, and `xsltproc`, sign generated executables, then
    run `ctest -N` and `ctest -VV`
  - result: CTest `2/2` passed
  - `runtest`: upstream output `Total 748 tests, no errors`
  - `testThreads`: passed
