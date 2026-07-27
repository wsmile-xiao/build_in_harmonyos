# ggml 0.17.0 OpenHarmony Conan adaptation

## Scope

- Issue: #628
- Upstream: https://github.com/ggerganov/ggml
- Source commit: `9be313313c8ecb9488911bd64550190e3ed80f38`
- Build system: CMake
- License: MIT
- Conan package: `ggml/0.17.0`

## Recipe decisions

- The source archive is pinned to the upstream commit and verified with SHA-256.
- `GGML_NATIVE=OFF` prevents host-specific instruction-set flags from entering an OHOS package.
- `GGML_ALL_WARNINGS=OFF` avoids compiler-ID-specific warning flags when a Conan profile uses different C and C++ compiler executables.
- Examples and upstream tests are disabled in the package build; the Conan test package performs a public API and CPU graph check.
- OpenMP is exposed as an option and defaults to `False` so the base package has no external runtime dependency.
- The CPU backend is enabled and packaged together with `ggml` and `ggml-base`.

## Verification target

The L1 test creates two `GGML_TYPE_F32` tensors, evaluates `ggml_add` through
`ggml_graph_compute_with_ctx`, and checks all four output values. On a cross
build, Conan still compiles and links the test while deferring execution to the
target device.
