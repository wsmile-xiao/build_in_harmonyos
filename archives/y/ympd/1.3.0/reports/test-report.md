# Test Report — ympd 1.3.0

## Build Status

- **Platform**: HarmonyOS 6.0 PC, AArch64
- **Compiler**: Clang 15.0.4
- **Build System**: CMake 4.1.2, Conan 2.29.1
- **Build Status**: success
- **Source**: official v1.3.0 archive; SHA-256 verified as `D9F68920CD93D1CFA971E1D7B9162A2B1724909BC9753C1338CECB3688D234D5`

## Upstream Test Inventory (R51)

- The official source archive contains no `tests/`, `test/`, or `test_package/` directory and no standalone test source files.
- CMake registers no tests; `ctest -N` reports `Total Tests: 0`.
- **Upstream test pass rate**: N/A (0 upstream tests).

## Adapted Test Results

| Test suite | Result | Details |
|---|---:|---|
| Conan `test_package` | 5/5 passed | Exact `-v` version, server startup, loopback HTTP request, HTTP 200, embedded page content |
| HarmonyOS-specific check | 1/1 passed | `readelf` confirms ELF64 and AArch64; the script also reruns the five consumer assertions above |
| Package CI | 1/1 package built | L0, L1, L4, and L5 passed; L2 skipped because direct CI launch omits Conan runenv and cannot resolve `libmpdclient.so.2` |
| Local repository suite | 10/12 suites passed | Two environment failures also reproduce on `upstream/main`: worker Git executable unavailable and `knowledge/recipes/catalog.tsv` absent |
| Knowledge graph validation | Passed | 541 `.kv` files, 541 Markdown files, 541 index rows; 169 existing corpus warnings |

## Test Execution Notes

- The device cannot access GitHub. Conan build and package CI used a local copy of the official archive after verifying the SHA-256 above; only the temporary validation recipe's source acquisition method was changed. The packaged recipe retains the official URL and hash.
- With Conan `runenv` loaded, the installed binary and HTTP smoke test pass. The package CI L2 result is a non-blocking skip for the unconfigured loader environment.
- The package CI snapshot omitted `knowledge/graph/`; its graph gate reported `no_graph`. The graph validation listed above ran locally against the repository.
