# Test Report — libax25 0.0.12-rc5

## Build Test
- **Configure**: Success (autoreconf + configure with OHOS patches)
- **Make**: Success (libax25.a, libax25.so, libax25io.a, libax25io.so)
- **Make install**: Success (DESTDIR=$TEST_PREFIX)
- **Make check**: Success (exit 0, no test targets)

## Functional Test (readelf -d)
- **libax25.so**: SONAME=libax25.so.0, NEEDED=libc.so
- **libax25io.so**: SONAME=libax25io.so.0, NEEDED=libc.so
- **libax25.a**: Static library, symbols verified (ax25_aton_entry, ax25_ntoa, ax25_validate)

## Conan Test Package (L1)
- **Build**: Success (CMake + clang)
- **Link**: Success (linked against libax25::libax25)
- **Test execution**: PASS (100% tests passed)
  - ax25_aton_entry("VK2ABC-5") -> OK
  - ax25_ntoa() -> "VK2ABC-5"
  - ax25_validate(network) -> TRUE

## Source Modifications
1. config.guess: Replaced with OHOS-aware stub (E007)
2. config.sub: Replaced with pass-through stub (E007)
3. configure: umask 077 -> 0000 (HMDFS compatibility)
4. config.status: umask 077 -> 0000
5. libtool: umask 0077 -> 0000
6. Shebangs: #!/bin/sh -> #!/system/bin/sh (E165)
