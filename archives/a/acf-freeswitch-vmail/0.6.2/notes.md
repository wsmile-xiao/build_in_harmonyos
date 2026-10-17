# acf-freeswitch-vmail 0.6.2 notes

## Package

- Upstream: https://gitlab.alpinelinux.org/acf/acf-freeswitch-vmail
- License: GPL-2.0-only
- Type: Alpine Configuration Framework app module
- Build: pure Lua/LSP resources; upstream `all` is empty and `install` copies `vmail*` and `template*` into `$(appdir)/freeswitch-vmail`, plus `authenticator-freeswitch-vmail.lua` into `$(acflibdir)`

## Tests

The upstream v0.6.2 source archive does not provide a first-party automated
test suite. The added `test_package` checks the installed ACF module layout:
controller, model, roles, menu, XML/LSP templates, authenticator library file,
and preserved module-local symlinks. If a Lua interpreter is available it also
parses installed `.lua` files without executing module code.

## OHOS validation

- 2026-08-16 17:28-17:29 CST, true device port 33332, runner:
  `/storage/Users/currentUser/ohos-test-runs/codex-a-acf-three-acf-three-20260816-r1-conan-r1-20260816-172817-36375`
- Command: `zsh ci/conan/build_and_test.sh archives/a/acf-freeswitch/0.8.0 archives/a/acf-freeswitch-vmail/0.6.2 archives/a/acf-amavisd-new/0.4.0`
- Runner exit code: 0; heavy lock acquired after 0 seconds.
- Gate results: L0 pass, L1 pass, L2 skip (no `bin/`), L4 pass, L5 pass
  (`share/acf/lib/authenticator-freeswitch-vmail.lua` packaged).
- `test_package`: 11 file/symlink layout checks passed, 0 failed. Lua parsing was
  skipped because the true-device environment did not provide a Lua interpreter.
