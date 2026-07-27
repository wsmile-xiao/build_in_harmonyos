# wasmedge 0.17.1 OpenHarmony PC adaptation notes

## Summary

WasmEdge 0.17.1 is adapted as a static CMake package with LLVM/AOT, plugins, examples, and tools disabled. This keeps the base runtime portable for OpenHarmony PC cross-build CI while preserving the public C API and VM execution path.

## Build and test

- Build system: CMake
- Source: `https://github.com/WasmEdge/WasmEdge/archive/refs/tags/0.17.1.tar.gz`
- SHA256: `b2da5bc43a6e11305ddffc7afa1d67c647fd49e34d334fc810ff63783fb52a25`
- Disabled options: LLVM/AOT, plugins, examples, upstream tests, tools, LTO, shared library build
- Packaging: static aggregate library is exposed as `wasmedge::wasmedge` so downstream consumers link a closed runtime library set directly.
- Smoke test: checks version APIs, configuration creation, VM lifecycle, and executes a minimal in-memory wasm add function through the packaged C API.

## Upstream test decision

The upstream `test/` tree contains API, common, executor, loader, validator, component, host/WASI, and AOT/plugin-oriented tests. The complete CTest suite is not enabled in this base recipe because it depends on the full WasmEdge feature set, including LLVM/AOT, plugins, tools, host/WASI runtime services, and test fixtures not packaged in the reduced OpenHarmony PC adaptation.

To cover the portable upstream foundation without pulling in those disabled features, `test_package/test_wasmedge.c` validates the same basic API/VM contract expected by upstream API tests: public version functions, configure context creation, VM creation/deletion, and `WasmEdge_VMRunWasmFromBuffer` execution of a minimal wasm module.
