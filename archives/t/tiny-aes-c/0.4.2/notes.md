# tiny-aes-c 0.4.2 adaptation notes

## Scope and provenance

- Package name and version: tiny-aes-c/0.4.2.
- Upstream project: CryptoManiac/tiny-aes-cpp.
- Upstream source: commit b2761c223710, pinned through the official GitHub
  codeload endpoint.
- Source SHA-256:
  f1cd837afe26f2ccc5027bed581f31325ac311a6348da15e8248887af1e96726.
- License: The Unlicense.

The upstream repository has no 0.4.2 tag or release. Version 0.4.2 is the
contribution-task and Conan package version; the immutable upstream identity is
the commit above. This C++ AES-256-CTR project is not the C tiny-AES-c project
by kokke that is already packaged as tiny-aes/1.0.0.

## Build

The pinned source contains only README.md, aes.cpp, aes.h, and unlicense.txt.
It has no CMakeLists.txt, Makefile, configure script, or third-party
dependencies. The recipe therefore:

1. downloads and hash-checks the pinned source archive;
2. applies patches/0001-aes.cpp.patch;
3. obtains the C++ compiler from the Conan compiler_executables profile map;
4. compiles aes.cpp as C++17 with strict warnings and optional PIC;
5. creates libtiny-aes-c.a with the configured or compiler-adjacent archiver;
6. installs aes.h, the static archive, and unlicense.txt.

The explicit source filename in conandata.yml is required because the codeload
URL has no archive suffix. This reuses the established E276 source-framing
pattern. Reading compiler executables from the profile map follows E392.

## Source patch

The single patch has three related C++ correctness changes:

1. Include algorithm directly before using std::copy_n. The original source
   fails a strict standalone compile because aes.cpp does not receive that
   declaration through aes.h.
2. Replace a union that is written through aes_block_t and then read through
   state_t. Those are distinct members, so reading the inactive member is not
   portable C++. Explicit row and column indexing preserves the prior byte
   order without depending on union type punning.
3. Return immediately for an empty vector and use indexed block traversal.
   This avoids constructing an end pointer from a possibly null data() result
   and documents the public empty-input behavior.

The patch is generated as a per-file unified diff by the repository
refresh-patch workflow and applies with patch -p1.

## Test inventory

The pinned upstream snapshot contains no test source and no test target, so the
upstream inventory is 0. No consumer assertion is counted as an upstream test.

The added test_package links the installed static library through the exported
CMake target and performs 12 assertions:

- NIST SP 800-38A F.5.5 four-block AES-256-CTR vector: 4;
- vector CTR round trip: 1;
- single-block NIST result, vector agreement, and round trip: 3;
- low-byte increment, big-endian carry, and full counter wrap: 3;
- empty-vector no-op: 1.

## Host verification

Environment: MinGW GCC 14.2.0 on Windows, C++17.

The unmodified source fails:

~~~text
error: comparison of integer expressions of different signedness
error: copy_n is not a member of std
~~~

The patched source was compiled with:

~~~text
g++ -std=c++17 -Wall -Wextra -Wpedantic -Werror -c aes.cpp
ar rcs libtiny-aes-c.a aes.o
g++ -D__OHOS__ -std=c++17 -Wall -Wextra -Wpedantic -Werror test_tiny_aes_c.cpp libtiny-aes-c.a
~~~

The linked consumer reported 12 assertions passed. The host command defines
__OHOS__ only to pass the test source's target guard, so this is host-executed
algorithm evidence, not HarmonyOS target evidence. The real HarmonyOS Conan and
device results are recorded below after target execution.

## HarmonyOS device verification

- Device: HarmonyOS HongMeng Kernel 1.12.0, aarch64, clang 15.0.4, Conan 2.31.1.
- Command: `conan create ... -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -tf=test_package`.
- Upstream inventory: 0 tests (confirmed from the pinned archive).
- Installed consumer: 12/12 assertions passed on the target, including the
  NIST AES-256-CTR vector, round trips, counter carry/wrap, and empty input.
- The target clang wrapper injects linker-only flags into compile commands; the
  recipe and consumer test demote only that warning while retaining `-Werror`
  for source diagnostics.

## Known limits

- Only AES-256-CTR is exposed; AES-128, AES-192, ECB, CBC, and other modes are
  not part of this package API.
- CTR mode requires callers never to reuse the same key and counter pair.
- No shared-library option is provided; the upstream project and this recipe
  deliver a static archive.
