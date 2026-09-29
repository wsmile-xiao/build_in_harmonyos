# MAdLib 1.3.0 HarmonyOS PC verification

Date: 2026-09-29. Claimed task: #8638. Team: 诶，云朵. Candidate path: B, subject to event review.

- Source: Debian's MAdLib mesh-adaptation release tarball, SHA-256 `266c8818b217599ef4a039ddfdccc6a04ee5f327855979d17320c8f152a4b4ad`. This is not Apache MADlib.
- Dependency: published OHOS `lapack/3.12.1` binary, including BLAS and Fortran runtime. No dependency source build was required.
- Target: HarmonyOS PC aarch64, Clang 15. The W3 receipt binds the actual campus-network endpoint and device identity; the IP is not permanent.
- Final run: `madlib-w3-20260929T043214Z`; one launch, frozen bundle SHA-256 `8fedff65a82a4402d366aa1ea84dae460a1d13443e45660bffef1fb099470ac8`, exact transfer and independent byte readback, full input manifest verification.
- `conan create` returned 0. The upstream `make check -j1` target executed but defines no registered test cases: **0/0**. The installed-package C++ consumer compiled, linked, called the public initialize/finalize API, and exited 0: **1/1**.
- Full Conan log SHA-256: `4ca43c65ba0422dbacef04b2f5bc92d864fe7ea0234013ab50efa126a761abe1`. Frozen transaction validator: `W3_VALIDATOR_PASS`, chain head `c6a25d379172dbf58bfddf8e61d614f1103849630c52b7eb4134940afab84fa7`, including runner absence, release, and postrelease.

The recipe minimally patches the release's old `config.sub` OHOS tuple recognition, Autoconf's HMDFS-incompatible temporary directory mask, and the missing `<unistd.h>` declaration of `_SC_PAGE_SIZE`. Earlier unique runs ended at those precise failures and were not relaunched. GNU make still emits a nonfatal HMDFS `jobserver mkfifo: Operation not permitted` warning in the successful run; the exit code and consumer result, not that warning alone, establish success. No CI, merge, registry publication, or score approval is claimed here.
