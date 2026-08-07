# autoconf

GNU Autoconf generates portable `configure` scripts from `configure.ac` templates.

## OHOS adaptation

- Package type: command-line build tool.
- Installed commands: `autoconf`, `autoheader`, `autom4te`, `autoreconf`, `autoscan`, `autoupdate`, `ifnames`.
- Runtime/build dependencies: `perl/5.42.2` and `m4/1.4.19`; both have OHOS armv8 packages in `ohpcd`.
- The 2.72 release tarball already ships `configure` and `Makefile.in`; the recipe does not run `autoreconf` while building Autoconf itself.

## Versions

| Version | Status | Notes |
|---------|--------|-------|
| [2.72](./2.72/) | built | OHOS isolated runner passed L0/L1/L5; upstream `make check` executed separately with 297/539 expected outcomes excluding 70 skipped |
