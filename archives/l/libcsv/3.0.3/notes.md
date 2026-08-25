# libcsv 3.0.3

## Source

libcsv 3.0.3 official SourceForge source archive.

SHA256:

d9c0431cb803ceb9896ce74f683e6e5a0954e96ae1d9e4028d6e0f967bebd7e4

## Build

Autotools build:

./configure
make
make check
make install

The library is implemented in ANSI C and has no external library dependencies.

## Tests

The upstream test program is test_csv.c.

The Conan test_package additionally validates:

- public header consumption
- version macros
- parser initialization
- CSV parsing
- field callback execution
- row callback execution
- parser finalization
- CSV writer quoting
