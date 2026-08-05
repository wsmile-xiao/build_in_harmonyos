# alglib 4.7.0 Adaptation Notes

## Scope

This package adapts the ALGLIB C++ GPL source archive for the task-board
version `4.7.0`. The upstream archive and headers use the generated source
version string `4.07.0`.

The package ships a C++ library and public headers. No command-line tool is
installed, so no software-level `commands.json` is required.

## Build Strategy

Upstream provides `src/*.cpp`, `src/*.h` and test programs, but no CMake,
Autotools or Makefile build system. The Conan recipe generates a small CMake
project during `generate()` and builds:

- `alglib` library from all `src/*.cpp` files
- four normal upstream test executables linked to `alglib`
- one separate `test_xne` executable built from a no-exceptions object library

Common compile definitions:

- `AE_OS=AE_POSIX`
- `AE_THREADING=AE_SERIAL`
- `AE_CPU=AE_AARCH64` on OHOS armv8
- `ALGLIB_NO_FAST_KERNELS`

`AE_THREADING=AE_SERIAL` and `ALGLIB_NO_FAST_KERNELS` keep the baseline portable
on OHOS and avoid x86-only SIMD/threading assumptions during the first
adaptation pass.

The upstream no-exceptions mode rejects any concrete OS definition and requires
thread-unsafe serial mode. The generated `test_xne` target therefore uses a
separate object build with:

- `AE_OS=AE_UNKNOWN`
- `AE_THREADING=AE_SERIAL_UNSAFE`
- `AE_NO_EXCEPTIONS`

## Upstream Tests

The release source contains five upstream C++ test programs:

- `tests/test_i.cpp`
- `tests/test_c.cpp`
- `tests/test_x.cpp`
- `tests/test_xne.cpp`
- `tests/test_xpart0.cpp`

The generated CMake project registers these as five CTest entries. They have
been executed on the new OHOS runner. The truthful upstream result is
`5/5 passed, 0 failed`; total CTest runtime was `198.83 sec`.

Runner details:

- Run directory:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-4.7.0-alglib-4.7.0-newport-r2-conan-20260805-141341-22685`
- Full package reference:
  `alglib/4.7.0#3fb72088498242ddd5112e411b18e489:21b17f8b2bc0e9511e276e3d57a23893067cefe5#ad298ae99ca3681c1a5dde07bea5f067`

`tests/test_c.cpp` is large and should be treated as a heavier C++ compile/test
target on the runner.

## Consumer Test

`test_package` builds a small C++ consumer that links `alglib::alglib` and
validates:

- `spdmatrixcholesky()` on a 2x2 positive definite matrix
- `spline1dbuildlinear()` plus `spline1dcalc()` on a small interpolation sample

## Verification Status

- Source URL probe: official ALGLIB tarball downloaded with browser-like
  `User-Agent`; recipe uses Conan `download()` with pinned sha256 to avoid
  Python `urllib` CA-store failures on the new OHOS machine.
- Source sha256:
  `cb89a553ee202b0a941605072a857102376ae44b0ccd225e4fa0e0e0b9708bf0`.
- OHOS build/test: passed on the new runner.
- Upstream CTest: `test_i`, `test_c`, `test_x`, `test_xpart0`, and `test_xne`
  all passed.
- `test_package`: passed; output included `alglib consumer API validation OK`.
- CI gates: L0 pass, L1 pass, L2 skipped because no `bin/` directory, L4 pass,
  L5 pass.
