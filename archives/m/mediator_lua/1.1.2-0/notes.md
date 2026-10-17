# mediator_lua 1.1.2-0 adaptation notes

## Scope

This package adds Olivine Labs mediator_lua 1.1.2-0 as a pure Lua dependency
for the Busted/Vusted chain used by nvim-lspconfig Path B validation.

## Source

- Upstream repository: https://github.com/Olivine-Labs/mediator_lua
- Source archive: https://github.com/Olivine-Labs/mediator_lua/archive/v1.1.2-0.tar.gz
- Mirror: https://gh-proxy.com/https://github.com/Olivine-Labs/mediator_lua/archive/v1.1.2-0.tar.gz
- SHA256: faf5859fd2081be4e9e4fb8873a2dc65f7eff3fd93d6dd14da65f8e123fcff9b
- LuaRocks release: 1.1.2-0

## Package layout

- Installs `src/mediator.lua` to `share/lua/5.4/mediator.lua`
- Copies upstream `README.md`, which includes the MIT license notice, to
  `licenses/README.md`
- Exports `LUA_PATH` through Conan runenv

## Upstream tests

The upstream Busted spec suite contains 26 `it(...)` cases in
`spec/mediator_spec.lua` by static count.

After the Lua CLI and Busted bootstrap chain became available in the Path B
integration workspace, this upstream suite was run unchanged on the OHOS
new-port device.

- Command: `busted --loaders lua --pattern "_spec.lua$" --output plainTerminal spec`
- OHOS new-port run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r2-20260807-023655-51799`
- Busted runner: packaged `busted/2.2.0-1` from the Path B integration chain
- Lua runner: packaged `lua/5.4.8.1` from the Path B integration chain
- Result: `26 successes / 0 failures / 0 errors / 0 pending`

## Validation plan

The test package requires `lua/5.4.8`, builds a small C program against
`liblua.a`, sets `LUA_PATH`, and executes:

```lua
local Mediator = require('mediator')
local mediator = Mediator()
local received
mediator:subscribe({'ohos'}, function(payload) received = payload.value end)
mediator:publish({'ohos'}, {value = 'ok'})
assert(received == 'ok')
```

This verifies the package search path, constructor, channel subscription, and
event publish behavior needed by downstream Lua test tooling.

## Validation results

- Local Windows/MinGW package-only `conan create -tf ''`: passed
- Local package-only full ref: `mediator_lua/1.1.2-0#b240b21f199b27cabdb4b2c1df24338b:da39a3ee5e6b4b0d3255bfef95601890afd80709#a3127c83b71f9ab46e3c38a8725c0558`
- OHOS new-port integration run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-lua-stack-r1-20260807-023057-41672`
- Full ref: `mediator_lua/1.1.2-0#a9e6061deb95a8dc548313cf56ea8c00:da39a3ee5e6b4b0d3255bfef95601890afd80709#a3127c83b71f9ab46e3c38a8725c0558`
- Test output: `mediator_lua smoke ok`
- Gates: L0 pass, L1 pass, L2 skip-no-bin-dir, L4 pass, L5 warn-no-artifacts-for-pure-Lua

The L5 warning is expected for this package because it installs only Lua source
under `share/lua/5.4` and has no `bin/` or `lib/` payload.
