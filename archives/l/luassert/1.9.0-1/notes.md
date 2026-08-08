# luassert 1.9.0-1 adaptation notes

## Scope

This package adds LunarModules luassert 1.9.0-1 as a pure Lua dependency for
the Busted/Vusted chain used by nvim-lspconfig Path B validation.

## Source

- Upstream repository: https://github.com/lunarmodules/luassert
- Source archive: https://github.com/lunarmodules/luassert/archive/refs/tags/v1.9.0.tar.gz
- Mirror: https://gh-proxy.com/https://github.com/lunarmodules/luassert/archive/refs/tags/v1.9.0.tar.gz
- SHA256: 1db0fabf1bd87392860375b89a8a37d17b687325c988be0df8c42e7e96e7ed73
- LuaRocks release: 1.9.0-1

## Package layout

- Installs `src/*.lua` to `share/lua/5.4/luassert/`
- Installs `src/matchers`, `src/formatters`, and `src/languages` under
  `share/lua/5.4/luassert/`
- Copies the MIT license to `licenses/LICENSE`
- Exports `LUA_PATH` through Conan runenv

## Upstream tests

The upstream Busted spec suite passed on the OHOS new-port leaf runner once the
Busted launcher provided a TMPDIR-backed `io.tmpfile()` fallback for the runner
sandbox.

- Run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r6-20260807-060440-54277`
- Result: `209 successes / 0 failures / 0 errors / 0 pending`

## Validation plan

The test package requires `lua/5.4.8.1` and `lua-say/1.4.1-3`, builds a small C
program against `liblua.a`, sets `LUA_PATH` for both Lua packages, and executes:

```lua
local luaassert = require('luassert')
luaassert.are.equal(1, 1)
luaassert.is.True(true)
luaassert.has.errors(function() error('expected') end)
```

This verifies package search paths, dependency loading through lua-say, and
representative assertion APIs needed by Busted.

## Validation results

- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-luassert-r2-20260807-060910-55644`
- Full ref: `luassert/1.9.0-1#bdbeed425a38a99ff275953c68120e0a:da39a3ee5e6b4b0d3255bfef95601890afd80709#877cedf130eb1cf409c3590c11c4e1fb`
- Consumer result: `1/1` smoke passed.
- Upstream result: `209 successes / 0 failures / 0 errors / 0 pending`
