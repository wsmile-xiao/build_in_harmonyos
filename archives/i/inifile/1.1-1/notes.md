# inifile 1.1-1 adaptation notes

## Scope

This package adds the pure Lua `inifile` module used by `lua_cliargs` for
`config_loader.from_ini`.

## Source

- Upstream repository: https://github.com/bartbes/inifile
- Source archive: https://github.com/bartbes/inifile/archive/refs/tags/v1.1.tar.gz
- SHA256: 3beb7db2d8ade8658152329c3644c8403300dc780d2dba346e612e45ef01ac24
- LuaRocks release: 1.1-1

## Package layout

- Installs `inifile.lua` to `share/lua/5.4/inifile.lua`
- Copies `inifile.lua` to `licenses/` because it contains the upstream
  Simplified BSD license notice
- Exports `LUA_PATH` through Conan runenv

## Upstream tests

The upstream source includes `inifile_spec.lua`. The Path B leaf upstream runner
executes that Busted spec once `busted/2.2.0-1` is available in the same Conan
home.

## OHOS validation

- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r6-20260807-050905-36912`
- Full ref: `inifile/1.1-1#f3e4b09d2b81a3fedd90213779dcddec:da39a3ee5e6b4b0d3255bfef95601890afd80709#3e19ce241c6ccba38d5056d6021d7640`
- Upstream run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-lua-pathb-leaf-upstream-r4-20260807-051152-38567`
- Upstream result: `18 successes / 0 failures / 0 errors / 0 pending`
- Consumer result: `1/1` smoke passed.
