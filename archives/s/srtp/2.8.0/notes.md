# srtp 2.8.0 adaptation notes

## Source selection

The points-platform entry is the Homebrew formula named `srtp`. Homebrew maps
that formula to Cisco libSRTP 2.8.0. The recipe therefore keeps the competition
name `srtp` while linking the upstream library artifact `srtp2`.

## Build strategy

The upstream project supports Autotools, CMake, and Meson. This adaptation uses
CMake because it detects platform headers and functions directly and does not
need a forged GNU build triplet or runtime edits to generated `configure`
files. The package is static to avoid versioned shared-library symlink handling
on HMDFS.

The upstream CMake build enables its internal crypto implementation by default.
`ENABLE_OPENSSL=OFF` preserves that self-contained path and avoids depending on
an OpenSSL package that is not required for core SRTP functionality.

## Tests

`LIBSRTP_TEST_APPS=ON` registers 12 upstream CTest cases. The Conan `build()`
method runs them with output-on-failure before installation. The consumer test
then initializes libSRTP, configures default RTP/RTCP policies, creates and
deallocates a real SRTP session, and shuts the library down.

## Validation commands

```bash
conan create archives/s/srtp/2.8.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```
