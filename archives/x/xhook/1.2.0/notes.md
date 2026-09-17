# xhook 1.2.0 — HarmonyOS PC adaptation notes

## What xhook is

iQIYI's PLT/GOT hook library for Android ELF (pure C, MIT). It walks
`/proc/self/maps`, parses ELF headers/dynamic sections of loaded objects
in memory, and patches GOT entries (PLT relocations) so that calls to a
chosen symbol (e.g. `malloc`) from selected libraries are redirected to a
replacement function. Upstream build is ndk-build only (Android.mk per
module); no CMake/autotools. Public C API: `xhook_register`,
`xhook_ignore`, `xhook_refresh`, `xhook_clear`, `xhook_enable_debug`,
`xhook_enable_sigsegv_protection` (xhook.h).

## Why OHOS needs a port

The hook engine itself (ELF parsing, GOT patching, mprotect, SIGSEGV
protection) is plain POSIX and works unmodified on OHOS musl. Four
Android-isms had to be handled:

1. **android liblog** (`xh_log.{h,c}` + all `XH_LOG_*` macros):
   `<android/log.h>` and `__android_log_print()` do not exist on OHOS.
   Patched: `__OHOS__` branch includes `<hilog/log.h>` and provides a
   compatible `android_LogPriority` enum + `__android_log_print()` that
   forwards to `OH_LOG_Print()` (libhilog_ndk.z.so). HiLog's LogLevel
   (DEBUG=3 INFO=4 WARN=5 ERROR=6 FATAL=7) is numerically identical to
   android_LogPriority, so the priority filtering logic (`xh_log_priority
   <= ANDROID_LOG_DEBUG` etc.) is preserved verbatim — no behavior drift.
2. **JNI bridge** (`xh_jni.c`): registers Java native methods for the
   xhookwrapper Android app (`Java_com_qiyi_xhook_NativeHandler_*`).
   OHOS has no ART/libnativehelper, and `jni.h` is not in the sysroot.
   The file is compiled out under `__OHOS__` (guard, not deletion); the
   C API in xhook.h is what OHOS consumers use.
3. **bionic elf.h extensions** (`xh_elf.c`): `DT_ANDROID_REL`,
   `DT_ANDROID_RELA`, `DT_ANDROID_RELSZ`, `DT_ANDROID_RELASZ` (packed
   relocations, from AOSP's relocation packer) are not in musl's elf.h.
   Locally `#ifndef`-defined with the bionic values so the packed-reloc
   handling compiles and still handles such objects if ever loaded.
   Regular OHOS binaries use RELA/RELR — handled by the untouched
   generic paths.
4. **bionic userspace macros**: `PAGE_MASK` is available to userspace on
   bionic but not musl; derived from `sysconf(_SC_PAGESIZE)` (cached)
   instead of hardcoding 4096. Also `struct sigaction` needs an explicit
   `#include <signal.h>` in `xh_core.c` (bionic's pthread.h pulls it in
   indirectly, musl's does not) and `-D_GNU_SOURCE` with `-std=c11`.

## Build recipe approach

Upstream has no CMake, so the conanfile drives the OHOS clang (from
`tools.build:compiler_executables` profile conf, R33) over the exact
upstream source list (xhook.c xh_core.c xh_elf.c xh_jni.c xh_log.c
xh_util.c xh_version.c) with upstream's own flags
(`-Wall -Wextra -Werror -fvisibility=hidden -std=c11`), links
`-lhilog_ndk.z` and stages `xhook.h` + libxhook itself. Default shared
matching upstream's `BUILD_SHARED_LIBRARY`. hilog_ndk.z declared in
`system_libs` so consumers link it automatically.

## Test strategy (upstream has no test target)

Upstream's only "test" is an Android demo: `libtest` (victim lib calling
`__android_log_print` from a thread), `libbiz` (hook consumer), and the
`xhookwrapper` app. It requires the Android NDK and an app process —
not runnable on OHOS. test_package reproduces the exact functional
scenario natively: `hook_target.c` mirrors libtest (background thread
calling malloc via PLT — OHOS's equivalent always-available PLT symbol),
`hook_main.c` mirrors libbiz (xhook_register + xhook_refresh, asserts
hook fires over time and old_func captures the GOT value). Verified
on-device: hook fires (counters 2→4 over 5s), old_func captures
0x5b541cd72c (real malloc).

Full public API exercised in local verification: register / ignore /
refresh(sync+async) / enable_debug (exercises the HiLog bridge) /
enable_sigsegv_protection / clear — all return 0.

## Known behavior notes (upstream design, not port defects)

- `old_func` is only written when the hook actually hits a GOT entry in
  `.rel[a].plt`; for targets whose imports live in `.rel[a].dyn`
  (BIND_NOW/RELRO libc-style) upstream deliberately passes NULL (see
  xh_elf.c hook loop) — same behavior on Android.
- Hooking in libc.so itself does not redirect calls already bound via
  RELRO; hooking a non-RELRO consumer library (the documented use case:
  your own or third-party .so) works, as the test proves.

## pitfalls for future consumers

- `-std=c11` alone hides `struct sigaction` on musl: keep
  `-D_GNU_SOURCE` (already in the recipe's cflags).
- The compat enum in xh_log.h redefines `android_LogPriority` only when
  `__OHOS__` is defined, so the same tree still builds on Android NDK.
