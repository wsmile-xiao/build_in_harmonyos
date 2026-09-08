# vpnc 0.5.3 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

vpnc uses a plain Makefile (no configure script). Build is driven by Conan:

1. `conan create` downloads the source tarball from upstream
2. AutotoolsToolchain generates conanbuild environment (CC, CFLAGS, LDFLAGS, CPPFLAGS)
3. Source patches applied via `replace_in_file()` in `build()` method (see below)
4. `make -j1 CC=<clang> BINS="vpnc cisco-decrypt" vpnc cisco-decrypt` builds both binaries
5. Manual `copy()` installs binaries to package folder (sbin/ and bin/)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `<error.h>` not found | OHOS defines `__linux__` but doesn't ship glibc's `<error.h>` | Split `#if defined(__linux__) \|\| defined(__GLIBC__)` in sysdep.h: glibc keeps `#include <error.h>` + `HAVE_ERROR`; non-glibc Linux defines other `HAVE_*` macros but NOT `HAVE_ERROR`, so vpnc's own `error()` fallback in sysdep.c is used |
| 2 | `struct ethhdr` redefinition | Both `linux/if_ether.h` (via `linux/if_tun.h`) and `netinet/if_ether.h` define `struct ethhdr` | Add `#define __UAPI_DEF_ETHHDR 0` before `#include <linux/if_tun.h>` in sysdep.c |
| 3 | `getpass()` not available | OHOS doesn't provide `getpass()` | Add `getpass()` implementation in sysdep.c (using termios) and forward declaration in sysdep.h |
| 4 | Missing library link flags | Makefile uses `libgcrypt-config --libs` which isn't shipped in Conan package | Explicitly add `-l{lib}` for each dependency library to `tc.extra_ldflags` in `generate()` |
| 5 | `makeman.pl` not found | Default `all` Makefile target builds man page requiring `makeman.pl` | Pass explicit targets `vpnc cisco-decrypt` on make command line |
| 6 | `ETH_ALEN` macro fails | `sizeof(struct ether_addr)` fails on OHOS | Define `ETH_ALEN` as constant 6 on non-glibc Linux |
| 7 | test_package LD_LIBRARY_PATH | conanrun env didn't set up library paths | Use `generators = "VirtualRunEnv"` in test_package/conanfile.py |

## 依赖版本

- libgcrypt/1.12.2 (which depends on libgpg-error/1.55)

## 验证结果

```bash
# Test: vpnc --version
vpnc --version
# Expected: "vpnc version 0.5.3"

# Test: cisco-decrypt with known test vector
cisco-decrypt 0038554D5A0C515739
# Expected: "test123"
```

## 注意事项

- vpnc requires TUN/TAP device support at runtime; the binary builds fine without it
- The --version flag may print to stderr; test should handle this
- cisco-decrypt is a separate utility for decrypting Cisco VPN .pcf file passwords
- Source URL is from the official upstream at unix-ag.uni-kl.de
- All source patches are applied inline via `replace_in_file()` in `build()`, not via patch files
- The `make` command uses explicit targets `vpnc cisco-decrypt` to skip man page generation
