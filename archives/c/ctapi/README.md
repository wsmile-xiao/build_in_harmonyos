# ctapi

ctapi provides the CT-API 1.1 C interface definition for communicating with
ISO/IEC 7816 compatible smart-card terminals.

## Features

- Declares the standard `CT_init`, `CT_data`, and `CT_close` entry points.
- Provides the standard CT-API status codes and terminal addresses.
- Supports both C and C++ consumers through an `extern "C"` guard.

## HarmonyOS adaptation

The upstream project is a single portable header and requires no source
patches. The Conan package installs `ctapi.h` unchanged. Consumer tests verify
the C interface, C++ linkage, and the HarmonyOS aarch64 ABI.

## Dependencies

ctapi has no build-time or runtime dependencies beyond the C standard integer
types supplied by the compiler toolchain.

## References

- [Debian package tracker](https://tracker.debian.org/pkg/ctapi)
- [Authoritative source view](https://sources.debian.org/src/ctapi/1.1%2Bnmu1/)
