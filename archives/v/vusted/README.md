# vusted

## Overview

Vusted is a Busted wrapper for testing Neovim plugins. This package provides
Vusted `2.5.3-1` for the nvim-lspconfig Path B validation chain.

## Package Layout

- Lua modules: `$PREFIX/share/lua/5.4/vusted/`
- Busted output handler: `$PREFIX/share/lua/5.4/busted/outputHandlers/vusted/default.lua`
- CLI entrypoint: `$PREFIX/bin/vusted`
- Neovim entry script: `$PREFIX/bin/vusted_entry.vim`

## Runtime

`vusted` expects `nvim` on `PATH`. Conan consumers should also compose
`LUA_PATH` and `LUA_CPATH` across Vusted, Busted, and their Lua dependencies.

## License

MIT

