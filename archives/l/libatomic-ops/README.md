# libatomic-ops

## Introduction
libatomic-ops provides portable atomic memory operation primitives
(fetch-and-add, compare-and-swap, test-and-set, spin pause) plus a
lock-free stack and an atomic malloc built on top of them.

## OHOS adaptation
- CMake build; no dependencies beyond system pthreads.
- Upstream option renames in 7.10.0 honored: `AO_BUILD_SHARED_LIBS`
  and standard `BUILD_TESTING`.
- Upstream ctest suite (5 cases) runs in `build()`; consumer test links
  both `atomic_ops` and `atomic_ops_gpl` and exercises fetch_add, CAS,
  test_and_set, pause, malloc and stack.

## Dependencies
- None (system pthreads only).

## Verification
```bash
ctest --output-on-failure
./test_libatomic_ops
```

## References
- Homepage: https://github.com/bdwgc/libatomic_ops
- Release: https://github.com/bdwgc/libatomic_ops/releases/tag/v7.10.0
