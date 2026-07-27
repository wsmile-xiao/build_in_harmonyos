# Perl 5.42.2

Conan recipe for the Perl programming language interpreter on OHOS aarch64.

The recipe pins the official `v5.42.2` Git tag to its immutable commit, builds
with Perl's native `Configure` script, runs the upstream `make test` suite,
and packages the installed `perl` executable for build-tool consumers.
