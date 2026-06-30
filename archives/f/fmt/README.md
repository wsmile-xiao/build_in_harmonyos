# fmt

**Description**: {fmt} is an open-source formatting library providing a fast and safe alternative to C stdio and C++ iostreams.

**Website**: https://fmt.dev

**GitHub**: https://github.com/fmtlib/fmt

## Compiled Versions

- **11.2.0-r1** (2026-05-19)
  - Build System: CMake
  - Compiler: Clang 15.0.4
  - Status: built
  - Notes: One test failure (file_test.line_buffering) due to platform-specific behavior

## Features

- Fast formatting library for C++
- Safe alternative to printf and iostreams
- Support for positional arguments
- Compile-time format string checking
- Custom format specifiers
- Wide string support

## Dependencies

No external dependencies required.

## Build Configuration

```cmake
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release
```

## Notes

- This is a header-only or static library (libfmt.a)
- Compatible with C++14 and above
- Used by many modern C++ projects for string formatting