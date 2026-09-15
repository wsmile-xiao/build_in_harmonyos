// Copyright 2026 The OpenHarmony PC adaptation authors.
//
// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// ----------------

// wuffs HarmonyOS-platform test (aarch64 SIMD fast path vs portable fallback).
//
// WHY THIS TEST EXISTS
//
// wuffs is a "single file C library": one file that acts as a header unless
// WUFFS_IMPLEMENTATION is defined. Its performance on HarmonyOS PC depends on
// compile-time-selected CPU-architecture-specific code paths. From
// release/c/wuffs-v0.4.c:
//
//   // To simplify Wuffs code, "cpu_arch >= arm_xxx" requires xxx but also
//   // unaligned little-endian load/stores.
//   #if defined(__ARM_FEATURE_UNALIGNED) && ... && little-endian
//   #if defined(__ARM_FEATURE_CRC32)  ->  CPU_ARCH__ARM_CRC32
//   #if defined(__ARM_NEON)           ->  CPU_ARCH__ARM_NEON
//
// So on OHOS PC (aarch64) the shipped build takes the NEON path, and that path
// is *conditional on platform capabilities*: little-endian byte order and
// working unaligned loads/stores. If either precondition does not actually
// hold on the target, wuffs' arch-specific code would be miscompiled or
// mis-selected - a failure mode that no amount of portable-C testing can
// detect, because the portable code is not what runs.
//
// Measured on this toolchain (see check 2 below, which prints both probes):
// __ARM_NEON and __ARM_FEATURE_UNALIGNED are defined, so the NEON path IS
// selected; __ARM_FEATURE_CRC32 is NOT defined by default (it needs an
// explicit -march=armv8-a+crc), so the ARM CRC-32 instruction path is NOT
// selected here and CRC-32 runs on the portable implementation.
//
// WHAT IT CHECKS
//
//   1. the platform preconditions that gate the aarch64 fast paths hold here
//      (little-endian, LP64, unaligned 64-bit round trip);
//   2. the library's own runtime probe agrees about which path was selected:
//      wuffs_base__cpu_arch__have_arm_neon() is ASSERTED in both directions, so
//      this file compiled twice proves it really exercises two different
//      implementations. The other probes (have_arm_crc32(), have_x86_sse42(),
//      have_x86_avx2()) are printed for the record and, where the expected
//      value is platform-invariant, also asserted;
//   3. decoding is correct from *unaligned* input buffers, which is precisely
//      the precondition the NEON path relies on: the same PNG is decoded from
//      16 different byte offsets in a deliberately misaligned buffer and every
//      result must equal the digest computed independently (Python
//      binascii.crc32) from the known 4x4 pixel pattern.
//
// HOW IT IS BUILT (see CMakeLists.txt)
//
// This file is compiled into TWO executables from the same source:
//
//   ohos_platform_test           - default flags: aarch64 fast paths ENABLED
//   ohos_platform_test_portable  - -DWUFFS_CONFIG__AVOID_CPU_ARCH: portable C
//
// Assertion 2 makes the pair meaningful: the first must report the NEON path
// as selected, the second must report it as not selected. Since both then have
// to satisfy the same known-answer assertions, agreement between them is a
// real NEON-vs-portable equivalence result rather than a tautology.

#include <stdint.h>
#include <stdio.h>
#include <string.h>

// This file is the single translation unit carrying the implementation, so the
// codec structs are complete types here (as in test_wuffs.c). WUFFS_CONFIG__
// AVOID_CPU_ARCH, when wanted, is passed on the compiler command line by
// CMakeLists.txt and therefore reaches wuffs before the include below.
#define WUFFS_IMPLEMENTATION

// Wuffs configuration shared with the other consumers (same module list).
#include "wuffs_test_config.h"

#include "test_data_png.h"

// ---------------- Expected values

// Independent known answers (Python binascii.crc32 / zlib.adler32 over the
// pixel bytes implied by test_data_png.h; not read back from any build).
#define WANT_CRC32_OF_RGB 0x6B64E606u

// ---------------- Small check harness

static int g_checks = 0;
static int g_failed = 0;

static void check(int ok, const char* what) {
  g_checks++;
  if (!ok) {
    g_failed++;
    printf("FAIL: %s\n", what);
  }
}

static void check_u32(uint32_t have, uint32_t want, const char* what) {
  g_checks++;
  if (have != want) {
    g_failed++;
    printf("FAIL: %s: have 0x%08X, want 0x%08X\n", what, (unsigned)have,
           (unsigned)want);
  }
}

