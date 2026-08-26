# rocksdb7 7.9.2

High-performance embedded key-value store for fast storage, developed by Meta.

- **Homepage**: https://rocksdb.org/
- **License**: Apache-2.0
- **Build system**: CMake
- **Source**: https://github.com/facebook/rocksdb (tag v7.9.2)

## OHOS Adaptation

### Patches
- `0001-CMakeLists.txt-harmonyos-platform.patch`: HarmonyOS platform detection + musl header force-include
- `0002-env-fs_posix.cc-ohos.patch`: `__OHOS__` guard for `sys/statfs.h` and `sys/sysmacros.h`
- `0003-env-io_posix.cc-ohos.patch`: `__OHOS__` guard for `sys/statfs.h` and `sys/sysmacros.h`

### Dependencies
zlib, snappy, lz4, zstd, bzip2, gflags (all optional at build time, all enabled).

### Build Options
Tests disabled (`-DWITH_TESTS=OFF`), tools disabled, benchmarks disabled, `FAIL_ON_WARNINGS=OFF`.
