# zlib test_package PIC probe

## Error signature

An ordinary executable links and runs, but a downstream shared library later fails with an AArch64 relocation error against zlib symbols.

## Root cause

Executable-only zlib tests do not cover the risky consumer path. A non-PIC static archive can link into an executable while still failing when linked into a shared object.

## Recommended test_package shape

Use two targets:

```cmake
find_package(zlib REQUIRED)

add_executable(test_zlib test.c)
target_link_libraries(test_zlib zlib::zlib)

add_library(zlib_pic_probe SHARED pic_probe.c)
target_link_libraries(zlib_pic_probe zlib::zlib)
```

`test_zlib` should perform a real `compress()` and `uncompress()` round trip. `zlib_pic_probe` only needs to build as a shared library; the link step is the assertion that catches a non-PIC archive.

## Validation evidence

For `zlib/1.3.1.1.1`, shadow CI built both targets:

```text
[ 75%] Linking C shared library libzlib_pic_probe.so
[100%] Linking C executable test_zlib
zlib 1.3.1 OK
```

The CI negative test also moved `lib/` and `include/` away and confirmed the test genuinely depends on the packaged zlib.

## Forbidden shortcuts

Do not use an empty test package or a version-only executable test for this zlib suffix. The package exists to solve DSO linking risk, so the test must exercise that link mode.
