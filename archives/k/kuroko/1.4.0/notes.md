# HarmonyOS PC verification

- Official `v1.4.0` source archive SHA-256:
  `55c143761da9b3ed0f523b9f7828dc04fc8e02280783274376dbbd335866c95d`.
- Exact archive bytes transferred to `10.62.210.132:2222`; remote SHA-256
  matched. Remote test root:
  `/data/storage/el2/base/haps/entry/files/kuroko-1.4.0-20260926T181400`.
- Native serial Clang build succeeded with default rich line editor. Upstream
  `make test` completed 148/148 `.krk`/`.expect` cases. No tests were edited.
- Isolated Conan home with the OHOS AArch64 profile: `conan graph info`
  resolved no external packages; `conan create` built the source, reran the
  full upstream suite, and passed the installed-package consumer test. The
  final `create-v3.log` SHA-256 is
  `b34bb50d47025261aa13b084f48a3e0d645fbcc3fd71eb28c018d7f7af3f03a3`.
  It reports package revision `46f4033d8e556ab240ccfe89dc17c21c` and
  `Kuroko packaged interpreter, module import, tool and C API: PASS`.
- Conan verification used `file://` for the exact same SHA-256 tarball because
  the target's GitHub access is not assumed; committed `conandata.yml` retains
  the official HTTPS URL. This does not verify direct HTTPS download on device.
- A packaged `krk-demo` without a library-path setting fails to find
  `libkuroko.so` (exit 127). `readelf -d` shows `$ORIGIN` RUNPATH; with the
  package `lib/` path in `LD_LIBRARY_PATH`, it prints `Kuroko 1.4.0` (exit 0).
  The recipe exports that Conan run environment. Direct standalone tool
  invocation without the environment is not claimed.
- The upstream build emits C compiler warnings; no zero-warning claim is made.
