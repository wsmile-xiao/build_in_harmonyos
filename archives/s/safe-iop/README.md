# safe-iop

safe-iop is a public-domain C library for detecting overflow and other invalid integer arithmetic before storing a result.

## Features

- Checked addition, subtraction, multiplication, division, and modulo macros.
- Signed and unsigned integer support from 8 to 64 bits, including `size_t` and `ssize_t`.
- Sequential three-, four-, and five-operand helpers.
- A linked `safe_iopf` format-string interface for 32-bit operations.

## OHOS adaptation

- The upstream source builds unchanged with HarmonyOS Clang 15 on armv8.
- The Conan recipe produces a shared library by default and also supports a static build.
- The complete upstream `make test` suite is executed during `conan create`.
- A dedicated consumer test verifies the native `__OHOS__`/AArch64 LP64 ABI and boundary overflow behaviour.

## Dependencies

- Build dependency: a C compiler and an archiver.
- Runtime dependency: the C runtime only.
- Third-party dependencies: none.

## References

- Upstream archive: https://code.google.com/archive/p/safe-iop/
- Official source: https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/safe-iop/safe-iop-0.3.1.tgz
