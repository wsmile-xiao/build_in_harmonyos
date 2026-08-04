# p5-io-compress-lzma 2.217 Build Notes

Date: 2026-08-01

## Summary

The CPAN distribution `IO-Compress-Lzma` 2.217 is a pure Perl module set. The
Conan recipe packages the upstream `lib/` tree into `lib/perl5` and exposes that
directory through `PERL5LIB`. It also packages upstream `Makefile.PL`,
`META.json`, `META.yml`, the full upstream `t/` test tree, and upstream
`examples/` scripts under
`share/p5-io-compress-lzma`.

The contrib task name is `p5-IO-Compress-Lzma`; the Conan package name is
normalized to lowercase as `p5-io-compress-lzma`.

## Runtime Dependencies

`META.json` lists these runtime prerequisites:

- `Compress::Raw::Lzma` 2.217
- `IO::Compress::Base` 2.217
- `IO::Uncompress::Base` 2.217

They are not built into this package.
They are supplied by the local Conan dependency chain:

- `perl/5.42.2`
- `p5-io-compress/2.217`
- `p5-compress-raw-lzma/2.217`
- `p5-compress-raw-bzip2/2.217` transitively through `p5-io-compress`

## Upstream Tests

Upstream provides a CPAN TAP test suite, normally run with `prove -lr t`.
The 2.217 release contains 45 `.t` files covering prerequisite checks,
LZMA/XZ/Lzip compression, truncation, tied handles, one-shot APIs,
interoperability, metadata, and POD.

After adapting the required local dependencies, the `test_package` now copies
packaged `lib/`, `t/`, and `examples/` into a writable upstream test tree and
runs the upstream suite with Conan's Perl interpreter:

```sh
perl prove -lr t
```

Verified on OHOS in runner directory:
`/storage/Users/currentUser/ohos-test-runs/codex-a-p5-io-compress-lzma-p5-io-compress-lzma-2.217-direct-r3-20260801-045357-23372`.
Result: `Files=45, Tests=19109, Result: PASS`. Some tests keep their upstream
TAP skip conditions for optional external tools/modules and disabled lengthy
tests; those skips are reported by TAP and are not failures. The Python
inventory check remains adapted consumer validation and is recorded separately
from upstream TAP tests.

## Validation Notes

The previous 2026-07-31 validation only packaged the upstream `t/` inventory and
did not run CPAN TAP tests. That old result is superseded by the 2026-08-01
OHOS run above, where `prove -lr t` executed and passed.
