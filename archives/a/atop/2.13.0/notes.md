# atop 2.13.0 — Adaptation Notes

## Software Info
- **Name**: atop
- **Version**: 2.13.0
- **Description**: System and process monitor for Linux — interactive CPU/memory/disk/network monitoring
- **Upstream**: https://github.com/Atoptool/atop
- **License**: GPL-2.0
- **Language**: C
- **Build system**: Makefile (not CMake/autotools)
- **Type**: CLI tool (atop, atopsar, atopacctd, atopconvert, atopcat, atophide)

## Dependencies
- glib/2.88.0.1 (via pkg-config for glib-2.0 cflags/libs)
- ncurses/6.6 (libncursesw for wide-char terminal support)
- zlib/1.3.1.1.1.1 (transitive from glib, directly linked via -lz)

## Adaptation Changes

### 1. linux/socket.h sockaddr_storage redefinition (ifprop.c, netlink.c)
**Problem**: OHOS sysroot has both `sys/socket.h` and `linux/socket.h` defining `struct sockaddr_storage` without proper guards. The atop source includes `<sys/socket.h>` then later includes `<linux/if.h>` / `<linux/wireless.h>` / `<linux/genetlink.h>` which pull in `<linux/socket.h>`, causing a redefinition error.

**Fix in ifprop.c**:
- Replaced `<linux/if.h>` with `<net/if.h>` (userspace header, provides `struct ifreq`)
- Replaced `<linux/in.h>` with `<netinet/in.h>` (userspace header, provides `struct sockaddr_in`)
- Added `<linux/types.h>` for `__u64`/`__u32`/`__u16`/`__u8` types (previously from `linux/if.h`)
- Added `#define _UAPI_LINUX_SOCKET_H` and `#define _UAPI_LINUX_IF_H` before `<linux/wireless.h>` to prevent it from re-including the conflicting headers

**Fix in netlink.c**:
- Added `typedef unsigned short __kernel_sa_family_t` (the only symbol `linux/netlink.h` needs from `linux/socket.h`)
- Added `#define _UAPI_LINUX_SOCKET_H` before `<linux/genetlink.h>` to prevent re-inclusion

### 2. qsort_r not available on HarmonyOS (new file: qsort_r_compat.c)
**Problem**: HarmonyOS (musl-based) libc does not export `qsort_r`, which atop uses in `showgeneric.c` and `atopsar.c` for sorting process lists with a context argument.

**Fix**: Created `qsort_r_compat.c` — a non-thread-safe wrapper around `qsort` using static storage for the comparator argument. atop is single-threaded so this is safe. Added `qsort_r_compat.o` to `ALLMODS` in the Makefile.

### 3. ncurses and zlib paths
**Problem**: The Makefile hardcodes `-lncursesw -lz` in link commands without specifying search paths. On OHOS, these libraries are managed by Conan, not installed in system paths.

**Fix**: In the conanfile.py `build()` method, pass ncurses and zlib include/lib paths via `CFLAGS` and `LDFLAGS` to make. The Makefile uses `override CFLAGS := ... $(CFLAGS)` and `override LDFLAGS := ... $(LDFLAGS)` which appends our flags.

## Build Command
```
make CC=clang CFLAGS="<ncurses_inc> <zlib_inc>" LDFLAGS="<ncurses_lib> <zlib_lib>" -j1
```

## Warnings (non-blocking)
- `qsort_r` implicit declaration warnings resolved by compat shim
- `waddwstr` implicit declaration (ncurses wide-char, non-blocking)
- `format` type mismatch in various.c (non-blocking)

## Verification
- `atop -V` outputs "Version: 2.13.0"
- `atopconvert -h`, `atopcat -h`, `atophide -h` all show usage
- All 6 binaries (atop, atopsar, atopacctd, atopconvert, atopcat, atophide) compile and link successfully
---

**编译结束**: 2026-08-28 15:10
**最终状态**: built
