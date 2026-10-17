# libschrift 0.10.2 adaptation notes

## Source

The recipe uses the official `v0.10.2` tag from `tomolt/libschrift` and verifies the downloaded archive with SHA-256.

The official archive was downloaded and independently hashed locally: SHA-256 `23e98611f0dfc6e22dcf531f2de987042ca5a81864911b4e917fb3218795fae0`.

## Build

The upstream project is a small C99 library with a Makefile. The recipe provides a CMake wrapper so Conan can build the static library and the upstream `stress.c` executable without external dependencies.

## Tests

The upstream snapshot has no `make test` target. Its bundled `stress.c` is built and run against `resources/Ubuntu-Regular.ttf`, exercising font loading, glyph lookup, glyph metrics, and rendering. The Conan consumer test checks the public version API and rejection of invalid memory and file font inputs.

## HarmonyOS

No source patch is required. The library uses only the C standard library for its core functionality, and the OHOS arm64 Conan profile supplies the compiler and platform settings.
