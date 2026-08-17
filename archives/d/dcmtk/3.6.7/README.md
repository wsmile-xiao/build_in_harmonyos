# dcmtk 3.6.7

DCMTK is a collection of libraries and applications implementing large parts of the DICOM standard.

## Build

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## Dependencies

All optional dependencies are enabled by default:
- zlib/1.3.1.1
- openssl/3.4.1
- libpng/1.6.58
- libtiff/4.6.0
- libxml2/[>=2.12.5 <3]
- libiconv/1.17

icu is NOT adapted on OHOS and is disabled.

## Patches

4 patches from conan-center-index:
1. CMake robust deps handling (find_package REQUIRED + imported targets)
2. CMake check openssl symbol (check_symbol_exists)
3. C++20 ambiguous overload operator== fix
4. CVE-2024-34508/34509 segmentation fault fix

## OHOS Adaptations

- CMAKE_SYSTEM_NAME=Linux (HarmonyOS is not in CMake's known platform list, so Linux is used as a compatible value)
- DCMTK_NO_TRY_RUN for cross-compilation
- charset_conversion=libiconv (oficonv not available in 3.6.7)
- DCMTK_WITH_ICU=OFF (icu not adapted)

## License

BSD-3-Clause
