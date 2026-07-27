# LevelDB

LevelDB is Google's ordered key-value storage library based on an LSM-tree.

## HarmonyOS PC adaptation

- Builds the official shared library with CMake.
- Uses only the platform thread library; there are no third-party Conan
  dependencies.
- Explicitly disables the optional crc32c, Snappy, and tcmalloc probes so host
  libraries cannot become undeclared package dependencies.
- Compiles all 30 POSIX upstream test targets in a separate static build tree.

## Verification

The Conan consumer opens a temporary database and verifies Put, Get,
WriteBatch, Delete, and cleanup behavior. Cross builds compile and link the
consumer and upstream tests without claiming target-side execution. The
resulting AArch64 binaries were also executed on a HarmonyOS PC: all 30
upstream targets and the consumer passed (31/31).

## Reference

- https://github.com/google/leveldb
