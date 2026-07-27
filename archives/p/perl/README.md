# Perl 5.42.2

Conan recipe for the Perl programming language interpreter on OHOS aarch64.

The recipe downloads the official CPAN release archive with a SHA256 check,
builds with Perl's native `Configure` script, runs the upstream `make test`
suite, and packages the installed `perl` executable for build-tool consumers.
