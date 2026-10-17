# libg722 1_2_0

ITU G.722 wideband speech codec (Sippy Software packaging of the public-domain
SpandSP/CMU implementation). Bit-exact encoder/decoder for 64/56/48 kbps with
an optional 8 kHz narrowband interop mode.

## Upstream

- Repository: https://github.com/sippy/libg722
- Version tag: v_1_2_0 (upstream versions as 1.2.0; this recipe uses 1_2_0
  directory/version naming per task requirement)
- Archive: https://github.com/sippy/libg722/archive/refs/tags/v_1_2_0.tar.gz
- sha256: 80b061446b1a014c27eff5659a2bcee4f584e44054b17a1cb3c8840da72513b6
  (matches FreeBSD ports distinfo for the v_1_2_0 codeload tarball)
- License: public domain (recipe declares Unlicense as the closest SPDX
  identifier; test code is BSD-2-Clause per upstream LICENSE)
- Build system: CMake (C17, options ENABLE_SHARED_LIB / ENABLE_STATIC_LIB)
- Public headers: g722.h, g722_codec.h, g722_encoder.h, g722_decoder.h
- No library dependencies.

## Upstream test audit

- tests/ directory: upstream has no tests/ directory; the suite is wired
  purely through CMakeLists.txt CTest integration.
- CTest registration (CMakeLists.txt, top-level project only):
  TestDynamic (links shared g722) and TestStatic (links static g722_static),
  both running `scripts/do-test.sh <test-binary>`.
- do-test.sh performs 6 fixture round-trips (decode/encode at 8k and 16k,
  big-endian variants, fullscale vector) and diffs
  `openssl sha256` output against test_data/test.checksum.
- Counted total: 2 ctest cases. Framework: ctest.
- The recipe forces both ENABLE_SHARED_LIB=ON and ENABLE_STATIC_LIB=ON so
  the full 2-case suite always runs, independent of the consumer's
  `shared` option. `ctest --output-on-failure` output is parsed for the
  "N tests passed ... out of M" line; the HMBS_UPSTREAM_TEST_RESULT marker
  is emitted via both print and self.output.info and persisted to
  build hmbs_upstream.json, then packaged to res/hmbs_upstream.json so the
  test_package can re-emit it on cache-hit rounds.
- Anti-false-pass notes: the marker requires rc==0 plus 2/2 Passed lines;
  exit 0 with zero Passed lines is reported as failed, not passed.
  do-test.sh needs `openssl` and `diff` from the base environment.

## Build approach

- Standard CMakeToolchain + cmake_layout flow, no patches.
- No OHOS-specific code paths; the codec is portable C17 (uses endian.h
  and getopt only in the test tool, which builds with the OHOS clang).
- Both libg722.so (VERSION 0) and libg722.a are built and packaged;
  libg722 is not a system-name library so the shared object is kept (R26
  does not apply).
- test_package builds test_g722.c with CMakeDeps/CMakeToolchain and runs
  9 real API checks (encoder/decoder lifecycle, 64k lengths, all three bit
  rates, 8 kHz mode). Each check prints CHECK-OK; the conanfile counts
  them for HMBS_TEST_PACKAGE_RESULT and runs the binary a second time
  under conanrun.

## HarmonyOS validation

- Pending HMBS true-machine preflight in this round; the recipe is written
  so `conan create` runs the upstream ctest suite followed by the consumer
  test. Results will be transcribed into the PR body from the preflight
  log only (no estimates).

## True-machine finding (TestDynamic loader failure)

- Symptom on HarmonyOS aarch64 preflight: TestStatic passed, TestDynamic
  failed with `Error loading shared library libg722.so` followed by
  `g722_decoder_new/g722_decode/g722_encoder_new/g722_encode: symbol not
  found`. Static passing while every shared-lib symbol is unresolved points
  at the loader not finding the just-built .so (build-tree RPATH stripped
  by the cross toolchain), not at broken codec code.
- Fix (recipe-level, no upstream source change, full 2-case suite still
  runs): bake the absolute build-tree lib dirs into the test binaries via
  CMAKE_BUILD_RPATH with CMAKE_BUILD_WITH_INSTALL_RPATH=OFF, keep an
  LD_LIBRARY_PATH fallback when invoking ctest, and pin
  CMAKE_C_VISIBILITY_PRESET=default since upstream declares plain C symbols
  with no visibility attributes (g722_decoder.h/g722_encoder.h).
