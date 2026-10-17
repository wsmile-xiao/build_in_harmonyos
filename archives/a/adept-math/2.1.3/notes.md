# adept-math 2.1.3 Adaptation Notes

## Source

- Upstream homepage: https://www.met.reading.ac.uk/clouds/adept/
- Upstream repository: https://github.com/rjhogan/Adept-2
- Source archive: https://github.com/rjhogan/Adept-2/archive/refs/tags/v2.1.3.tar.gz
- SHA256: `7a982e537db456df90a32d81b95d40cb69448fb41f78ca0f678f51e35d68118b`

The upstream download page lists formal release tarballs only up to 2.1.1.
The task version 2.1.3 is available from the official GitHub tag `v2.1.3`.
That tag is a GitHub source snapshot and does not contain generated Autotools
files such as `configure`.

## Build Strategy

The recipe uses a custom static build instead of running `autoreconf`.
Reason: `autoconf/2.72` and `m4/1.4.19` did not download cleanly from the
ohpcd Conan remote during W0 checks, while the Adept library itself has no
required runtime dependencies.

The build compiles the upstream `adept/*.cpp` files into `libadept.a`, writes a
minimal `config.h` and `config_platform_independent.h`, and generates
`include/adept_source.h` from the upstream source list for the `test_no_lib`
upstream test.

Optional BLAS/LAPACK acceleration is disabled. This follows the upstream
configuration summary behavior when no Fortran/BLAS/LAPACK stack is available:
core automatic differentiation remains enabled, while matrix multiplication and
LAPACK-backed routines throw Adept's `feature_not_available` exceptions.

## Upstream Tests

Upstream test entry: `test/Makefile` target `check`.

The upstream `PROGRAMS` list contains 25 test program names:

1. `test_adept`
2. `test_adept_with_and_without_ad`
3. `test_radiances`
4. `test_gsl_interface`
5. `test_misc`
6. `test_checkpoint`
7. `test_thread_safe`
8. `test_array_speed`
9. `test_no_lib`
10. `test_radiances_array`
11. `test_constructors`
12. `test_arrays`
13. `test_arrays_active`
14. `test_arrays_active_pausable`
15. `test_fixed_arrays`
16. `test_fixed_arrays_active`
17. `test_derivatives`
18. `test_array_derivatives`
19. `test_thread_safe_arrays`
20. `test_complex_arrays`
21. `test_packet_operations`
22. `test_fastexp`
23. `test_reduce_active`
24. `test_minimizer`
25. `test_interp`

The recipe compiles and runs the same program list during `build()`. GSL is
declared as a `test_requires` dependency so `test_gsl_interface` can be included
without propagating GSL to Adept consumers.

`state.cpp` is part of the upstream `test_gsl_interface` object set and directly
includes `<gsl/gsl_multimin.h>`, so the recipe applies the test-only GSL include
flags to both `state.cpp` and `test_gsl_interface.cpp`. GSL remains a
`test_requires` dependency and is not propagated to Adept consumers.

## OHOS New-Port Verification

- Port: `33332`
- Job base: `/storage/Users/currentUser/ohos-users/codex-a/adept-math-2.1.3-newport-r1`
- Runner run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-2.1.3-adept-math-2.1.3-newport-r1-conan-20260805-153331-57055`
- Start/end: `2026-08-05 15:33:31 +0800` to `2026-08-05 15:37:49 +0800`
- Exit code: `0`
- Full package reference: `adept-math/2.1.3#9138052c8763859522443d39602fdbbe:6b129b068851896169fae42d399fa922d239ce8a#ba18a07f3be0be2d77bbf2bef08eb42d`
- Upstream tests: `25/25` programs passed during `build()`.
- Consumer test: `test_package` built and ran the AD gradient smoke, `1/1` passed.
- CI gates: L0 pass, L1 pass, L2 skip (`no bin/ dir` library package), L4 pass, L5 pass.

Local Windows precheck: MinGW `g++` 8.1 compiled the direct static library
source list into `libadept.a` and ran the consumer AD smoke successfully. This
was only an early recipe-logic check; the authoritative result is the OHOS
new-port run above.

## Consumer Test

`test_package` builds a small C++ program that creates an Adept stack, records
`y = x*x + 2*x`, runs reverse-mode automatic differentiation, and asserts the
gradient at `x = 3` is `8`.
