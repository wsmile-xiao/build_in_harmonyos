# socket-wrapper 1.5.2 adaptation notes

## Scope

- Branch: `feat/socket-wrapper-1.5.2`
- Allowed edit scope: `archives/s/socket-wrapper/1.5.2/`
- Same cwrap family as pam-wrapper/1.1.8 and nss-wrapper/1.1.16, both already
  archived in this repository

## W0 dependency check

`socket_wrapper` is a CMake cwrap project that builds:

- `libsocket_wrapper.so`, the LD_PRELOAD interposition library that redirects
  BSD socket API calls through Unix domain sockets
- `libsocket_wrapper_noop.so`, the link-time stub library exposing the public
  helpers (`socket_wrapper_enabled()`, `socket_wrapper_indicate_no_inet_fd()`,
  `socket_wrapper_syscall_valid()`, `socket_wrapper_syscall_va()`)

There are no hard runtime dependencies; everything needed comes from libc
and libpthread. The upstream CTest suite requires `cmocka >= 1.1.0`.

W0 results (R35: verified with actual downloads, not just `conan list`):

```text
conan list "cmocka/*" -r=ohpcd          -> cmocka/2.0.2
conan download cmocka/2.0.2 -r=ohpcd --only-recipe -> recipe in cache
conan install --requires=cmocka/2.0.2 -r=ohpcd -pr:h ohos-aarch64
                                        -> binary 21b17f8b... Already installed
```

cmocka/2.0.2 is published in the ohpcd remote with a usable OHOS binary, so
the recipe runs the upstream suite with it as a `test_requires` dependency.

## Source and build analysis

- Source URL (official gitlab archive format, tag is the full
  `socket_wrapper-1.5.2`, not `v1.5.2`):
  `https://gitlab.com/cwrap/socket_wrapper/-/archive/socket_wrapper-1.5.2/socket_wrapper-socket_wrapper-1.5.2.tar.gz`
- SHA256: `f03d8933457d13d69fa0aebc946685e904186bd81513b154a6de06d806f40387`
- Build system: CMake >= 3.10; 1.4.x and older used autoconf, 1.5.x is CMake
- Default recipe mode: `with_upstream_tests=True`, `UNIT_TESTING=ON`
- Opt-out mode for non-runnable cross-builds: `with_upstream_tests=False`

## Platform findings

| # | Finding | Impact | Handling |
|---|---------|--------|----------|
| 1 | musl (OHOS libc) defines `fopen64`/`open64`/`openat64` as macros aliasing `fopen`/`open`/`openat` under `_GNU_SOURCE`, so the interposed `FILE *fopen64(...)` etc. conflict with the macro expansions | 3 redefinition errors | `0001` adds `#undef fopen64/open64/openat64` (guarded by `__OHOS__`) right before the three interposed definitions |
| 2 | musl declares `int recvmmsg(int, struct mmsghdr *, unsigned int, unsigned int, struct timespec *)` and `int sendmmsg(int, struct mmsghdr *, unsigned int, unsigned int)` — flags are `unsigned int`, while upstream only knows the glibc (`int` flags) and FreeBSD (`ssize_t`) prototypes | 2 conflicting-types errors for the exported `recvmmsg`/`sendmmsg` | `0002` adds `check_prototype_definition` probes (`HAVE_RECVMMSG_UNSIGNED_FLAGS`, `HAVE_SENDMMSG_UNSIGNED_FLAGS`), `0003` declares them in config.h.cmake, `0001` adds the musl branch to all 4 recvmmsg and 3 sendmmsg signature chains (typedef, libc_ wrapper, swrap_ implementation, exported symbol) |
| 3 | OHOS mounts `/tmp` read-only (E002) and the upstream test helpers hardcode `/tmp/...` mkdtemp templates | test_ioctl/test_fcntl_lock setup failures, torture.c socket dir failure | `0004`/`0005`/`0006` make torture.c, test_ioctl.c and test_fcntl_lock.c honor `TMPDIR`, falling back to the original `/tmp` template; the conan recipe sets TMPDIR to a build-tree runtime dir |
| 4 | AF_UNIX socket `bind()` returns EPERM on the HMDFS `/storage/...` share where `$HOME` lives, but succeeds on `/data/storage/el2/base/temp` | exploratory runs from `$HOME/tmp` failed with `bind: Operation not permitted` | The recipe's ctest step points `SOCKET_WRAPPER_DIR` at a directory under the build folder on a native filesystem; the exploratory validation ran from `/data/storage/el2/base/temp` |
| 5 | OHOS ELF binaries must be signed before execution (E077) | build-tree tests and packaged .so files cannot run/load unsigned | The recipe signs the upstream test binaries, helper .so files, and packaged .so files with `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`, mirroring pam-wrapper/1.1.8 |

