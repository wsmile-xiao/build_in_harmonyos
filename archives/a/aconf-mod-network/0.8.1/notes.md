# aconf-mod-network 0.8.1 notes

## Package

- Upstream: https://gitlab.alpinelinux.org/kunkku/aconf/ (Alpine Configurator)
- License: BSD-2-Clause
- Type: pure Lua module (Alpine `aconf-mod-network` subpackage)
- Build: no compilation; Alpine splits `aconf/modules/network.lua` into this
  subpackage, installed under `usr/share/lua/5.3/aconf/modules/`

## Tests

Upstream aconf 0.8.1 does not ship a first-party automated test suite
(Alpine's aports recipe declares `options="!check"`). The added `test_package`
verifies the module file is present and syntactically parseable when a Lua
interpreter is available.

## OHOS validation

- Status: CI L0/L1/L4/L5 gate verification pending (pure Lua data package with
  no compiled code; `bin/` and `lib/` are absent by design, so L2 is expected
  to skip).
