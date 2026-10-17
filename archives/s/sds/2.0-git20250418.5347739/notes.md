# SDS 2.0-git20250418.5347739 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/antirez/sds
- Version generation: SDSLib 2.0
- Fixed commit: `5347739b1581fcba74fd5cab1fc21d2aef317d71`
- Commit date: 2025-04-18
- License: BSD-2-Clause
- Language: C99
- Third-party dependencies: none

Upstream publishes no release or version tag. The package version combines the API
generation declared in `sds.c` and `README.md`, the commit date, and the abbreviated
commit hash for reproducibility.

## Build

The recipe compiles `sds.c` with the HarmonyOS Clang toolchain and packages
`libsds.a`, `sds.h`, `sdsalloc.h`, and the license. No source patch is required.

## Upstream tests

Upstream provides one test executable through the `SDS_TEST_MAIN` compile definition.
The original test body is embedded in `sds.c`; although it has 28 static `test_cond`
call sites, allocation-growth checks run repeatedly and produce 46 runtime assertions.
They cover creation, binary safety, concatenation, formatting, trimming, ranges,
comparison, representation, allocation growth, lengths, and content preservation.
The recipe compiles the upstream test unchanged, signs the HarmonyOS ELF, and runs it.
The 46 runtime assertions are not inflated into separate test-case boundaries.

## Consumer test

One Conan consumer executable links the packaged `sds::sds` target and verifies
creation, binary-safe append, formatted append, trimming, range extraction, splitting,
and joining. Its assertions form one consumer integration-test boundary.
