# p5-io-compress-lzma

Conan recipe for the CPAN `IO-Compress-Lzma` distribution.

`IO-Compress-Lzma` provides Perl modules for reading and writing LZMA, XZ, and
Lzip streams through the `IO::Compress` and `IO::Uncompress` APIs.

## Package

- Version: 2.217
- Upstream: https://metacpan.org/dist/IO-Compress-Lzma
- License: perl_5
- Conan package name: `p5-io-compress-lzma`

The upstream task name uses CPAN casing (`p5-IO-Compress-Lzma`). Conan package
names are normalized to lowercase.

## Runtime Notes

This package contains the pure Perl modules from the distribution. Consumers also
need a Perl runtime and the CPAN runtime prerequisites:

- `Compress::Raw::Lzma` 2.217
- `IO::Compress::Base` 2.217
- `IO::Uncompress::Base` 2.217

