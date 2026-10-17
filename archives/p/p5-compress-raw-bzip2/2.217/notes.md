# p5-compress-raw-bzip2 2.217 Build Notes

Date: 2026-08-01

## Summary

`Compress-Raw-Bzip2` is a Perl XS module. The Conan recipe builds it with
`ExtUtils::MakeMaker`, links against the existing `bzip2/1.0.8` package, and
packages the generated `blib/lib` and `blib/arch` trees under `lib/perl5`.

## Upstream Tests

Upstream provides 7 CPAN TAP files under `t/`. The recipe runs the upstream
suite with:

```sh
make test TEST_VERBOSE=1
```

On OHOS the generated XS `.so` files must be signed before Perl can load them,
so the recipe signs the `blib` shared object before running the upstream suite.

Verified on OHOS in runner directory:
`/storage/Users/currentUser/ohos-test-runs/codex-a-p5-compress-raw-bzip2-p5-compress-raw-bzip2-2.217-direct-r6-20260801-041622-5249`.
Result: 7/7 upstream files passed, 307/307 TAP assertions passed. The
`test_package` load/version check also passed.

## Runtime

Consumers load this package through `PERL5LIB=<package>/lib/perl5`. This package
is needed because `perl/5.42.2` only provides `Compress::Raw::Bzip2` 2.213,
while `IO-Compress` 2.217 requires 2.217.
