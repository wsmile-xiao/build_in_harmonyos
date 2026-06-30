# Apache Thrift

**Apache Thrift - Cross-language serialization framework**

## Description

Apache Thrift is a software framework for scalable cross-language services development.
It combines a software stack with a code generation engine to build services that work
efficiently and seamlessly between C++, Java, Python, PHP, Ruby, Erlang, Perl, Haskell,
C#, Cocoa, JavaScript, Node.js, Smalltalk, OCaml, Delphi, and other languages.

## Homepage

- https://thrift.apache.org/

## Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.23.0 | built | 2026-05-28 | CMake build, requires Boost |

## Dependencies

- flex >= 2.6.4
- bison >= 3.8.2
- boost >= 1.84.0

## Build System

- CMake (recommended for OpenHarmony)
- Autotools (not recommended)

## Key Components

- `thrift` - Thrift compiler (IDL to code generator)
- `libthrift` - C++ runtime library
- Thrift headers for C++, Python, Java, etc.

## Usage Example

```bash
# Generate C++ code from .thrift file
thrift --gen cpp service.thrift

# Compile generated C++ code
g++ -c gen-cpp/service_types.cpp -lthrift
```

## OpenHarmony Specific Notes

- Use CMake build (BUILD_TESTING=OFF)
- Disable Python/Java/NodeJS bindings (-DWITH_PYTHON=OFF, etc.)
- Requires Boost 1.84.0 (precompiled package available)