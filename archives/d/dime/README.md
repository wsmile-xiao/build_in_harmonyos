# dime

`dime` ("DXF Import, Manipulation and Export") is a portable C++ class library
for reading, constructing, manipulating, and writing DXF (Drawing eXchange
Format) files, from the Coin3D / Kongsberg family.

## OpenHarmony adaptation

- Upstream: https://github.com/coin3d/dime (BSD-3-Clause)
- Version 0.20111205 is the 2011-12-05 upstream snapshot (Mercurial r187);
  the source URL pins the equivalent git commit `edcbe949ae67`, byte-identical
  to the Debian `dime_0.20111205.orig` tarball (see 0.20111205/notes.md).
- Build system: Autotools (pre-generated configure, libtool 1.5 era)
- Zero external dependencies (libc/libm only)
- Library-only package: `libdime` + `include/dime` + `dime.pc`; the
  `dxf2vrml`/`dxfsphere` example programs are noinst and not installed
- Consumer smoke test: build a model, write a DXF file, read it back, and
  verify the entity round-trips (test_package/test.cpp)
