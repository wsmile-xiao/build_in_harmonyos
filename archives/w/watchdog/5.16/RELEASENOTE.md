# watchdog 5.16 - OpenHarmony Release Notes

**Release Date**: 2026-04-28
**Build System**: autotools
**Target Platform**: OHOS aarch64

## Package Contents

This package contains:
- `watchdog` - System watchdog daemon (84KB)
- `wd_keepalive` - Keepalive daemon (47KB)
- `wd_identify` - Watchdog identifier (39KB)
- Man pages (watchdog.8, wd_keepalive.8, wd_identify.8, watchdog.conf.5)

## Installation

```bash
tar -xzf watchdog-5.16-ohos-aarch64.tar.gz
cd watchdog-5.16-ohos-aarch64
./install.sh
```

This will install binaries to `/storage/Users/currentUser/usr/local/sbin/`
and man pages to `/storage/Users/currentUser/usr/local/share/man/`.

## Build Notes

### Compilation
- Compiled with clang (LLVM) on OHOS aarch64
- Configure options: `--prefix=/storage/Users/currentUser/usr/local`
- Build: `make -j$(nproc)` - successful

### Known Issues (OHOS Platform)
1. **shutdown.c warnings**: `quotactl()` and `reboot()` functions are not declared
   - These are Linux-specific syscalls not available in OHOS
   - Does not affect compilation, but runtime reboot functionality may be limited
   
2. **HMDFS temp file issue**: config.status fails to create temp files in current directory
   - Fixed with TMPDIR workaround during build
   - Not an issue for end users

### Testing
- No automated test suite (`make check` returns nothing)
- Manual verification: `watchdog` executable runs and shows version 5.16

## Dependencies
- No external library dependencies (standalone C application)
- Requires: `/dev/watchdog` device for hardware watchdog functionality

## License
GPL-2.0-or-later (see COPYING file in source)

## Source
https://downloads.sourceforge.net/project/watchdog/watchdog/5.16/watchdog-5.16.tar.gz