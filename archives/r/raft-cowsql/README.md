# raft-cowsql

Asynchronous C implementation of the Raft consensus protocol, forked by the cowsql project (Canonical). This is the cowsql-specific version of the raft library used by distributed SQL engines.

## Overview
- **Website**: https://github.com/cowsql/raft
- **License**: LGPL-3.0
- **Category**: db / distributed consensus

## Dependencies
- Optional: libuv >= 1.18.0 (for the libuv raft_io implementation)
- Optional: lz4 >= 1.7.1 (for snapshot compression, requires libuv)
- Build tools: autoconf, automake, libtool, pkg-config

## HarmonyOS aarch64 Adaptation

### Key Issues
1. **Bootstrap required**: GitHub tarball doesn't include generated autotools files; must run `autoreconf -i`
2. **HMDFS umask bug**: config.status fails with Permission denied (E011); fix by changing `umask 077` to `umask 022` in configure
3. **config.guess/config.sub**: System autotools already includes ohos support (2023-09-19 version)

### Build Instructions
```bash
autoreconf -i
sed -i 's/umask 077/umask 022/g' configure
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make check
```

### Test Results
All 3 test suites pass on HarmonyOS aarch64 (without libuv).

### Deliverables
- libraft.so.0.0.0 (shared library)
- libraft.a (static library)
- raft.h, raft/fixture.h (headers)
- raft.pc (pkg-config)
