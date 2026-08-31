# libwapcaplet

String internment library for the NetSurf browser project.

## Description
libwapcaplet provides efficient string internment (also called string internalisation or string pooling). It allows strings to be stored and compared efficiently by using a hash table that maps string data to unique lwc_string pointers.

## Version
- Current: 0.4.3.1

## License
MIT

## Dependencies
None

## Build System
Originally uses NetSurf's own build system (netsurf-buildsystem). On HarmonyOS/OpenHarmony, replaced with a standalone Makefile.

## Precompiled Package
Available as `libwapcaplet-0.4.3.1-ohos-aarch64.tar.gz` containing:
- `lib/libwapcaplet.a` — static library
- `lib/pkgconfig/libwapcaplet.pc` — pkg-config file
- `include/libwapcaplet/libwapcaplet.h` — header file
