# lua_cliargs 3.0.2-1 adaptation notes

## Scope

This package adds LunarModules lua_cliargs 3.0.2-1 as a pure Lua dependency for
the Busted/Vusted chain used by nvim-lspconfig Path B validation.

## Source

- Upstream repository: https://github.com/lunarmodules/lua_cliargs
- Source archive: https://github.com/lunarmodules/lua_cliargs/archive/refs/tags/v3.0.2.tar.gz
- Mirror: https://gh-proxy.com/https://github.com/lunarmodules/lua_cliargs/archive/refs/tags/v3.0.2.tar.gz
- SHA256: a7a57ab9c73f6c44040a78305b6dc7780ca1565cc4c9057d74a6608cb0443af4
- LuaRocks release: 3.0.2-1

## Package layout

- Installs `src/cliargs.lua` to `share/lua/5.4/cliargs.lua`
- Installs `src/cliargs/*.lua` and `src/cliargs/utils/*.lua` under `share/lua/5.4/cliargs`
- Copies the MIT license to `licenses/LICENSE`
- Exports `LUA_PATH` through Conan runenv

## Validation plan

The test package requires `lua/5.4.8.1`, builds a small C program against
`liblua.a`, and executes:

```lua
local cli = require('cliargs.core')()
cli:argument('ARG', 'argument description')
local result = cli:parse({'value'})
assert(result.ARG == 'value')
local loader = require('cliargs.config_loader')
local config = assert(loader.from_ini('cliargs-smoke.ini'))
assert(config.mode == 'fast')
```

This verifies the package search path, a minimal parser behavior, and the INI
configuration loader. `config_loader.from_ini` requires `inifile`, so this
package now models `inifile/1.1-1` as a Conan dependency.

## Validation results

- Local Windows/MinGW package-only `conan create -tf ''`: passed
- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r6-20260807-050905-36912`
- Full ref: `lua_cliargs/3.0.2-1#12a39ab4eaef75aa23d2208023353a08:da39a3ee5e6b4b0d3255bfef95601890afd80709#33d1aaa763907845ec35e5bb1ad7cca9`
- Test output: `lua_cliargs smoke ok`
- Gates: L0 pass, L1 pass, L2 skip-no-bin-dir, L4 pass, L5 warn-no-artifacts-for-pure-Lua
- OHOS upstream Busted run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r4-20260807-051152-38567`
- Upstream result: `174 successes / 0 failures / 0 errors / 0 pending`

The L5 warning is expected for this package because it installs only Lua source
under `share/lua/5.4` and has no `bin/` or `lib/` payload.
