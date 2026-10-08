# lss — Linux Syscall Support

Linux Syscall Support (lss) provides C language wrappers for making
direct Linux system calls, without relying on the libc wrappers. The
main artifact is the single header file `linux_syscall_support.h`.

## Usage

```c
#include "linux_syscall_support.h"

long pid = sys_getpid();
```

## Build

Header-only library — no build step required. The package provides
`linux_syscall_support.h` in the `include/` directory.

## Upstream

- Repository: https://chromium.googlesource.com/linux-syscall-support
- License: BSD-3-Clause (Chromium project)
- Used by: crashpad, breakpad
