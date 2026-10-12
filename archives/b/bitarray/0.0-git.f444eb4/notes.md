# bitarray 0.0-git.f444eb4 OHOS PC 适配笔记

## Upstream

- Repository: https://github.com/noporpoise/bitarray
- Fixed commit: `f444eb4` (master HEAD at packaging time; newer than the last
  release tag v2.0, which predates the 2014 header/word-width rework)
- License: Public Domain / CC0 (LICENSE file is the CC0 legal text; README:
  "This software is in the Public Domain")
- Language: C99
- Third-party dependencies: none

Upstream publishes no release tags (git ls-remote --tags only shows the ancient
`v2.0` tag from the pre-2014 API). The package version `0.0-git.f444eb4`
follows the team's git-snapshot convention: `0.0` because the project never
declared a version, `git` + abbreviated commit hash for reproducibility.

## Build

The library is a single translation unit (bit_array.c + bit_array.h, which
includes bit_macros.h) with no real build system: the top-level Makefile is
example-grade and merely archives `bit_array.o` into `libbitarr.a` with
`ar -csru`. The recipe compiles bit_array.c with the HarmonyOS Clang toolchain
directly (`-std=c99 -Wall -Wextra -Wc++-compat -O2 -fPIC`), archives
`libbitarr.a` with llvm-ar, and packages the static library plus the three
public headers (bit_array.h, bit_macros.h, bar.h — bar.h is the upstream
short-name wrapper API, exercised by the upstream `test_bar_wrapper` suite)
and the license. No source patch is required. The compiler is resolved from
`tools.build:compiler_executables` conf (R33: no bare ${CC}).

## Upstream tests

`make test` runs, from dev/Makefile, `./bit_array_test && ./bitlock_test`
(examples/Makefile's `test` target just runs the demo programs):

- **bit_array_test** — the main upstream test program, linked against
  libbitarr.a. 31 test suites / 15564 ASSERT() checks covering create/clone,
  set/get/clear/toggle, regions, word load/store, shift/rotate, arithmetic
  (add/minus/multiply/div), next_permutation, random+shuffle, and the bar.h
  wrapper API. On-device run after self-signing: `0/31 suites failed`,
  `0/15564 tests failed`, exit 0.
- **bitlock_test** — exercises the header-only bitlock acquire/release macros
  over 8 worker threads (10000 loops each), verifying the protected sum
  matches the expected value (1504500000). On-device run: `Pass.`, exit 0.

Test sources are compiled unmodified. The only build-flag difference from the
upstream Makefile is `-std=gnu99` (instead of no explicit standard) so the
STD/POSIX declarations in the OHOS sysroot headers stay visible; bitlock_test
links `-lpthread` exactly as upstream does. One benign compiler warning
(`-Wimplicit-const-int-float-conversion` in bit_array_test.c's RAND_MAX *
prob) does not affect the result.

## Consumer test

One Conan consumer executable links the packaged `bitarray::bitarray` target
and verifies 16 assertions: create/free lifecycle, single-bit set/get/clear/
toggle flipping (including bit 0 and the last bit), the variadic
`bit_array_set_bits(3, 1,2,5)` call pattern from upstream examples/example.c,
`bit_array_to_str` serialization (`1000000001`), `bit_array_from_str`
round-trip of the serialized pattern, `bit_array_to_str_rev` on a palindrome
pattern, and `bit_array_resize` growth preserving existing bits.

## 验证结果

```bash
$ conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
    --build=missing -c tools.build:jobs=2
...
bitarray/0.0-git.f444eb4: Package '…' built
...
 0 / 31 suites failed              # upstream bit_array_test
 0 / 15564 tests failed
Testing Bitlocks ... Pass.          # upstream bitlock_test
bitarray consumer test passed: 16 assertions
```
