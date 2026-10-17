# Packaging — nettle 4.0

This package uses Conan for packaging. No manual tar.gz packaging needed.
The `conan create` command handles source compilation, packaging, and testing.

## Conan Package
- Recipe: conanfile.py
- Profile: ohos-aarch64
- Channel: ohpcd/stable
- Dependencies: gmp/6.3.0
- Libraries: libnettle.a, libhogweed.a
