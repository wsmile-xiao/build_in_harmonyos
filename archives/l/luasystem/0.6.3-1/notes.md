# luasystem 0.6.3-1 adaptation notes

## Scope

This package adds LunarModules luasystem 0.6.3-1 as a native Lua dependency for
the Busted/Vusted chain used by nvim-lspconfig Path B validation.

## Source

- Upstream repository: https://github.com/lunarmodules/luasystem
- Source archive: https://github.com/lunarmodules/luasystem/archive/refs/tags/v0.6.3.tar.gz
- SHA256: 3a0f22b818d725d6439b0afca93108a2293a1a46d31b2296adf412e6da33651e
- LuaRocks release: 0.6.3-1

## Package layout

- Builds `system.core` from upstream C sources into `lib/lua/5.4/system/core.so`
- Installs `system/init.lua` to `share/lua/5.4/system/init.lua`
- Copies the MIT license to `licenses/LICENSE.md`
- Exports `LUA_PATH` and `LUA_CPATH` through Conan runenv

## Upstream tests

The upstream Busted spec suite contains 78 `it(...)` cases by static count:

- `spec/01-time_spec.lua`: 5
- `spec/02-random_spec.lua`: 4
- `spec/03-environment_spec.lua`: 5
- `spec/04-term_spec.lua`: 53
- `spec/05-bitflags_spec.lua`: 11

The automated upstream run executes the Busted suite with `--exclude-tags=manual`
because the OHOS validation runner is non-interactive and cannot provide the
terminal/TTY conditions required by manual cases.

- Upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r8-20260807-061840-58054`
- Result: `78 successes / 0 failures / 0 errors / 9 pending`
- Manual TTY cases are not claimed as passed.

## Validation plan

The test package requires `lua/5.4.8.1`, builds a small C program against
`liblua.a`, sets `LUA_PATH`/`LUA_CPATH`, and executes:

```lua
local system = require('system')
assert(type(system.gettime()) == 'number')
assert(#system.random(4) == 4)
system.setenv('LUASYSTEM_SMOKE', 'ok')
assert(system.getenv('LUASYSTEM_SMOKE') == 'ok')
assert((system.bitflag(3) - system.bitflag(1)):value() == 2)
```

This covers the Lua wrapper, native module loading, and representative exported
APIs without relying on the not-yet-packaged Busted runner.

## Validation results

- OHOS new-port run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-luasystem-r2-20260807-062101-58702`
- Full ref: `luasystem/0.6.3-1#5ffb40162e4dafeb79bc6ebdc4347a57:b3c0011005d51381f1539bc96e0d2a6e4f804b4e#35d2dae86e16312d819c6ecfae552621`
- Test output: `luasystem smoke ok`
- Gates: L0 pass, L1 pass, L2 skip-no-bin-dir, L4 pass, L5 pass
- L5 destructive negative test moved `lib/` away and confirmed the package
  smoke fails without the packaged native module.
