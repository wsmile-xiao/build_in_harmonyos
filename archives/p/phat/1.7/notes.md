# PHAT 1.7 HarmonyOS adaptation notes

## Source and scope

- Official source: `https://bitbucket.org/phat-code/phat/get/v1.7.tar.gz`
- SHA256: `0b03a652ca9855eab3bda980a735588fed7c947f43cdf06a1ea8212ca7b8c271`
- Official tag: `v1.7`, commit `a74705e4628e447084d47dbf13a16dfb6d2ebd9a`
- Task scope: the C++ header library and its `phat` command-line utility. The top-level `setup.py` is an optional pybind11 wrapper and is not the primary C++ deliverable.

## Dependencies and build

The C++ library has no third-party dependency. OpenMP is optional upstream; HarmonyOS uses the upstream sequential fallback, which implements the required timing and thread-count helpers without `libomp`.

The recipe compiles the utility and official self-test directly with the compiler selected by Conan. This avoids changing the old upstream CMake file, which has no install rules.

## Upstream test census

| Evidence | Count | Result |
|----------|------:|--------|
| `src/self_test.cpp` standalone C++ test entry | 1 | 1/1 passed |
| `tests/` or `test/` directories | 0 | none present |
| CTest registrations (`add_test`, `enable_testing`) | 0 | none present |

The official test is unmodified and runs against `examples/torus.bin`. It compares eight representations, eight reduction algorithms, primal/dual results, the vector interface, and the unordered-map representation.

## Added tests

- Generic consumer test: constructs a triangle boundary matrix and validates matrix metadata and exact persistence pairs through installed headers.
- CLI integration test: runs the packaged `phat` executable on an ASCII matrix and validates the exact output pairs.
- HarmonyOS-specific test: requires `__OHOS__` and AArch64 at compile time, then compares standard, twist, and chunk reductions using installed headers.

## Validation

All declared upstream and added tests pass. The package requires no source patch and introduces no implicit system dependency.
