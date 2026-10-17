# uid-wrapper 1.2.5 adaptation notes

## Environment

- Build system: CMake (top-level CMakeLists.txt, minimum 3.5.0)
- Date: 2026-09-02
- Status: built
- Branch: feat/uid-wrapper-1.2.5

## W0 dependency check

`uid-wrapper` (cwrap family) is an LD_PRELOAD interposition library that
wraps the uid/gid libc family (getuid/setuid/seteuid/setresuid/setgroups
and syscall-based variants). It has no hard runtime dependency; the only
external requirement is the `cmocka` test framework for the upstream
CTest suite.

Probe on the `ohpcd` remote:

- `conan download cmocka/2.0.2 -r=ohpcd --only-recipe` → recipe found
- `conan list cmocka/2.0.2:* -r=ohpcd` → package
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5` for
  `armv8/clang 15/OHOS 6.0` exists

`cmocka/2.0.2` is therefore consumable as a `test_requires` for the
upstream suite; no other dependencies.

## Source and build analysis

- Source URL: `https://gitlab.com/cwrap/uid_wrapper/-/archive/uid_wrapper-1.2.5/uid_wrapper-uid_wrapper-1.2.5.tar.gz`
- SHA256: `7cf89aae95f45d0c8b36c4b75eb36d65f7f769846eec7c6c0564fd6b6cb44275`
- Build system: CMake; `UNIT_TESTING` option gates the cmocka test suite
- License: GPL-3.0-or-later (full GPL text in `LICENSE`)

Upstream builds `libuid_wrapper.so` (SOVERSION 0) plus a pkg-config file,
CMake config files, and a man page. The wrapper activates via
`LD_PRELOAD=libuid_wrapper.so` with `UID_WRAPPER=1` (and
`UID_WRAPPER_ROOT=1` to simulate root).

## Platform findings

| # | Finding | Impact | Handling |
|---|---------|--------|----------|
| 1 | musl does not define `RTLD_DEEPBIND`; OHOS loader has no libc.so.6 | Upstream code compiles because both are behind `#ifdef` guards; dlopen loop falls back to `RTLD_NEXT` | No patch needed; verified by build + runtime test |
| 2 | musl `syscall()` prototype is `long syscall(long, ...)` not `int syscall(int, ...)` | `HAVE_SYSCALL_INT` stays undefined; uid_wrapper uses its va_list path | No patch needed |
| 3 | `CMAKE_SYSTEM_NAME=HarmonyOS` is not matched by upstream `DefinePlatformDefaults.cmake` (`LINUX` stays unset) | `HAVE_LINUX_32BIT_SYSCALLS` is not defined → the seven `*32` syscall tests are not registered (they are i386-era compat syscalls, not applicable to aarch64 anyway) | No patch needed; native aarch64 syscall tests (`test_syscall*`) still run and pass |
| 4 | musl loader does not search the executable directory for DT_NEEDED libraries | `test_uwrap_enabled` fails to load `libuwrap_enabled.so` (`Error loading shared library libuwrap_enabled.so`) | Patch 0001 adds `LD_LIBRARY_PATH=${CMAKE_CURRENT_BINARY_DIR}` to that test's environment |
| 5 | OHOS has no `nobody` account; more importantly OHOS seccomp kills the real (non-wrapped) privileged-id syscall from an unprivileged process with SIGSYS instead of returning `-1/EPERM` | `test_uwrap_disabled` first failed at `getpwnam("nobody") == NULL`, and after a synthetic-uid retry it died with SIGSYS at the real `setreuid` | Patch 0001 disables the `test_uwrap_disabled` CTest entry on HarmonyOS (target still built). The wrapper-disabled code path is still covered indirectly by `test_uwrap_enabled` plus the real-syscall passthrough exercised by `test_syscall*` |
| 6 | MAN_INSTALL_DIR is never set upstream; `install(FILES uid_wrapper.1 DESTINATION ${MAN_INSTALL_DIR}/man1)` | With DESTDIR staging the man page lands in `<dest>/man1`; no absolute-path pollution observed | No patch needed (verified by make install DESTDIR staging) |
| 7 | OHOS ELF signing | Packaged `.so` artifacts get a `.codesign` section like pam-wrapper | Same `_sign_elf_files` helper pattern as `pam-wrapper/1.1.8` |

## Upstream CTest validation

Full local OHOS device run (aarch64, OHOS 6.0, clang 15 from
`/data/service/hnp/bin`), with cmocka/2.0.2 from the ohpcd remote:

- 25 tests registered upstream (before gating)
- 24 passed, 0 failed
- 1 disabled: `test_uwrap_disabled` (seccomp SIGSYS, finding #5)
- The 7 `*32` i386-compat syscall tests are not registered on aarch64
  (finding #3), consistent with upstream behavior on 64-bit-only systems

## Verification

Device-native preflight (out-of-tree cmake, same toolchain as Conan):

```bash
cmake -DCMAKE_BUILD_TYPE=Release -DUNIT_TESTING=ON \
      -DCMAKE_PREFIX_PATH=<cmocka pkg> ../uid_wrapper-uid_wrapper-1.2.5
make -j8
ctest --output-on-failure -j4   # 100% tests passed, 0 failed out of 24
```

Runtime interposition check (fake root):

```
$ UID_WRAPPER=1 UID_WRAPPER_ROOT=1 LD_PRELOAD=.../libuid_wrapper.so ./t_uwrap
uid=0 euid=0 gid=0
after setuid(0): uid=0 euid=0
```

The Conan `test_package` runs the same matrix via `LD_PRELOAD` with
`UID_WRAPPER=1 UID_WRAPPER_ROOT=1` and asserts 17 checks
(getuid/geteuid/getgid/getegid==0, getresuid/getresgid, setuid/seteuid/
setgid/setgroups/setresuid transitions).
---

**编译结束**: 2026-09-02 16:08
**最终状态**: built
