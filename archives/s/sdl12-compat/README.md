# sdl12-compat

SDL-1.2 compatibility layer implemented using SDL-2.0 API.

## Description

sdl12-compat is a library that provides the SDL-1.2 API on top of SDL-2.0.
It allows programs that were written against SDL-1.2 to run without modification
using the SDL-2.0 library. This is useful for running legacy SDL-1.2 games and
applications on modern systems.

## Version

- 1.2.68-r1: SDL-1.2 compatibility layer, compiled for OpenHarmony aarch64

## Dependencies

- SDL2 (2.30.0): Required runtime dependency, provides the underlying SDL-2.0 implementation

## Build Configuration

- Build system: CMake
- Configure options: `-DCMAKE_INSTALL_PREFIX=... -DCMAKE_BUILD_TYPE=Release`
- Compiler: clang / clang++

## Key Products

- libSDL-1.2.so: Shared library providing SDL-1.2 API
- libSDLmain.a: Static library for SDL main function wrapping
- SDL header files (include/SDL/): SDL-1.2 compatible headers
- sdl-config: Configuration helper script
- sdl12_compat.pc: pkg-config file
