# libpthread-stubs

Meta package for pthread symbols - provides lightweight stubs for pthread functions when the C runtime does not provide them.

## Description

libpthread-stubs is a meta package that provides pkg-config information for pthread symbols. On platforms where the C runtime provides all pthread functions (like OpenHarmony), this package installs an empty pkg-config file with no additional Cflags or Libs.

## Version

- 0.4 (current)

## Dependencies

None - this is a meta package with no actual library code.

## Build Status

- Version 0.4: ✅ built (pkg-config file installed)
- Build system: autotools
- Configure issue: HMDFS file system prevents config.status from creating temporary files; manually generated Makefile and pthread-stubs.pc

## Notes

On OpenHarmony, all pthread functions are provided by the system, so PKG_CONFIG_CFLAGS and PKG_CONFIG_LIBS are empty.