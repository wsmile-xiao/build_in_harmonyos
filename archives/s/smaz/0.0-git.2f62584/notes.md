# smaz 0.0-git.2f62584 OHOS PC 适配笔记

## Upstream

- Repository: https://github.com/antirez/smaz
- Fixed commit: `2f625846a775501fb69456567409a8b12f10ea25` (master HEAD, verified via git ls-remote)
- License: BSD-3-Clause (COPYING, 2006-2009 Salvatore Sanfilippo)
- Language: C99
- Third-party dependencies: none

Upstream publishes no release or version tag (git ls-remote --tags is empty). The
package version `0.0-git.2f62584` follows the team's git-snapshot convention:
`0.0` because the project never declared a version, `git` + abbreviated commit
hash for reproducibility.

## Build

The library is a single translation unit (smaz.c + smaz.h) with no build system
beyond a two-line Makefile that only builds the test program. The recipe
compiles smaz.c with the HarmonyOS Clang toolchain directly (`-std=c99 -Wall
-pedantic -O2`), archives `libsmaz.a` with llvm-ar, and packages the static
library, smaz.h, and the license. No source patch is required. The compiler is
resolved from `tools.build:compiler_executables` conf (R33: no bare ${CC}).

## Upstream tests

Upstream ships one test program, smaz_test.c, built by `make` via
`gcc -o smaz_test -O2 -Wall -W -ansi -pedantic smaz.c smaz_test.c`. The recipe
compiles it from the unmodified upstream sources and runs it on the OHOS
device after self-signing with binary-sign-tool (same flow as sds 2.0). The
only build-flag difference from the upstream Makefile is `-std=gnu99` instead
of `-ansi`, because musl/OHOS does not declare POSIX `random()` under strict
ISO C99 — the test source itself is unchanged.

The program iterates 17 fixed strings (English text, URLs, Italian sentences)
plus 1,000,000 randomized round-trips (alternating charset-constrained and
raw-byte random buffers), reporting "TEST PASSED :)" on success. Counted as
one upstream test boundary with 1,000,017 runtime assertions; the iteration
count is not inflated into separate test cases.

## Consumer test

One Conan consumer executable links the packaged `smaz::smaz` target and
verifies 8 assertions: short-string compression ratio, lossless English
round-trip, lossless URL round-trip, binary data containing the verbatim
opcode bytes 0x00/0xfe/0xff/0x80/0x7f round-trips losslessly, empty-input
compression and decompression, single-character round-trip, and undersized
output buffer reporting (returns outlen+1 as documented in the upstream
README).

## 验证结果

```bash
$ conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
    --build=missing -c tools.build:jobs=2
...
smaz/0.0-git.2f62584: Package 'a4caeb1cf8f7ab732f69b3dbd0e46f0f9d99cd8b' built
...
TEST PASSED :)            # upstream smaz_test, 17 fixed + 1000000 random round-trips
smaz consumer test passed: 8 assertions
```
