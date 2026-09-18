# rnnoise 0.1.1 adaptation notes (HarmonyOS PC, aarch64)

- Upstream is the official Xiph GitLab repo: gitlab.xiph.org/xiph/rnnoise, tag
  `v0.1.1`. The tarball SHA-256 is byte-verified in `conandata.yml`.
- The project is Autotools (configure.ac + Makefile.am). The v0.1.1 tarball
  ships no generated `configure`, so `build()` runs `autoreconf -fi` first;
  automake/libtool are pulled as `tool_requires` (automake/1.18 +
  libtool/2.5.4, same precedent as abiword-plugin-docbook) because the CI
  sandbox only has the autoconf family.
- E114 (OHOS security framework): configure's `config.status` subprocess cannot
  create its `./confXXXXXX` temp dir and write `subs1.awk` (Permission denied).
  The recipe pre-creates a writable dir, points `TMPDIR` at it, and repoints
  configure's internal `ac_tmp` (same fix as libgsf/abiword-plugin-docbook).
- The library links only against libm; no third-party runtime dependencies.
- Upstream v0.1.1 ships no test suite (no tests dir / make check / framework);
  `configure.ac` only defines the library plus the `rnnoise_demo` example.
- Consumer validation (test_package/test.c) exercises rnnoise_create /
  rnnoise_process_frame / rnnoise_destroy on OHOS aarch64 and runs inside
  `conan create`.
---

**编译结束**: 2026-09-08 00:36
**最终状态**: built
---

**编译结束**: 2026-09-08 00:41
**最终状态**: built
