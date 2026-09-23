# mars 1.3.0 — HarmonyOS PC adaptation notes

## What mars is

Tencent's cross-platform infrastructure library behind WeChat: STN
(signal transmission network), Comm (shared components), Xlog
(high-performance logging), SDT (network diagnostics) plus a bundled
boost 1.60 subset. Upstream: https://github.com/Tencent/mars, tag v1.3.0
(2019, the last tagged release).

## Scope of this port

**Comm + Xlog core** (`libmars-comm.a`, `libmars-xlog.a`,
`libmars-boost.a`), per platform guidance (core Comm+Xlog first). STN/SDT
are *consumer-level* on OHOS: they require the embedding app to register
task callbacks (longlink_packer/shortlink_packer, MakesureAuthed,
Buf2Resp...) and provide a live netinfo source — that bridge is what
upstream ships as Android JNI wrappers (mars_android_sdk). A static
`libmars-comm` + `libmars-xlog` is the reusable base every such consumer
builds on.

## Why OHOS needs a port

1. **Upstream build tree is platform-wrapper-only.** mars/CMakeLists.txt
   has exactly MSVC / ANDROID(=shared .so for the Java SDK) / APPLE
   branches; there is no headless Linux/OHOS target (the `elseif(UNIX)`
   flags exist but no target consumes them at top level). The recipe
   therefore drives OHOS clang directly over the *exact* source lists the
   per-module CMakeLists glob for a non-MSVC, non-Android platform
   (verified file-by-file against comm/log/boost CMakeLists.txt).

2. **musl has no pthread_cancel()** (OHOS libc). `Thread::unsafe_exit()`
   non-Android branch calls it. Patch: extend the ANDROID branch guard to
   `defined(ANDROID) || (defined(__linux__) && !defined(__GLIBC__))` — a
   libc-capability condition, not a platform macro (bionic and musl both
   lack pthread_cancel; glibc keeps the plain path). The branch mirrors
   the upstream ANDROID code exactly: installs a SIGUSR2 handler calling
   `pthread_exit(0)` (without it the signal's default disposition would
   kill the whole process), then delivers SIGUSR2 to the target thread
   (the method is unused by mars core itself, grep-verified).

3. **musl has no sys/sysctl.h.** `debugger_utils.c` BSD sysctl debugger
   probe fails to compile. Patch: `__has_include(<sys/sysctl.h>)`
   feature detection (standard C, no platform macro) — glibc/musl fall
   back to reading `/proc/self/status` `TracerPid` (the Linux-standard
   debugger-attach indicator, same semantics as BSD `P_TRACED`); BSD
   systems keep the original sysctl probe unchanged.

4. **Platform abstraction layer was JNI-only.** Upstream provides
   getNetInfo/getCurWifiInfo/getCurSIMInfo/getAPNInfo/getProxyInfo/
   isNetworkConnected/ConsoleLog via comm/jni/platform_comm.cc (Java
   callbacks) or objc/platform_comm.mm. New file `comm/ohos/
   platform_comm_ohos.cc`:
   - `getNetInfo()` → UDP-probe `local_ipstack_detect()` (the same
     connect-a-UDP-socket technique comm already uses for AI_ADDRCONFIG
     detection) — reports kOtherNet when any IP stack is up, kNoNet
     otherwise;
   - WiFi/SIM/APN queries → false (no cellular radio / no native Wi-Fi
     query on a PC);
   - `ConsoleLog()` → fprintf(stderr) with level prefix, matching
     upstream semantics (console sink as an *output* of the xlogger
     pipeline — Android writes logcat, Windows the debug console; feeding
     back into xlogger_Write would recurse into the appender).

5. **xlogger pid/tid source.** Upstream: Android jni/xlogger_threadinfo.cc
   or objc/xlogger_threadinfo.mm. New file
   `comm/ohos/xlogger_threadinfo_ohos.cc` — musl `gettid()` is only
   declared under `_GNU_SOURCE`, which the recipe enables build-wide.

6. **AI review fixes** (both rounds, all findings accepted):
   - round 2 (R8): `__OHOS__` platform-macro branches eliminated —
     sysctl probe now `__has_include`-detected (TracerPid fallback),
     `unsafe_exit` now guarded by `__linux__ && !__GLIBC__` (libc
     capability: bionic/musl lack pthread_cancel, glibc keeps it);
   - round 1: debugger probe TracerPid fallback instead of a stub;
     ConsoleLog stderr sink instead of feeding back into the xlogger
     pipeline (recursion risk); unsafe_exit full SIGUSR2-handler parity
     (default disposition would terminate the process); test switched
     from printf-style `xinfo2("... %_", 1)` to the TSF form (legal
     placeholder scope).

6. **zlib for xlog.** `log_buffer.cc` deflates log payloads; zlib/1.3.1
   from the ohpcd registry (W0/R35 verified with conan install). No
   libcurl: the optional curl extras are not part of the upstream default
   static-lib build.

## Build recipe approach

conanfile.py `build()` reads the compiler from
`tools.build:compiler_executables` (R33), compiles the three source sets
(comm / xlog / boost — the boost set is the exact fixed list from
upstream boost/CMakeLists.txt non-ANDROID branch) with upstream's own
flags (`-fno-exceptions`, gnu++14, `-DXLOGGER_TAG="mars::..."` as a
*quoted string literal* exactly like upstream CMakeUtils
`add_definitions`), archives with llvm-ar. Headers are staged under
`include/mars/{comm,log,boost}` so consumers write
`#include "mars/comm/autobuffer.h"` / `#include "mars/log/appender.h"`.

Static-only (default_options shared=False): matches upstream
`add_library(... STATIC ...)` for comm/xlog/boost, and avoids RPATH
issues on OHOS.

## Test strategy (upstream has no test target)

No add_test/enable_testing anywhere on the v1.3.0 tag; samples/ are
Android/iOS apps; stn/test_cases/*.cc are not registered by any build
target and need WeChat-internal callbacks + live test servers.
test_package reproduces the functional scenario every mars consumer runs
at startup (WeChat's own wrapper included):

- xlog end-to-end: appender_open → xlogger_SetLevel(Debug) →
  xinfo2/xwarn2 (TSF type-safe format + printf style) + xdebug2 →
  appender_flush_sync → appender_close → re-open +
  appender_get_current_log_path → assert file exists non-empty on disk.
- comm primitives STN is built on: AutoBuffer write/roundtrip
  (byte-identical), strutil::Tokenizer split, gettickcount() monotonic
  across a 50ms sleep.

5/5 PASS on-device (OHOS PC runtime, aarch64 musl + libc++_shared from
/system/lib64).

## Known behavior notes (upstream design, not port defects)

- `Alarm` on non-Android falls back to MessageQueue timing only (no
  /dev/alarm ioctl) — upstream design; the OHOS path keeps it.
- `ANR_CHECK_DISABLE` is auto-defined for non-Android-non-Apple (upstream
  guard in anr.h) — ANR watchdog compiles to no-op, same as a Linux
  build.
- getdnssvraddrs/pingquery non-Android branches are empty upstream
  (Android uses __system_property_get) — netinfo_util's DNS listing shows
  "empty" on OHOS; the STN DNS path uses getaddrinfo_with_timeout which
  works natively.
