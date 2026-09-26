# Local adaptation test report — klibc-fstype 2.0.14

- Target: HarmonyOS PC, AArch64 (`ohos-aarch64` profile)
- Isolated Conan home: `/storage/Users/currentUser/work/psj/ch-klibc-fstype`
- Command: `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
- Result: `CREATE_EXIT:0`
- Upstream source: `https://www.kernel.org/pub/linux/libs/klibc/2.0/klibc-2.0.14.tar.xz`
- SHA-256: `281bfb683e196818412af70b8968b7726475a80ff1c4bd67119e6bf5059f9075` (verified against the cached archive)
- Upstream test suite for `usr/kinit/fstype`: 0 cases. `rg -n '^#(if|ifdef).*TEST_' usr/kinit/fstype` and `rg -n '^[[:space:]]*(test|check):' usr/kinit/fstype/Kbuild` both returned no matches. The component Kbuild has no test target or self-test entry point. Declared and reported as 0/0.
- Consumer tests: 4/4 passed on the device:
  1. Detect gzip magic when given a file path.
  2. Detect gzip magic from stdin backed by a regular file.
  3. Report a sufficiently large zero-filled image as unknown with size 0.
  4. Reject excess command-line arguments with exit status 1.

The unknown-image fixture is 128 KiB because upstream probes signatures as far as block 64. The package builds the two upstream C translation units directly and packages `bin/fstype` plus the upstream license.
