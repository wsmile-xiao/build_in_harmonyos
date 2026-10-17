# uid-wrapper 1.2.5 OpenHarmony adaptation record

## Basic information

- Software: uid-wrapper
- Version: 1.2.5
- Build system: CMake
- Target: Linux or OHOS libc environments with LD_PRELOAD support

## Build guidance

The package builds upstream `uid_wrapper` as the shared library
`libuid_wrapper.so`. It is consumed via `LD_PRELOAD=libuid_wrapper.so`
together with `UID_WRAPPER=1` (and `UID_WRAPPER_ROOT=1` to simulate
root), letting unprivileged test processes exercise uid/gid transitions
without real privileges.

The Conan test package runs the library through `LD_PRELOAD` and
verifies that getuid/geteuid/getgid/getegid report 0 and that
setuid/seteuid/setgid/setgroups/setresuid transitions succeed under the
wrapper.

The upstream CTest suite is enabled by default through the
`with_upstream_tests=True` option, which adds the `cmocka/2.0.2`
test requirement, turns on `UNIT_TESTING`, and runs CTest during the
Conan build step.

## Known limits

- `test_uwrap_disabled` is disabled on HarmonyOS: it expects the real
  (non-wrapped) privileged-id syscall to fail with `-1/EPERM`, while the
  OHOS seccomp policy terminates the unprivileged syscall with SIGSYS.
  The target is still built; only its CTest registration is gated off.
- The seven i386-compat `*32` syscall tests are not registered on
  aarch64 (upstream `HAVE_LINUX_32BIT_SYSCALLS` gate), consistent with
  upstream behavior on 64-bit-only systems.
- musl compatibility is native: `RTLD_DEEPBIND` and the `libc.so.6`
  dlopen probe are compiled out through upstream `#ifdef` guards, and
  the wrapper falls back to `RTLD_NEXT`.

## Verification

Device-native verification (aarch64 OHOS 6.0, clang 15):

- Upstream CTest with cmocka/2.0.2: 24 passed, 0 failed, 1 disabled.
- `test_package` LD_PRELOAD interposition check passed on device.
