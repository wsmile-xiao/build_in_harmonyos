# acf-snort 0.8.1 notes

## Package

- Upstream: https://gitlab.alpinelinux.org/acf/acf-snort
- License: GPL-2.0-only
- Type: Alpine Configuration Framework app module
- Build: pure Lua/LSP resources; upstream `all` is empty and `install` copies `snort*` into `$(appdir)/snort`

## Tests

The upstream v0.8.1 source archive does not provide a first-party automated
test suite. The added `test_package` checks the installed ACF module layout and
shared template links. On filesystems where symlink creation is unavailable,
the recipe stores the link target in a fallback file and the test verifies that
target. If a Lua interpreter is available it also parses installed `.lua` files
without executing module code.

## OHOS validation

- 2026-08-17, 56267: `CI_PACKAGES=archives/a/acf-snort/0.8.1 zsh ci/conan/build_and_test.sh`
- Result: pass (`L0_RESULT=pass`, `L1_RESULT=pass`; `L2_RESULT=skip` because no `bin/` directory)
