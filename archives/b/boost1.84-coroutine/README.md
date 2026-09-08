# boost1.84-coroutine

Boost.Coroutine (v1, deprecated successor coroutine2) provides generalized subroutines with cooperative switching. This package is a standalone component split from boost 1.84.0 for HarmonyOS PC (aarch64).

## OHOS adaptation

- Manually compiles Boost.Context fcontext ASM (`make/jump/ontop_arm64_aapcs_elf_gas.S` + `posix/stack_traits.cpp`) into `libboost_context.a` and Boost.Coroutine (`detail/coroutine_context.cpp` + `exceptions.cpp` + `posix/stack_traits.cpp`) into `libboost_coroutine.a` — B2 (Boost.Build) is incompatible with OHOS (E068).
- Installs the full `boost/` header tree so the package is self-contained.
- Upstream tests (2 executables) run via header-only `included/unit_test.hpp` without a compiled boost_test library; both pass on OHOS aarch64.

## Dependencies

None (context/coroutine only need boost headers + libc; musl pthread_setcancelstate shim via `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`).

## References

- https://github.com/boostorg/coroutine (branch boost-1.84.0)
- https://www.boost.org/doc/libs/1_84_0/libs/coroutine/
- https://www.boost.org/doc/libs/1_84_0/libs/context/
