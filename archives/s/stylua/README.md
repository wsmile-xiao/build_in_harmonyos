# stylua

A code formatter for Lua, written in Rust.

## Features
- Formats Lua code according to configurable style rules
- Supports Lua 5.1, 5.2, 5.3, 5.4, LuaJIT, and Luau
- EditorConfig support
- LSP server mode for IDE integration

## OpenHarmony Compilation Notes
- Build system: Custom (Rust/Cargo)
- No source modifications required for OHOS
- Compiled with: `cargo build --release --no-default-features --features editorconfig,lsp`
- wasm-bindgen feature disabled (not needed for OHOS target)
