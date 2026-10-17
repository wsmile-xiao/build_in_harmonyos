# Draft: BSD sys/sysctl.h missing on OHOS → __APPLE__ include guard

> Source event: `chipmunk2d/7.0.3` OHOS adaptation on 2026-09-03.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

Chipmunk2D 7.0.3 compiles `src/cpHastySpace.c` on OHOS with:

```text
/storage/.../src/cpHastySpace.c:11:10: fatal error: 'sys/sysctl.h' file not found
```

`sys/sysctl.h` is a BSD/macOS-specific header. OHOS uses musl libc and does not
ship it. The file includes it unconditionally for all non-`_WIN32` targets:

```c
#ifndef _WIN32
#include <sys/sysctl.h>   /* ← missing on OHOS/Linux-musl */
#include <pthread.h>
#else
...
#endif
```

while the only consumer of that header, `sysctlbyname("hw.ncpu", ...)`, sits
inside an `#ifdef __APPLE__` block:

```c
#ifdef __APPLE__
    if(threads == 0){
        size_t size = sizeof(threads);
        sysctlbyname("hw.ncpu", &threads, &size, NULL, 0);
    }
#else
    if(threads == 0) threads = 1;
#endif
```

So the include scope (unconditional) is wider than the call scope (Apple only).
On OHOS the header is included but never used, and the include itself fails.

## Root cause

Include-scope/platform scope asymmetry: an unconditional include of a BSD-only
header whose only call site is Apple-only. musl-based platforms (OHOS, and also
glibc-free Linux variants) do not provide `sys/sysctl.h` at all.

## Fix

Converge the include into the same `__APPLE__` guard as its only call site:

```c
#ifndef _WIN32
#ifdef __APPLE__
#include <sys/sysctl.h>
#endif
#include <pthread.h>
#else
...
#endif
```

No replacement implementation is needed on OHOS because the guarded branch is
unreachable there (`threads = 1` fallback already exists).

## Verification

`conan create archives/c/chipmunk2d/7.0.3 -pr:h=ci/conan/profiles/ohos-aarch64`
succeeded after the patch; W3 local CI Pass rate 100% (1/1); test_package
consumer test (cpSpace/cpBody/cpShape, 60-step gravity simulation) passed.

## Applicability boundary

Applies when a non-`_WIN32` source unconditionally includes a BSD/macOS-only
header but only uses it under `__APPLE__`. If the capability is actually needed
on the target platform, use the `__OHOS__` guard pattern (cf. E086) or provide
a musl-compatible implementation instead; do not leave the unconditional include.

## Counter-examples / limits

- If `sysctl`/`sysctlbyname` is called on Linux too (e.g. glibc's deprecated
  `sysctl(2)`), the guard must be broader; on musl neither exists.
- If the header is needed for types/macros used elsewhere on Linux, guard and
  region must be scoped precisely; do not blanket-remove the include.

## Similar entries

- E086 (`struct ucred` missing on OHOS → `__OHOS__` guard)
- E102 (exclude OHOS from `__linux__` conditionals for musl-absent APIs)