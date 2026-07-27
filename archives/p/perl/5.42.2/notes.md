# Perl 5.42.2 OHOS Notes

- Source is the official CPAN `perl-5.42.2.tar.gz` archive verified with
  SHA256 `9384e8deb75b7b1695e5637971b752281aaecd025a3d5d4734d33c1d0adfee47`.
- Perl uses its own `Configure` script rather than Autotools. The recipe
  supplies the compiler and archive tools from the Conan OHOS profile.
- `make test` is intentionally retained as the nonzero upstream test suite.
- The test package invokes the installed interpreter and loads core modules.
