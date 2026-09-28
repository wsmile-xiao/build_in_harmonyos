# debconf 1.5.92 HarmonyOS PC package notes

## Packaging

`debconf` is a pure Perl application. The recipe downloads the official Debian source archive, installs `Debconf/**/*.pm` beneath `lib/perl5`, and copies its executable `debconf-*` helpers to `bin`. It does not invoke the upstream `all` target, which builds documentation, translations and a bitmap rather than the runtime modules. No external CPAN runtime modules are required.

The source archive contains both `work/Debconf/` and the executable `work/debconf`. On the case-insensitive HMDFS, those paths collide during extraction. The tar extraction renames the executable temporarily to `debconf.tool`; package() restores its intended `bin/debconf` name.

## Tests

The upstream `Test/` suite uses `Test::Unit::*`, with LDAP/SLAPD integration. The OHOS runtime does not provide these CPAN test modules or LDAP service, so the suite cannot run here. Its test source declares 7 `sub test_*` methods (`rg -c '^\s*sub\s+test_[A-Za-z0-9_]+' Test`). This limitation is recorded in `test_package/MANIFEST.yml` and is not counted as an upstream pass.

The HarmonyOS consumer test loads the packaged `Debconf::Priority` API, checks the exported priority list and validation behavior, then invokes the packaged `debconf-escape -u` command with a newline escape. It covers 8 assertions in total: the ordered priority list, four known priority values, rejection of an unknown value, and an escape/unescape round trip.
