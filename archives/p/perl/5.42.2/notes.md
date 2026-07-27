# Perl 5.42.2 OHOS Notes

- Source is the official `v5.42.2` tag pinned to commit
  `b62845c7186b0b6a8e4e83419e6b5ef64ceef3ed`.
- Perl uses its own `Configure` script rather than Autotools. The recipe
  supplies the compiler and archive tools from the Conan OHOS profile.
- `make test` is intentionally retained as the nonzero upstream test suite.
- The test package invokes the installed interpreter and loads core modules.
