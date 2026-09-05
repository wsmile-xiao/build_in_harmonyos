# pkgconf

pkgconf is a program and library for resolving pkg-config metadata. The
`pkgconf/3.0.6` Conan package installs a static `libpkgconf` library together
with the `pkgconf`, `bomtool`, `spdxtool`, and `pccritic` command-line tools.

## Package contents

- `lib/libpkgconf.a`
- `include/pkgconf/libpkgconf/{libpkgconf.h,stdinc.h,iter.h,bsdstubs.h,libpkgconf-api.h}`
- `lib/pkgconfig/libpkgconf.pc`
- `share/aclocal/pkg.m4`
- `bin/pkgconf`
- `bin/bomtool`
- `bin/spdxtool`
- `bin/pccritic`

Upstream 3.0.6 does not install a `pkg-config` alias. Consumers that need the
traditional command name should select it explicitly in their own environment;
this package does not create an unowned alias.

## Conan usage

Link the library through the generated CMake target:

```cmake
find_package(pkgconf CONFIG REQUIRED)
target_link_libraries(my_target PRIVATE pkgconf::pkgconf)
```

The four installed programs are available from the package `bin` directory.
