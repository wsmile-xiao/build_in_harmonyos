# par2 (par2cmdline)

## Description

par2cmdline is a PAR 2.0 compatible file verification and repair tool. It uses Reed-Solomon error correction codes to create parity volumes that can be used to repair damaged or missing files.

## Version

0.8.1

## Build Information

- **Build System**: autotools (autoconf/automake)
- **Platform**: OpenHarmony aarch64 (aarch64-unknown-linux-ohos)
- **Compiler**: clang 15.0.4
- **Dependencies**: None (statically linked libstdc++, OpenMP support)
- **Configure Options**: `--prefix=/storage/Users/currentUser/usr/local`

## Installed Binaries

| Binary | Description |
|--------|-------------|
| `par2` | Main binary (create, verify, repair) |
| `par2create` | Symlink to par2 (create mode) |
| `par2verify` | Symlink to par2 (verify mode) |
| `par2repair` | Symlink to par2 (repair mode) |

## Test Results

All 29 tests passed (make check).

## Source

- Upstream: https://github.com/Parchive/par2cmdline
- Tag: v0.8.1
