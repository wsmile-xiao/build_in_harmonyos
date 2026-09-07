# mpdecimal — General Decimal Arithmetic Library

## Description
mpdecimal is a C/C++ library for decimal floating point arithmetic, implementing
the General Decimal Arithmetic Specification (IEEE 754-2008). It is the reference
implementation behind Python's `decimal` module.

Homepage: https://www.bytereef.org/mpdecimal/

## Versions
- 2.5.1 (published, conan recipe) — CPython 3.9-3.11 builtin version
- 4.0.1 (published, legacy package flow)

## Features
- C library (`libmpdec`) for decimal arithmetic
- C++ library (`libmpdec++`) for decimal arithmetic
- Static and shared libraries
- Thread-safe operations
- `__uint128_t` support on 64-bit

## License
BSD-2-Clause

## Dependencies
- None (only requires `-lm` math library)
