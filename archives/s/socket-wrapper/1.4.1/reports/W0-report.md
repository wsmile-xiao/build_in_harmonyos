# W0 Dependency Report — socket-wrapper 1.4.1

Date: 2026-09-04

## Source and language baseline

- Official source: `https://ftp.samba.org/pub/cwrap/socket_wrapper-1.4.1.tar.gz`
- SHA256: `390cc82a1b2103555cfd803bc1acbfeeed2b68cde081005b92cac78ec76554aa`
- Build system: CMake 3.5 or newer
- Declared project: `project(socket_wrapper VERSION 1.4.1 LANGUAGES C)`
- Language preflight: task `cpp`, detected `c`, accepted as the C/C++ compatible family
- Source statistics: 37 C source files; C is 100% of the compiled-language sources

The 1.4.1 source declares 28 regular CMocka executables, two additional
SCM_RIGHTS tests when `HAVE_STRUCT_MSGHDR_MSG_CONTROL` is available, and one
fork/thread deadlock test. The expected maximum CTest inventory is therefore
31 entries. The configured `ctest -N` output on OHOS is the final authority.

## Hard runtime dependencies

None. `libsocket_wrapper.so` and `libsocket_wrapper_noop.so` use the target
libc, dynamic loader, and pthread implementation supplied by HarmonyOS.

## Test dependencies

| Dependency | Required by | Registry evidence | Status |
|---|---|---|---|
| `cmocka/2.0.2` | Upstream CTest suite (`find_package(cmocka 1.1.0 REQUIRED)`) | `conan download cmocka/2.0.2 -r=ohpcd --only-recipe` downloaded recipe revision `07881f2c819b9063a0be6ece415bb688`; `conan install --requires=cmocka/2.0.2 -r=ohpcd -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never` downloaded package ID `21b17f8b2bc0e9511e276e3d57a23893067cefe5`, revision `b4ce227ddd2e15f8e1874032e5478ffa` | Published and resolvable for OHOS 6.0/aarch64 |

## HarmonyOS 6.0 runtime evidence

The local `Huawei_2in1` emulator reports:

```text
Linux localhost 5.10.210 ... x86_64
OpenHarmony-6.0.0.47
uid=2000(shell) ... context=u:r:sh:s0
```

- `/tmp` is mounted read-only (`touch` returns exit code 1).
- `/data/local/tmp` is writable and is the emulator test runtime directory.
- The dynamic loader accepts `LD_PRELOAD` for shell-launched programs.
- This emulator image is runtime-only: it does not contain Conan, CMake,
  Clang, Git, `llvm-objcopy`, or `binary-sign-tool`.
- The installed host Native SDK 26.0.0 contains the
  `x86_64-linux-ohos` toolchain. Host cross-built ELF files will be pushed
  over HDC and executed on the HarmonyOS 6.0 emulator.
- Repository-standard aarch64 Conan/CI validation still uses
  `ci/conan/profiles/ohos-aarch64` in a DevBox-equipped HarmonyOS environment.

## Capability evidence relevant to the port

The installed OHOS musl headers declare:

```c
int sendmmsg(int, struct mmsghdr *, unsigned int, unsigned int);
int recvmmsg(int, struct mmsghdr *, unsigned int, unsigned int,
            struct timespec *);
```

They also define `fopen64`, `open64`, and `openat64` as macros that alias the
non-64-suffixed functions. These facts independently confirm the two main
portability adaptations seen in the 1.5.2 reference without treating that
newer recipe as a substitute for 1.4.1 evidence.

## Conclusion

W0 passes. No missing dependency blocks the port. Use `cmocka/2.0.2` only as
a test requirement, preserve the shared-library/`LD_PRELOAD` package model,
and use a short writable native filesystem for `SOCKET_WRAPPER_DIR`.
