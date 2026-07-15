# wasmedge 0.17.1 OpenHarmony PC adaptation notes

## Summary

WasmEdge 0.17.1 is adapted as a CMake package with LLVM/AOT, plugins, examples, and tests disabled. This keeps the base runtime and command-line tool portable for OpenHarmony PC cross-build CI.

## Build and test

- Build system: CMake
- Source: `https://github.com/WasmEdge/WasmEdge/archive/refs/tags/0.17.1.tar.gz`
- SHA256: `b2da5bc43a6e11305ddffc7afa1d67c647fd49e34d334fc810ff63783fb52a25`
- Disabled options: LLVM/AOT, plugins, examples, tests, tools, LTO
- Warning policy: suppress GCC 13 false-positive maybe-uninitialized and array-bounds Werror diagnostics
- Smoke test: checks packaged public C API headers and library directory.
