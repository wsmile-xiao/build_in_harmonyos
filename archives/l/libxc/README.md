# libxc

Libxc is a library of exchange-correlation functionals for density-functional
theory. This archive builds the C and Fortran 2003 interfaces as static
libraries for OpenHarmony PC.

The `7.1.2` package enables derivative order 3 so downstream scientific
software can use the KXC interfaces. It exports separate `Libxc::xc` and
`Libxc::xcf03` Conan CMake targets; the Fortran target depends on the C target.

- Homepage: https://libxc.gitlab.io/
- Source: https://gitlab.com/libxc/libxc
- License: MPL-2.0

## OpenHarmony PC adaptation

- Builds static C and Fortran 2003 libraries with derivative order 3.
- Removes the installed 'xc-info' command so the package remains library-only.
- Uses one complete OHOS SDK for the target sysroot and Clang resource files.
- Requires `find_package(Libxc COMPONENTS Fortran)` after enabling Fortran when
  consuming the compiler-specific module files; C-only consumers remain
  independent of the Fortran ABI.

## Dependencies

- Build tool: `flang-ohos/20.1.0`; Fortran consumers must declare the same
  tool requirement and use CMake 3.24 or newer.
- System link dependency: `libm`, exported by the C component.
