# Nuklear 4.12.8

## Source

- URL: https://github.com/Immediate-Mode-UI/Nuklear/archive/refs/tags/4.12.8.tar.gz
- SHA256: `2b5d278547cf7f4232d2a48334b8756c3c4533608bf01b2ebc9a4de0063eef08`
- License: MIT OR Unlicense

## Build

Nuklear is a single-header ANSI C library. The package copies `nuklear.h` into
`include/`, installs the upstream license, and exposes the CMake target
`nuklear::nuklear`.

No source patch is required for the OHOS package. Consumers that compile the
implementation define `NK_IMPLEMENTATION` in exactly one translation unit.

## Upstream Tests

The 4.12.8 release archive contains demos and examples, but it does not provide
a formal test directory, CTest target, or standalone unit-test command. No
upstream tests are removed or modified by this package.

## Consumer Test

`test_package/test_nuklear.c` compiles the packaged header with
`NK_IMPLEMENTATION`, links through `find_package(nuklear CONFIG)`, and executes
12 assertions against public Nuklear APIs:

- context initialization and cleanup;
- rectangle and vector helpers;
- color constructors;
- string length helper;
- input begin, scroll, and end flow.

This verifies that the packaged header is consumable and that a downstream C
program can compile and execute Nuklear API calls.

## Validation

```bash
conan create archives/n/nuklear/4.12.8 --build=missing
python -m py_compile archives/n/nuklear/4.12.8/conanfile.py archives/n/nuklear/4.12.8/test_package/conanfile.py
```
