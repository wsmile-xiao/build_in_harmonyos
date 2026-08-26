# TinyExpr 1.1.1 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/codeplea/tinyexpr
- Tag: `v1.1.1`
- Commit: `6d2233ce14dca063994708a91b3b98e24e8aa0c3`
- License: Zlib
- Language: C99
- Third-party dependencies: none; the library links the system math library

## Build

The recipe compiles `tinyexpr.c` with the HarmonyOS Clang toolchain and packages
`libtinyexpr.a`, `tinyexpr.h`, and the Zlib license. No upstream source patch is
required.

## Upstream tests

The upstream Makefile defines two independent test targets:

1. `smoke` tests the default TinyExpr semantics.
2. `smoke_pr` rebuilds the same upstream suite with `TE_POW_FROM_RIGHT` and
   `TE_NAT_LOG`, testing right-associative exponentiation and natural-log behavior.

Each executable runs 15 named upstream test groups. The recipe compiles the original
`smoke.c` unchanged, signs each HarmonyOS ELF, and runs both targets. Test groups and
internal assertions are not inflated into additional test-case boundaries.

## Consumer test

One Conan consumer executable links the packaged `tinyexpr::tinyexpr` target. It
checks direct expression evaluation, variable binding with repeated evaluation,
parse-error reporting, and standard math function support. Its assertions form one
consumer integration-test boundary.
