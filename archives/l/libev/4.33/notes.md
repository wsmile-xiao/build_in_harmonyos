# libev 4.33 OHOS Conan adaptation

## Scope

- Source: libev 4.33 release archive with verified SHA256.
- Package: shared `libev` C library plus `ev.h`, `ev++.h`, and `event.h`.
- Dependencies: no third-party Conan dependencies.

## Build approach

The archived autotools attempt failed when `config.status` created temporary
files on HMDFS. The recipe therefore generates a small CMake project that
builds the same upstream sources (`ev.c` and `event.c`) and derives `config.h`
from compile/link feature checks.

SDK 11 does not contain a system `libev.so`, so the recipe defaults to a shared
package. It assigns `VERSION 4.0.0` and `SOVERSION 4`, matching upstream
libtool `-version-info 4:0:0`, and uses `$ORIGIN` as the install RUNPATH.

OHOS does not implement the newer io_uring syscall family. The generated CMake
target sets `EV_USE_IOURING=0` only for OHOS; portable epoll, poll, select,
eventfd, signalfd, and timerfd capabilities remain controlled by feature checks.
The Linux `__kernel_rwf_t` typedef is checked with a compile probe equivalent to
upstream `AC_CHECK_TYPES`, rather than a symbol-address probe that rejects types.

## Tests and evidence boundary

libev 4.33 ships no upstream test target. The Conan consumer validates the
reported 4.33 version, creates the default event loop, and runs a one-shot
timer callback. During a Windows-to-OHOS cross-build it is compiled and linked
but not executed because `can_run()` is false. Target execution was verified
separately on a HarmonyOS PC device.

Three independent CTest unit cases now cover version constants, loop userdata
and initial state, and one-shot timer activation/callback/event-mask behavior.
They contain 11 assertions and compile/link together with the existing
3-assertion consumer. The forced `conan create --build=libev/*` log SHA256 is
`8D0866DEE4B767D50A76AC1546EF6A39744951419C21910CA3BAB4D95DDB6037`;
the Windows-hosted cross-build still skips execution by design.

On 2026-07-24, the two AArch64 test executables and `libev.so.4` were uploaded
to `/storage/Users/currentUser/codex-tests/pr-3009` on HarmonyOS PC
`10.62.151.101:2222`. Each ELF was signed in its final HMDFS path. The consumer
and the `version`, `loop_userdata`, and `timer_once` unit cases all exited 0,
for a device result of 4/4. The consumer output confirmed libev 4.33 and the
default-loop timer callback. Signed SHA256 values were
`b437815ccf3dfb1dc47ef16dd7022e065205cf6e866426389592336d1b92f070`
(`test_libev`),
`c7943dcaa8e19c05edd5acf8b15412697e4e2ccc98c976ea9d4cd887c7e8c609`
(`test_libev_unit`), and
`b171e3108547d3d0ffcbcee2682680ced519b9344367ff3acfbb96d0528f5eea`
(`libev.so.4`).

The final `conan create` produced recipe revision
`73333e435862e817075ecb36ab0f55b9`, package ID
`01d92cf349a0dd98ff915f4bd99a04430171517f`, and package revision
`03688af8a1f0696b9ad4f751a2d55240`. `llvm-readelf` confirmed AArch64 ELF64,
SONAME `libev.so.4`, RUNPATH `$ORIGIN`, and only `libc.so` as a dynamic
dependency. The package contains no static archive and no Windows path string.

## Knowledge reuse and path classification

- Reused `openharmony-conan-cmake-upstream-tests-cross-runpath` for the shared
  library RUNPATH and host-path audit.
- Reused the existing OHOS adaptation rule that unsupported new Linux syscalls
  such as io_uring must not be enabled solely because Linux headers are present.
- Added verified knowledge draft E217 (`knowledge/graph/draft/E217-draft-CX17.kv`
  and `knowledge/graph/draft/E217-draft-CX17.md`) for the reusable rule that typedef availability must
  be tested with a target compile probe rather than `check_symbol_exists`.
  This is a path B knowledge innovation, so the dependency is classified as
  path A + path B.
- libev uses public C/CMake/Conan tooling, has no private system interface,
  assembly, closed binary, special scheduler, or large dependency graph, so it
  does not qualify for path C.
