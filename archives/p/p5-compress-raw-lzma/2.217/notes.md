# p5-compress-raw-lzma 2.217 Build Notes

Date: 2026-08-01

## Summary

`Compress-Raw-Lzma` is a Perl XS module. The Conan recipe builds it with
`ExtUtils::MakeMaker`, links against the existing `xz/5.6.2` package, and
packages the generated `blib/lib` and `blib/arch` trees under `lib/perl5`.

## Upstream Tests

Upstream provides 10 CPAN TAP files under `t/`. The recipe runs the upstream
suite with:

```sh
make test TEST_VERBOSE=1
```

On OHOS the generated XS `.so` files must be signed before Perl can load them,
so the recipe signs the `blib` shared object before running the upstream suite.

Verified on OHOS in runner directory:
`/storage/Users/currentUser/ohos-test-runs/codex-a-p5-compress-raw-lzma-p5-compress-raw-lzma-2.217-direct-r1-20260801-043818-52164`.
Result: 10/10 upstream files passed, with 3399/3399 executed TAP assertions
passed. The `test_package` load/version check also passed.

## Runtime

Consumers load this package through `PERL5LIB=<package>/lib/perl5`. This package
is required by `p5-io-compress-lzma/2.217` because `perl/5.42.2` does not provide
`Compress::Raw::Lzma`.
