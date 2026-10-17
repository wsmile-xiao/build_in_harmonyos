# DRAFT: open62541 must guard the glibc-only stdio limit header by libc capability

> Status: Draft | Updated: 2026-09-10
> Source event: `open62541/1.5.6` HarmonyOS PC adaptation

## Symptom

The POSIX event loop fails during an OHOS cross build with:

```text
fatal error: 'bits/stdio_lim.h' file not found
```

The failure comes from `arch/posix/eventloop_posix.h`, where the header is
included for ordinary non-Android/non-Apple platforms.

## Root Cause

The OHOS SDK uses a musl-based libc surface and does not provide the glibc
private header `bits/stdio_lim.h`. The upstream platform test treats OHOS as
generic Linux because the compiler defines Linux-compatible macros, but that
does not make glibc-only headers available.

## Adaptation

Keep the upstream include only for the libc that provides it:

```c
#if defined(__GLIBC__)
# include <bits/stdio_lim.h>
#endif
```

`__GLIBC__` expresses the header capability directly and also covers other
non-glibc libc environments without naming a platform. The guard must stay
local to the header. Do not add a fake `bits/stdio_lim.h`
to the package or copy glibc headers into the OHOS sysroot.

## Verification

The `open62541/1.5.6` Conan recipe applies
`0001-arch-posix-eventloop_posix.h.patch`. The package then builds with the
OHOS CMake toolchain, and its independent C consumer compiles and links as an
AArch64 ELF. The same consumer executes successfully in single-package
HarmonyOS shadow CI.

## Scope

This is a portability fix for the POSIX event-loop header. It does not imply
that every Linux-only open62541 plugin is available on OHOS; each plugin still
 needs an independent sysroot and runtime capability check.
