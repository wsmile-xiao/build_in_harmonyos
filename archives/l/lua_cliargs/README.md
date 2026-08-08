# lua_cliargs

lua_cliargs is a pure Lua command-line argument parsing module. This archive
packages the LunarModules 3.0.2-1 release for the Lua/Busted/Vusted dependency
chain used by nvim-lspconfig Path B validation.

## OHOS scope

- Pure Lua package; no native build or ELF signing is required.
- Installs modules under `share/lua/5.4`.
- Exports `LUA_PATH` through Conan runenv for downstream consumers.
- Validates `require('cliargs.core')` and a minimal parse smoke test through a
  C program linked against `lua/5.4.8`.