// ---------------- 1. Platform preconditions

static void test_platform_preconditions(void) {
  // The aarch64 fast paths require little-endian byte order (the wuffs source
  // says so explicitly). OHOS PC is little-endian aarch64.
  //
  // Harden against a silent pass: if a compiler defined neither macro, the
  // logical expression below would be false and the check would still "fail"
  // correctly, but the *intent* would be untested. Fail the build instead.
#if !defined(__BYTE_ORDER__) || !defined(__ORDER_LITTLE_ENDIAN__)
#error "cannot determine byte order; the wuffs ARM fast paths assume little-endian"
#else
  check(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
        "platform is little-endian (required to enable wuffs' ARM fast paths)");
#endif

  // wuffs' I/O buffers carry size_t lengths and uint64_t positions; OHOS PC
  // aarch64 is an LP64 target. Assert the data model the library assumes.
  check(sizeof(size_t) == 8, "sizeof(size_t) == 8 (LP64 data model)");
  check(sizeof(uint64_t) == 8, "sizeof(uint64_t) == 8");
  check(sizeof(void*) == 8, "sizeof(void*) == 8 (64-bit pointers)");

  // The other precondition in the wuffs source: unaligned little-endian
  // load/stores must work. Probe it for real through a misaligned pointer, and
  // check the byte order of the loaded value too.
  uint8_t raw[16];
  for (int i = 0; i < 16; i++) {
    raw[i] = (uint8_t)(0x11 * (i + 1));
  }
  for (size_t off = 1; off <= 8; off++) {
    uint64_t got = 0;
    memcpy(&got, raw + off, sizeof got);  // avoid UB from a cast
    uint64_t want = 0;
    for (size_t i = 0; i < 8; i++) {
      want |= ((uint64_t)raw[off + i]) << (8 * i);  // little-endian assembly
    }
    check(got == want, "unaligned little-endian 64-bit load round trip");
  }
}

// ---------------- 2. Which code path did the library select?

static void test_selected_code_path(void) {
  // wuffs exposes its own probes for the ARM fast paths. Assert them in BOTH
  // directions so that the two builds of this file are provably not the same
  // binary: the default OHOS aarch64 build must select the NEON path, and the
  // AVOID_CPU_ARCH build must not.
#if defined(WUFFS_CONFIG__AVOID_CPU_ARCH)
  const int want_neon = 0;
  const char* build_name =
      "portable (WUFFS_CONFIG__AVOID_CPU_ARCH): arch-specific code disabled";
#else
  const int want_neon = 1;
  const char* build_name = "default (aarch64 fast paths enabled)";
#endif

  printf("# build: %s\n", build_name);
  printf("# wuffs_base__cpu_arch__have_arm_neon()     = %d (want %d)\n",
         (int)wuffs_base__cpu_arch__have_arm_neon(), want_neon);
  printf("# wuffs_base__cpu_arch__have_arm_crc32()    = %d\n",
         (int)wuffs_base__cpu_arch__have_arm_crc32());
  printf("# wuffs_base__cpu_arch__have_x86_sse42()    = %d\n",
         (int)wuffs_base__cpu_arch__have_x86_sse42());

  check((int)wuffs_base__cpu_arch__have_arm_neon() == want_neon,
        "library selected the expected ARM NEON path for this build");
  // On an aarch64 target the x86 paths must never be selected; selecting one
  // would mean the arch detection is wrong for this platform.
  check(!wuffs_base__cpu_arch__have_x86_sse42(),
        "no x86 SSE4.2 path selected on this aarch64 platform");
  check(!wuffs_base__cpu_arch__have_x86_avx2(),
        "no x86 AVX2 path selected on this aarch64 platform");
}

// ---------------- 3. Correctness with unaligned input (NEON precondition)

