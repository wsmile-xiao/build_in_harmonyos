# Relacy 0.0-git20191025.acc09bb

**Build system:** upstream Makefile; Conan installs the header-only API.  
**Source commit:** `acc09bbe65a1837a08912774c7fed178547514e6` (2019-10-24 UTC)  
**Source URL:** https://codeload.github.com/dvyukov/relacy/tar.gz/acc09bbe65a1837a08912774c7fed178547514e6  
**SHA256:** `f8e54e14e5c89287a8052293b34c7bf51bf3445dd7090c27fab98604230677b`

## OHOS adaptation

- The upstream POSIX fiber backend calls `getcontext`, `makecontext`, and `swapcontext`; the OHOS SDK header declares none of these APIs and its libc does not export them.
- Patch `0001-relacy-platform.patch` provides cooperative fiber handoff with pthread condition variables. The Conan package propagates `RELACY_USE_PTHREAD_FIBERS`, preserving Relacy's single-logical-thread-at-a-time scheduler without changing its public API.
- The two-logical-thread consumer smoke probe passed on the HarmonyOS device; full upstream and Conan consumer tests are recorded below.

## Discoveries and findings

- 鉁?The OHOS SDK omits the POSIX `ucontext` fiber APIs used by this upstream revision.
- 鉁?Cooperative handoff through pthread mutexes and condition variables preserves one-logical-thread-at-a-time Relacy scheduling.

## Package contents and tests

- Header-only `relacy/` API installed under `include/relacy`; the upstream BSD-3-Clause license is included.
- Upstream `make check` passed all 4 model-check suites: 3 suites from `test/ntest/ntest.cpp` and the `cli_ws_deque` example. The suites completed on device.
- Conan consumer test passed both `RL_ASSERT` checks while simulating 1,000 schedules (2/2).
- Conan 2.29.1 create, package, and test-package validation passed.
- G0 configure check is not applicable: this upstream snapshot has no `configure` script; the Conan build runs the upstream Makefile `check` target instead.

- Consumer test includes the packaged `relacy/relacy.hpp` header, schedules two logical threads with separate `rl::var` state, and verifies both results (2 checks).
---

**缂栬瘧缁撴潫**: 2026-09-29 02:25
**鏈€缁堢姸鎬?*: built
