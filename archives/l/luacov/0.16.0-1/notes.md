# luacov 0.16.0-1 adaptation notes

## Scope

This package adds LuaCov as a pure Lua dependency for Busted's `--coverage`
option. It is required to run Busted's own upstream `spec/cl_spec.lua` coverage
configuration test on OHOS.

## Source

- Upstream repository: https://github.com/lunarmodules/luacov
- Source archive: https://github.com/lunarmodules/luacov/archive/refs/tags/v0.16.0.tar.gz
- SHA256: 0396d48fd12dd7dacf8bd3778d15ef17218e701f4a3c2f36e4e2a64b60db1736
- LuaRocks release: 0.16.0-1

## Package layout

- Installs Lua modules under `share/lua/5.4/luacov`
- Installs `src/bin/luacov` to `bin/luacov`
- Exports `LUA_PATH` and `PATH` through Conan runenv
- Requires `datafile/0.11-1`

## Upstream tests

The release source has no first-party Busted spec suite. Package validation uses
a consumer smoke test that loads LuaCov modules through Conan `LUA_PATH`.
Busted's own upstream suite separately validates LuaCov integration through
`busted --coverage --coverage-config-file=...`.

## OHOS validation

- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r6-20260807-050905-36912`
- Full ref: `luacov/0.16.0-1#a91bac2a7cb2a49c72dd04c9dcd07ec3:da39a3ee5e6b4b0d3255bfef95601890afd80709#59e8002239a6187e6a4decefe65f0501`
- Consumer result: `1/1` smoke passed.
- Upstream result: `0` first-party specs in the release source.
- Downstream coverage validation: Busted upstream run `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-upstream-specs-r7-20260807-051047-37947` passed `1670 successes / 0 failures / 0 errors / 7 pending`.
