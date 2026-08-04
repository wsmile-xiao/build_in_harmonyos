# p5-io-compress 2.217 Build Notes

Date: 2026-08-01

## Summary

`IO-Compress` is a pure Perl module distribution. The Conan recipe runs the
upstream MakeMaker build, then packages the upstream `lib/` tree under
`lib/perl5` and exposes it through `PERL5LIB`.

## Dependencies

`META.json` requires:

- `Compress::Raw::Bzip2` 2.217
- `Compress::Raw::Zlib` 2.217
- Perl core modules `Encode`, `Scalar::Util`, and `Time::Local`

`perl/5.42.2` provides `Compress::Raw::Zlib` 2.222, which satisfies the zlib
requirement. It only provides `Compress::Raw::Bzip2` 2.213, so this package
requires `p5-compress-raw-bzip2/2.217`.

## Upstream Tests

Upstream provides 93 CPAN TAP files under `t/`. The recipe runs the upstream
suite with:

```sh
make test TEST_VERBOSE=1
```

The `bin/zipdetails` and `bin/streamzip` scripts are preserved under
`share/p5-io-compress/bin`, but this package is exposed as a Perl module
dependency rather than a command package.

Verified on OHOS in runner directory:
`/storage/Users/currentUser/ohos-test-runs/codex-a-p5-io-compress-p5-io-compress-2.217-direct-r2-20260801-043159-32125`.
Result: 93/93 upstream files passed, with 25472/25472 executed TAP assertions
passed. The `test_package` gzip/gunzip roundtrip also passed.

## HarmonyOS Adaptation

The recipe patches `lib/IO/Compress/Base.pm` during build. Upstream disables
Merge mode for an empty target file only when Perl's `-w` file test reports the
file as writable. On OHOS, `-w` can return false for a file that is actually
appendable, which leaves Merge enabled and makes `InflateScan` fail on an empty
file. The patch treats an existing zero-length file as a normal append target;
truly unwritable files still fail later when opened for append.
