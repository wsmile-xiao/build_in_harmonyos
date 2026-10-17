# ParaFly 0.1.0

**Build system:** Autotools  
**Source:** https://codeload.github.com/ParaFly/ParaFly/tar.gz/refs/tags/v0.1.0  
**Source commit:** `1fdec9c5611661f1936df0411cbee33c04cedacf`  
**SHA256:** `662e8bc2d7f5dae2cb63804bba13b4790eeda9f4e40126e1d947005c89134c4d`

## OHOS build notes

- E011: the upstream configure script creates private temporary files with umask 077; patch 0001 changes both temporary-directory attempts to umask 022 for HMDFS.
- The source snapshot includes a stale generated `config.status`; the recipe removes it from the Conan source and build staging directories before configuring.
- E127: use the SDK-provided OpenMP headers and runtime rather than building libomp, whose pthread cancellation APIs are unavailable on OHOS. The recipe locates `omp.h` relative to the configured compiler.
- Patch 0002 replaces the removed C++17 `random_shuffle` with `std::shuffle` and a Mersenne Twister generator.
- The source archive includes a prebuilt x86_64 binary at `bin/ParaFly`; the package installs only the binary rebuilt from source. The Conan build copy replaces its bundled `bin/ParaFly` with the rebuilt executable before running `make -C test test`, so the upstream test Makefile does not run the x86_64 snapshot binary.

## Tests

- Upstream `make test`: all 10 entries in `test/cmds.txt` completed successfully on the HarmonyOS device.
- Consumer `test_package/test.sh`: three commands ran, completion records were written, and no failed commands were recorded (5/5 checks).
- `conan create` and the consumer test passed with Conan 2.29.1; G0 and W3 are recorded by the archive finish pipeline.

## Discoveries and findings

- ✅ Configure's umask 077 prevents generated temporary files from working on HMDFS; use umask 022 (E011).
- ✅ The SDK compiler path identifies the OpenMP header/runtime location without a separate libomp package (E127).
- ✅ The archived Git snapshot contains generated configure state, so remove `config.status` before an out-of-tree configure.
- ✅ C++17 removes `random_shuffle`; use `std::shuffle` with an explicit random-number generator.
---

**编译结束**: 2026-09-29 01:23
**最终状态**: built
