# busted 2.2.0-1 adaptation notes

## Scope

This package adds LunarModules Busted 2.2.0-1 as the Lua test framework needed
by Vusted and the nvim-lspconfig Path B validation chain.

## Source

- Upstream repository: https://github.com/lunarmodules/busted
- Source archive: https://github.com/lunarmodules/busted/archive/refs/tags/v2.2.0.tar.gz
- SHA256: befca10f573bb476fa1db2e3149150d65f802a71d34d1682679e640665f2dc2b
- LuaRocks release: 2.2.0-1

## Package layout

- Installs `busted.lua` to `share/lua/5.4/busted.lua`
- Installs the `busted/` module tree to `share/lua/5.4/busted/`
- Installs upstream `bin/busted` to `bin/busted.lua`
- Installs a native `bin/busted` launcher linked against packaged Lua
- The native launcher exposes Lua CLI-compatible negative `arg` entries for
  downstream `pl.app.lua()` users.
- The native launcher also maps `os.tmpname()` and `io.tmpfile()` to
  `TMPDIR`-backed temporary files for OHOS runner sandboxes.
- Copies the MIT license to `licenses/LICENSE`

## Dependency notes

Busted 2.2.0-1 depends on the following Lua packages in this Path B chain:

- `lua_cliargs/3.0.2-1`
- `luasystem/0.6.3-1`
- `dkjson/2.8-1`
- `lua-say/1.4.1-3`
- `luassert/1.9.0-1`
- `lua-term/0.7`
- `lua-penlight/1.15.0`
- `mediator_lua/1.1.2-0`

Penlight also requires `luafilesystem/1.8.0-1` for `pl.dir`, which Busted
loads through `busted.modules.test_file_loader`.

LuaCov is only needed for optional coverage mode. It is not required by the
packaged test runner or the consumer smoke tests. Lua CLIArgs requires
`inifile/1.1-1` for `config_loader.from_ini`.

## Upstream tests

The upstream tarball includes a Busted self-test suite under `spec/`. Full
execution passed on the OHOS new-port validation run after all test-runner
dependencies were available in the same isolated Conan home.

- Run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-upstream-specs-r9-20260807-060351-53729`
- Result: `1670 successes / 0 failures / 0 errors / 7 pending`
- Pending cases are upstream-declared pending items for async token callbacks,
  `__gc` error output, Moonscript, and LuaJIT FFI paths.

## Validation plan

The test package requires `lua/5.4.8.1`, builds a small C program against
`liblua.a`, explicitly composes `LUA_PATH` and `LUA_CPATH` across all Lua
dependencies, and loads Busted core modules to verify version metadata and
dependency resolution. It also executes a small Busted spec that checks the
native launcher exposes a reusable Lua CLI invocation for Penlight
`pl.app.lua()`.

## Validation results

- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r10-20260807-060245-52696`
- Full ref: `busted/2.2.0-1#2722ce1e253a8bef4ebc1b5043014b28:4df0932bd77659124e53ec83e89473d223e318ac#a1f9c8e5e3b4aac9cc28199a6aa51d8d`
- Test output: `busted smoke ok` and launcher compatibility smoke `1/1`
- Gates: L0 pass, L1 pass, L2 skip-nonblocking, L4 pass, L5 pass
- Upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-upstream-specs-r9-20260807-060351-53729`
- Upstream result: `1670 successes / 0 failures / 0 errors / 7 pending`
