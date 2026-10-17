# acf-quagga 0.10.1 notes

## Package

- Upstream: https://gitlab.alpinelinux.org/acf/acf-quagga
- Source archive: Alpine official distfiles mirror over HTTP, with SHA256
  matching the upstream GitLab v0.10.1 archive. This avoids CI workers whose
  Python runtime lacks SSL support during Conan source download.
- License: GPL-2.0-only
- Type: Alpine Configuration Framework app module
- Build: pure Lua/LSP resources; upstream `all` is empty and `install` copies `bgp*`, `ospf*`, and `zebra*` into `$(appdir)/quagga`

## Tests

The upstream v0.10.1 source archive does not provide a first-party automated
test suite. The added `test_package` checks the installed ACF module layout and
shared template links for the bgp, ospf, and zebra submodules. On filesystems
where symlink creation is unavailable, the recipe stores the link target in a
fallback file and the test verifies that target. If a Lua interpreter is
available it also parses installed `.lua` files without executing module code.

## OHOS validation

- 2026-08-17, 56267: `CI_PACKAGES=archives/a/acf-quagga/0.10.1 zsh ci/conan/build_and_test.sh`
- Result: pass (`L0_RESULT=pass`, `L1_RESULT=pass`; `L2_RESULT=skip` because no `bin/` directory)
