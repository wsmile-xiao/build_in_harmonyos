# InChI

InChI is the IUPAC International Chemical Identifier implementation. The
`inchi/1.07.5` Conan package provides the C API as a shared OHOS library.

## Package contents

- `lib/libinchi.so`
- `include/inchi_api.h`
- `include/ixa.h`
- `lib/pkgconfig/inchi.pc`

## Conan usage

```cmake
find_package(inchi CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE inchi::inchi)
```

The recipe builds the upstream API library and its complete seven-program unit
test inventory. It disables the unrelated command-line programs and replaces
the upstream test-only network fetch with `gtest/1.17.0` from the Conan
dependency graph.