// Decodes the embedded PNG at byte offset |off| inside a deliberately
// misaligned buffer and returns the CRC-32 of the decoded 24bpp RGB pixels.
// Returns 0 on any decode error.
static uint32_t crc32_of_decode_at_offset(size_t off) {
  uint8_t buffer[256];
  uint8_t rgb[TEST_PNG_WIDTH * TEST_PNG_HEIGHT * 3];
  memset(buffer, 0xAA, sizeof buffer);
  memcpy(buffer + off, g_test_png, sizeof g_test_png);

  wuffs_png__decoder dec;
  if (wuffs_png__decoder__initialize(
          &dec, sizeof dec, WUFFS_VERSION,
          WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED)
          .repr != NULL) {
    return 0;
  }

  wuffs_base__io_buffer src = wuffs_base__ptr_u8__reader(
      buffer + off, (size_t)sizeof g_test_png, true);

  wuffs_base__image_config ic = wuffs_base__null_image_config();
  if (wuffs_png__decoder__decode_image_config(&dec, &ic, &src).repr != NULL) {
    return 0;
  }
  if (wuffs_base__pixel_config__width(&ic.pixcfg) != TEST_PNG_WIDTH ||
      wuffs_base__pixel_config__height(&ic.pixcfg) != TEST_PNG_HEIGHT) {
    return 0;
  }
  wuffs_base__pixel_config__set(&ic.pixcfg, WUFFS_BASE__PIXEL_FORMAT__RGB,
                                WUFFS_BASE__PIXEL_SUBSAMPLING__NONE,
                                TEST_PNG_WIDTH, TEST_PNG_HEIGHT);

  wuffs_base__pixel_buffer pb = wuffs_base__null_pixel_buffer();
  if (wuffs_base__pixel_buffer__set_from_slice(
          &pb, &ic.pixcfg,
          wuffs_base__make_slice_u8(rgb, (size_t)sizeof rgb))
          .repr != NULL) {
    return 0;
  }

  wuffs_base__frame_config fc = wuffs_base__null_frame_config();
  if (wuffs_png__decoder__decode_frame_config(&dec, &fc, &src).repr != NULL) {
    return 0;
  }

  uint64_t workbuf_len = wuffs_png__decoder__workbuf_len(&dec).max_incl;
  static uint8_t workbuf[65536];
  if (workbuf_len > (uint64_t)sizeof workbuf) {
    return 0;
  }
  if (wuffs_png__decoder__decode_frame(
          &dec, &pb, &src, WUFFS_BASE__PIXEL_BLEND__SRC,
          wuffs_base__make_slice_u8(workbuf, (size_t)workbuf_len), NULL)
          .repr != NULL) {
    return 0;
  }

  wuffs_crc32__ieee_hasher h;
  if (wuffs_crc32__ieee_hasher__initialize(
          &h, sizeof h, WUFFS_VERSION,
          WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED)
          .repr != NULL) {
    return 0;
  }
  return wuffs_crc32__ieee_hasher__update_u32(
      &h, wuffs_base__make_slice_u8(rgb, (size_t)sizeof rgb));
}

static void test_unaligned_input_decode(void) {
  // Every offset 0..15 must decode identically: this is the platform property
  // (unaligned little-endian load/store) that gates the NEON path above.
  for (size_t off = 0; off < 16; off++) {
    uint32_t have = crc32_of_decode_at_offset(off);
    g_checks++;
    if (have != WANT_CRC32_OF_RGB) {
      g_failed++;
      printf("FAIL: decode from unaligned offset %zu: have 0x%08X, want 0x%08X\n",
             off, (unsigned)have, (unsigned)WANT_CRC32_OF_RGB);
    }
  }
}

// ---------------- 4. The selected CRC-32 implementation is value-correct

static void test_crc32_selected_impl_value(void) {
  // IMPORTANT (measured, not assumed): on the OHOS aarch64 toolchain used here,
  // __ARM_FEATURE_CRC32 is NOT defined by default - it requires an explicit
  // -march=armv8-a+crc. So wuffs does not select its ARM CRC-32 instruction
  // path on this platform, and the check below validates whichever
  // implementation WAS selected (the library reports it above via
  // wuffs_base__cpu_arch__have_arm_crc32(), which prints 0 here). The point of
  // the assertion is the value contract, not the mechanism.
  const uint8_t* nine = (const uint8_t*)"123456789";
  wuffs_crc32__ieee_hasher h;
  if (wuffs_crc32__ieee_hasher__initialize(
          &h, sizeof h, WUFFS_VERSION,
          WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED)
          .repr != NULL) {
    check(0, "crc32 hasher initialize");
    return;
  }
  check_u32(wuffs_crc32__ieee_hasher__update_u32(
                &h, wuffs_base__make_slice_u8((uint8_t*)nine, 9)),
            0xCBF43926u,
            "CRC-32 of \"123456789\" matches the standard check value");
}

// ---------------- main

int main(void) {
  test_platform_preconditions();
  test_selected_code_path();
  test_unaligned_input_decode();
  test_crc32_selected_impl_value();

  printf("OK: %d checks passed, %d failed\n", g_checks - g_failed, g_failed);
  return g_failed ? 1 : 0;
}
