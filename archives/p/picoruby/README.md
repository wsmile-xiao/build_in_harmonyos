# picoruby

PicoRuby - Smallest Ruby implementation for microcontrollers.

## Description

PicoRuby is an alternative mruby implementation designed for microcontrollers
with small memory footprint:
- ROM: 256 KB
- RAM: 128 KB or less
- Portable: depends only on standard C library

## Binaries

- `picoruby` - Ruby interpreter
- `picorbc` - Ruby bytecode compiler (.rb → .mrb)
- `picoirb` - Interactive REPL

## Build System

Uses mruby's Rake-based build system (not autotools/cmake).
Requires Ruby interpreter and git for building.

## Dependencies

- Ruby (CRuby) - for running build scripts
- git - for cloning gem dependencies from GitHub

## Available Versions

- 3.0.2 (published)
