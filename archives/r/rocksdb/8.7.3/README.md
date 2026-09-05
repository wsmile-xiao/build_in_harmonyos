# rocksdb 8.7.3

High-performance embedded key-value store for fast storage, developed by Meta.

- **Homepage**: https://rocksdb.org/
- **License**: Apache-2.0
- **Build system**: CMake
- **Source**: https://github.com/facebook/rocksdb (tag v8.7.3)

## OHOS Adaptation

### Patches
- `0001-CMakeLists.txt-harmonyos-platform.patch`: Add HarmonyOS platform detection.
  `CMAKE_SYSTEM_NAME` is `HarmonyOS` on OpenHarmony, not `Linux`, so `OS_LINUX` was
  undefined. Adding a HarmonyOS branch defines `OS_LINUX`, which satisfies the
  `#if defined(OS_LINUX)` include guards in `env/fs_posix.cc` and `env/io_posix.cc`.

### Dependencies
zlib, snappy, lz4, bzip2 (static). zstd and gflags are **excluded**: on the ohpcd
repo they only ship as shared libraries, and the OHOS container dynamic loader
rejects loading user-writable-path shared libs (`dlopen` returns Permission denied),
which blocks local `test_package` validation. The remaining static compression
libraries keep RocksDB's compression functionality intact.

### Build Options
Tests disabled (`-DWITH_TESTS=OFF`), tools disabled, benchmarks disabled,
`FAIL_ON_WARNINGS=OFF`, `PORTABLE=ON`. Built with Ninja generator.
