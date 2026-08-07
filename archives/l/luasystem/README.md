# luasystem

luasystem provides platform-independent system calls for Lua. This archive
packages the LunarModules 0.6.3-1 release for the Busted/Vusted dependency
chain used by nvim-lspconfig Path B validation.

## OHOS scope

- Builds the native `system.core` Lua C module for OHOS.
- Installs Lua wrapper files under `share/lua/5.4` and C modules under
  `lib/lua/5.4`.
- Exports `LUA_PATH` and `LUA_CPATH` through Conan runenv for downstream
  consumers.
- Validates `require('system')`, time, random, environment, and bitflag smoke
  behavior through a C program linked against `lua/5.4.8`.
