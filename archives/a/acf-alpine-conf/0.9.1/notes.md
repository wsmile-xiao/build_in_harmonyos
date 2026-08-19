# acf-alpine-conf 0.9.1 notes

## Package

- Upstream: https://gitlab.alpinelinux.org/acf/acf-alpine-conf
- License: GPL-2.0-only
- Type: Alpine Configuration Framework app module
- Build: pure Lua/LSP resources; upstream `all` is empty and `install` copies `lbu*` into `$(appdir)/alpine-conf`

## Tests

The upstream v0.9.1 source archive does not provide a first-party automated
test suite. The added `test_package` checks the installed ACF module layout:
controller, model, roles, menu, and LSP templates.

## OHOS validation

- Status: CI L0/L1/L4/L5 gate verification pending (package is a pure ACF
  resource package with no compiled code; `bin/` and `lib/` are absent by
  design, so L2 is expected to skip).
