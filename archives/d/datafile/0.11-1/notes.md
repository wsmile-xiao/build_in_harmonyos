# datafile 0.11-1 adaptation notes

## Scope

This package adds the pure Lua `datafile` module used by LuaCov. It is part of
the Busted/Vusted toolchain needed for Neovim-hosted upstream tests.

## Source

- Upstream repository: https://github.com/hishamhm/datafile
- Source archive: https://github.com/hishamhm/datafile/archive/refs/tags/v0.11.tar.gz
- SHA256: b9e7ffff06b88ea1dc5b3ef9b08b3c3e78a3b6d6a6da3c2042cf3b65375134de
- LuaRocks release: 0.11-1

## Package layout

- Installs `datafile.lua` to `share/lua/5.4/datafile.lua`
- Installs upstream `datafile/*.lua` modules to `share/lua/5.4/datafile/`
- Exports `LUA_PATH` through Conan runenv

## Upstream tests

The release source has no first-party Busted spec suite. Package validation uses
a consumer smoke test that loads `datafile` and its packaged opener modules from
Conan `LUA_PATH`.

## OHOS validation

- OHOS new-port build/test_package run: `/storage/Users/currentUser/ohos-users/codex-a/neovim-vusted-pathb-integration-20260806/runs/codex-a-busted-luacov-chain-r6-20260807-050905-36912`
- Full ref: `datafile/0.11-1#e660224df2c9bc17d4870bd166d4ef6a:da39a3ee5e6b4b0d3255bfef95601890afd80709#3a8318a43717f09b5d403559ef106b86`
- Consumer result: `1/1` smoke passed.
- Upstream result: `0` first-party specs in the release source.
