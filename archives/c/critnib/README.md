# critnib

Lock-free critnib tree (radix/critbit hybrid) with fixed-size uintptr_t keys.
Extracted from Intel PMDK, standalone at https://github.com/kilobyte/critnib.

## OHOS adaptation

- Build system: cmake, 1 portability patch (CMakeLists compat)
- Static by default, respects BUILD_SHARED_LIBS

## Dependencies

- C compiler + pthreads only

## References

- Upstream: https://github.com/kilobyte/critnib
