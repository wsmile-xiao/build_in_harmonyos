# Test Report — bdw-gc 8.2.6

## Build Environment
- Platform: HarmonyOS (OHOS) aarch64
- Compiler: clang 15.0.4
- Build system: autotools
- Date: 2026-08-05

## Test Results

### Upstream Tests (make check)
All 16 tests passed:

| # | Test | Result |
|---|------|--------|
| 1 | cordtest | PASS |
| 2 | gctest | PASS |
| 3 | leaktest | PASS |
| 4 | middletest | PASS |
| 5 | smashtest | PASS |
| 6 | hugetest | PASS |
| 7 | realloc_test | PASS |
| 8 | staticrootstest | PASS |
| 9 | test_atomic_ops | PASS |
| 10 | threadleaktest | PASS |
| 11 | threadkey_test | PASS |
| 12 | subthreadcreate_test | PASS |
| 13 | initsecondarythread_test | PASS |
| 14 | disclaim_test | PASS |
| 15 | disclaim_bench | PASS |
| 16 | disclaim_weakmap_test | PASS |

Total: 16/16 PASS, 0 FAIL, 0 SKIP

### Conan test_package
Consumer smoke test (GC_INIT, GC_MALLOC, GC_gcollect) passed.

## Adaptations
- E011: umask 077 → 022 (HMDFS permission fix)
- CANCEL_SAFE disabled on __OHOS__ (pthread_setcancelstate not available)
- GC_HAVE_PTHREAD_EXIT disabled on __OHOS__ (pthread_cancel not available)

