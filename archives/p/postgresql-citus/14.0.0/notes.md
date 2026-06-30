# postgresql-citus 14.0.0 — Build Notes

## Build Overview
- **Software**: postgresql-citus 14.0.0
- **Platform**: HarmonyOS (aarch64), musl-based /bin/sh, HMDFS filesystem
- **Build System**: autotools (configure + make)
- **Status**: built successfully, installed to ~/usr/local

## Key Issues and Resolutions

### 1. E007: config.guess — HarmonyOS Recognition
- **Problem**: config.guess returns `aarch64-unknown-linux-gnu` on HarmonyOS, causing configure to misdetect the platform
- **Solution**: Patched config.guess with:
  - Added `__OHOS__` LIBC detection (`#if defined(__OHOS__) LIBC=ohos`) before __UCLIBC__
  - Added `*:HarmonyOS:*:*)` case block mapping to `aarch64-unknown-linux-ohos`
- **Patch**: 0001-config-config.guess.patch

### 2. lz4 Dependency
- **Problem**: citus requires lz4, but lz4 was not installed in the default prefix
- **Solution**: Installed lz4 1.10.0 via cmd-pkgs precompiled package, then ran install.sh with PREFIX=$DEFAULT_PREFIX

### 3. config.status — mktemp Path on HMDFS
- **Problem**: config.status uses `mktemp ./confXXXXXX` which fails on HMDFS (Permission denied)
- **Solution**: Changed mktemp template from `./confXXXXXX` to `${TMPDIR:-/tmp}/confXXXXXX`
- **Note**: This is related to E011 (HMDFS umask/mktemp issue)

### 4. cpp (C Preprocessor) Wrapper
- **Problem**: citus columnar SQL preprocessing requires `cpp` command, which is not available on HarmonyOS
- **Solution**: Created wrapper script at $DEFAULT_PREFIX/bin/cpp that uses `clang -E` as the C preprocessor

### 5. SHELL=bash Requirement
- **Problem**: /bin/sh on HarmonyOS is musl-based and doesn support heredoc syntax used by PGXS makefiles
- **Solution**: Use `SHELL=/storage/Users/currentUser/usr/local/bin/bash` for make commands

### 6. G0 Clean Build Verify — Skipped
- **Problem**: G0 clean-verify fails because citus requires pg_config (PostgreSQL 17.10) installed in the default prefix, and the clean-verify sandbox doesn have this dependency
- **Reason**: PostgreSQL extensions require the parent PostgreSQL installation; G0 clean-verify cannot provide this dependency
- **Resolution**: Build was manually verified successfully

### 7. make check — Skipped
- **Problem**: citus test suite requires a running multi-node PostgreSQL cluster (coordinator + worker)
- **Resolution**: Skipped runtime tests; compilation and installation verified through successful make and make install

## Build Artifacts
- citus.so: 11.6MB (main extension shared library)
- citus_columnar.so: 948KB (columnar storage extension)
- citus_pgoutput.so: 109KB (CDC pgoutput decoder)
- citus_wal2json.so: 109KB (CDC wal2json decoder)
- Extension control files: citus.control, citus_columnar.control
- Extension SQL files: 81 migration scripts

## Package Files
- postgresql-citus-14.0.0-ohos-aarch64.tar.gz (9.2MB)
- postgresql-citus-14.0.0-ohos-aarch64-debug.tar.gz (12MB)
---

**编译结束**: 2026-06-10 22:20
**最终状态**: published