## Upstream test results

All 32 CTest entries build and register on OHOS. Full run with
`cmocka/2.0.2` from the ohpcd remote:

```text
91% tests passed, 3 tests failed out of 32
FAILED: test_ioctl, test_fcntl, test_python_concurrency_reproducer
```

The three failures are OHOS platform limits, not socket_wrapper defects:

1. `test_ioctl`: the OHOS kernel returns EACCES (errno 13) for
   `ioctl(fd, SIOCGPGRP, &grp)` even on a plain, un-interposed UDP socket.
   Verified with a standalone C probe without LD_PRELOAD: `rc=-1 errno=13`.
2. `test_fcntl`: the `test_fcntl_dupfd_existing_open_fd` case expects
   `fcntl(s, F_DUPFD, 100) == 100`, but the OHOS fd table allocates the first
   free descriptor above 107 in this process, so the dup returns 108. This is
   an fd allocation layout difference, not an interception bug
   (`test_fcntl_getfd_existing_open_fd` passes).
3. `test_python_concurrency_reproducer`: needs `/usr/bin/echo` (missing on
   OHOS) and a writable `/tmp` for its mktemp template.

Everything else passes: TCP connect/bind/write-read/writev-readv/poll/
sendmsg-recvmsg(+fd)/sendmmsg-recvmmsg/get_peer_sock_name/socket_options,
UDP send-recv/sendto-recvfrom/sendmsg-recvmsg, dup2, listen, max_sockets,
public_functions, close_failure, tcp_socket_overwrite, syscall_uwrap, all
five threaded tests, sendmsg_recvmsg_fd, fork_thread_deadlock, swrap_unit.

## Exploratory functional validation (before packaging)

Independent consumer program (kept simplified in test_package):

```text
SOCKET_WRAPPER_DIR=<writable dir> SOCKET_WRAPPER_IFACE=2 \
LD_PRELOAD=<...>/libsocket_wrapper.so ./quick_test
socket_wrapper_enabled=1
bind/listen on 127.0.0.1:27777 ok
connect ok
accept peer= 127.0.0.1:10786 (AF_INET passthrough view)
echo payload ok: swrap-ohos
socket-wrapper LD_PRELOAD loopback redirection PASSED
```

The wrapper created the `T016C81` unix socket file in SOCKET_WRAPPER_DIR and
the accept() peer was presented as AF_INET 127.0.0.1, proving the full
interposition round-trip on OHOS/musl.

## Local verification

- Downloaded the official tarball and computed SHA256
- Exploratory CMake configure + build with the OHOS clang toolchain: pass
  after the six portability patches
- Patch dry-run + apply check against a pristine tree: all six patches apply
  cleanly and reproduce the working tree
- `python -m py_compile` on conanfile.py and test_package/conanfile.py
- `conan create` with `-pr:h/-pr:b ohos-aarch64`: pass (W3, .ci-result.json
  exit_code=0)

## Notes for downstream users

- `package_info().libs` exposes `socket_wrapper_noop`, the link-time stub that
  applications should link against when they call the public helpers;
  `libsocket_wrapper.so` is meant for `LD_PRELOAD` only and its path is
  exported as `SOCKET_WRAPPER_LIB` in runenv/buildenv
- The packaged .so files are signed for OHOS; consumers that copy them must
  preserve the signature
---

**编译结束**: 2026-09-02 18:36
**最终状态**: built
