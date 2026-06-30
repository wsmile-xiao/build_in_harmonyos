# mruby

mruby is a lightweight implementation of the Ruby language, written in C. It is designed to be embedded in other applications, providing a compact and efficient Ruby runtime.

## Key Features
- Lightweight Ruby implementation in C
- Minimal memory footprint
- Designed for embedding in other applications
- Supports most Ruby syntax and standard library features
- Includes mrbgems (modular gem system)

## Binaries
- `mruby` - Ruby interpreter
- `mrbc` - Ruby bytecode compiler
- `mirb` - Interactive Ruby (IRB-like REPL)
- `mrdb` - mruby debugger
- `mruby-strip` - Strip debug sections from bytecode
- `mruby-config` - Build configuration helper

## Library
- `libmruby.a` - Static library for embedding mruby
- `libmruby_core.a` - Core library (internal)

## Compiled Versions
| Version | Status | Date |
|---------|--------|------|
| 3.3.0 | published | 2026-05-26 |