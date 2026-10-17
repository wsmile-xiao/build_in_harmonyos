// Copyright 2026 The OpenHarmony PC adaptation authors.
//
// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// ----------------

// wuffs test_package consumer test (C, implementation translation unit).
//
// This is the L1 consumer view of the Conan package: it uses ONLY the file the
// package installs (include/wuffs/wuffs-v0.4.c), through the public API, and
// checks results against independent known-answer values.
//
// What it verifies:
//   1. the packaged file really is Wuffs 0.4.0-alpha.10 (WUFFS_VERSION and
//      WUFFS_VERSION_STRING, i.e. the versioned release and not the
//      unversioned development snapshot, whose version is 0);
//   2. the file works in both documented modes at once: this TU defines
//      WUFFS_IMPLEMENTATION, while test_wuffs_header_only_tu.c and
//      test_wuffs_cpp.cpp include it as a plain header and link against this
//      TU (header-only use and single-implementation use coexist);
//   3. a real decode: the embedded 4x4 RGB PNG is decoded to 24bpp RGB, and the
//      decoded pixel bytes are hashed. The 4x4 RGB pixel pattern is known a
//      priori, so the expected CRC-32/adler32 values below were computed
//      independently (Python zlib/adler32) from the raw pixel bytes, not read
//      back from this build. Any endianness, alignment or AArch64/NEON codegen
//      bug in the decoder shows up as a mismatch;
//   4. the hasher API on raw input;
//   5. error paths: a decoder initialized with a mismatched WUFFS_VERSION must
//      fail, and a truncated (closed) input must report a hard error rather
//      than a "short read" suspension.

#define WUFFS_IMPLEMENTATION

#include "wuffs_test_config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// ---------------- Test data

// A 4x4 8-bit RGB PNG (filter type 0 on every row, no interlacing), generated
// independently of Wuffs. Pixel (x, y) = (11 + 40x, 23 + 50y, 7 + 30(x+y)),
// each channel taken modulo 256.
static const uint8_t g_png[] = {
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x04,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x26, 0x93, 0x09, 0x29, 0x00, 0x00, 0x00,
    0x3D, 0x49, 0x44, 0x41, 0x54, 0x78, 0xDA, 0x63, 0xE0, 0x16, 0x67, 0x37,
    0x16, 0x57, 0x8D, 0x16, 0x77, 0x6E, 0x16, 0x4F, 0x64, 0xE0, 0xF6, 0x54,
    0x35, 0xF6, 0x74, 0x8E, 0xF6, 0x4C, 0x6C, 0xF6, 0xAC, 0x67, 0xE0, 0xAE,
    0x76, 0x36, 0xAE, 0x4E, 0x8C, 0xAE, 0xAE, 0x6F, 0xAE, 0x9E, 0xCB, 0xC0,
    0xBD, 0x36, 0xD1, 0x78, 0x6D, 0x7D, 0xF4, 0xDA, 0xB9, 0xCD, 0x6B, 0x77,
    0x03, 0x00, 0x4D, 0x3B, 0x10, 0xA1, 0x47, 0x03, 0xB8, 0xB7, 0x00, 0x00,
    0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
};

#define PNG_WIDTH 4
#define PNG_HEIGHT 4

// Computed independently from the pixel pattern above (Python binascii/zlib):
//   crc32(png file bytes)     = 0x437F9210
//   crc32(decoded RGB bytes)  = 0x6B64E606
//   adler32(decoded RGB bytes)= 0x3A8710A1
#define WANT_CRC32_OF_PNG_FILE 0x437F9210u
#define WANT_CRC32_OF_RGB 0x6B64E606u
#define WANT_ADLER32_OF_RGB 0x3A8710A1u

static uint8_t g_rgb[PNG_WIDTH * PNG_HEIGHT * 3];

// ---------------- Tiny check harness

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

// ---------------- Hashers

static uint32_t crc32_of(const uint8_t* ptr, size_t len) {
  wuffs_crc32__ieee_hasher h;
  wuffs_base__status status = wuffs_crc32__ieee_hasher__initialize(
      &h, sizeof h, WUFFS_VERSION,
      WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED);
  if (status.repr != NULL) {
    return 0;
  }
  return wuffs_crc32__ieee_hasher__update_u32(
      &h, wuffs_base__make_slice_u8((uint8_t*)ptr, len));
}

static uint32_t adler32_of(const uint8_t* ptr, size_t len) {
  wuffs_adler32__hasher h;
  wuffs_base__status status = wuffs_adler32__hasher__initialize(
      &h, sizeof h, WUFFS_VERSION,
      WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED);
  if (status.repr != NULL) {
    return 0;
  }
  return wuffs_adler32__hasher__update_u32(
      &h, wuffs_base__make_slice_u8((uint8_t*)ptr, len));
}

// ---------------- PNG decoding

// Decodes g_png as 24bpp RGB into g_rgb. Returns NULL on success, or the
// failing status representation.
static const char* decode_png(void) {
  wuffs_png__decoder dec;
  wuffs_base__status status = wuffs_png__decoder__initialize(
      &dec, sizeof dec, WUFFS_VERSION,
      WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED);
  if (status.repr != NULL) {
    return status.repr;
  }

  wuffs_base__io_buffer src =
      wuffs_base__ptr_u8__reader((uint8_t*)g_png, sizeof g_png, true);

  wuffs_base__image_config ic = ((wuffs_base__image_config){});
  status = wuffs_png__decoder__decode_image_config(&dec, &ic, &src);
  if (status.repr != NULL) {
    return status.repr;
  }
  if (wuffs_base__pixel_config__width(&ic.pixcfg) != PNG_WIDTH) {
    return "unexpected width";
  }
  if (wuffs_base__pixel_config__height(&ic.pixcfg) != PNG_HEIGHT) {
    return "unexpected height";
  }

  // Ask for 24bpp RGB regardless of the file's own pixel format.
  wuffs_base__pixel_config__set(&ic.pixcfg, WUFFS_BASE__PIXEL_FORMAT__RGB,
                                WUFFS_BASE__PIXEL_SUBSAMPLING__NONE, PNG_WIDTH,
                                PNG_HEIGHT);

  wuffs_base__pixel_buffer pb = ((wuffs_base__pixel_buffer){});
  status = wuffs_base__pixel_buffer__set_from_slice(
      &pb, &ic.pixcfg,
      wuffs_base__make_slice_u8(g_rgb, (size_t)sizeof g_rgb));
  if (status.repr != NULL) {
    return status.repr;
  }

  wuffs_base__frame_config fc = ((wuffs_base__frame_config){});
  status = wuffs_png__decoder__decode_frame_config(&dec, &fc, &src);
  if (status.repr != NULL) {
    return status.repr;
  }

  // decode_frame needs a scratch buffer of at least the decoder's advertised
  // workbuf length (upstream's own callers size theirs from workbuf_len()).
  uint64_t workbuf_len = wuffs_png__decoder__workbuf_len(&dec).max_incl;
  uint8_t* workbuf = (uint8_t*)malloc((size_t)workbuf_len);
  if (workbuf == NULL) {
    return "could not allocate the decoder work buffer";
  }
  status = wuffs_png__decoder__decode_frame(
      &dec, &pb, &src, WUFFS_BASE__PIXEL_BLEND__SRC,
      wuffs_base__make_slice_u8(workbuf, (size_t)workbuf_len), NULL);
  free(workbuf);
  if (status.repr != NULL) {
    return status.repr;
  }

  // The frame must be the whole image, and there must be no second frame.
  status = wuffs_png__decoder__decode_frame_config(&dec, &fc, &src);
  if (status.repr != wuffs_base__note__end_of_data) {
    return "expected @end of data after the single frame";
  }
  return NULL;
}

// ---------------- main

int main(void) {
  // (1) The packaged file must be the versioned 0.4.0-alpha.10 release.
  check_u32((uint32_t)WUFFS_VERSION, 0x000040000u, "WUFFS_VERSION");
  check(strncmp(WUFFS_VERSION_STRING, "0.4.0-alpha.10", 14) == 0,
        "WUFFS_VERSION_STRING starts with 0.4.0-alpha.10");
  check(WUFFS_VERSION_PRE_RELEASE_LABEL[0] != '\0',
        "WUFFS_VERSION_PRE_RELEASE_LABEL is non-empty");

  // (2) Hashers over raw input.
  check_u32(crc32_of(g_png, sizeof g_png), WANT_CRC32_OF_PNG_FILE,
            "crc32 of the PNG file bytes");
  check_u32(header_only_tu_crc32_of_png(), WANT_CRC32_OF_PNG_FILE,
            "crc32 via the header-only translation unit");
  check_u32(crc32_of((const uint8_t*)"123456789", 9), 0xCBF43926u,
            "crc32 of the standard check value \"123456789\"");
  check_u32(adler32_of((const uint8_t*)"123456789", 9), 0x091E01DEu,
            "adler32 of the standard check value \"123456789\"");

  // (3) Real decode of the embedded PNG.
  const char* err = decode_png();
  check(err == NULL, err ? err : "decode_png");
  if (err == NULL) {
    check_u32(crc32_of(g_rgb, sizeof g_rgb), WANT_CRC32_OF_RGB,
              "crc32 of the decoded RGB pixels");
    check_u32(adler32_of(g_rgb, sizeof g_rgb), WANT_ADLER32_OF_RGB,
              "adler32 of the decoded RGB pixels");
    check_u32(cpp_tu_crc32_of_decoded_rgb(), WANT_CRC32_OF_RGB,
              "crc32 of the decoded RGB pixels, via the C++ consumer");
  }

  // (4) Error paths.
  {
    wuffs_png__decoder dec;
    wuffs_base__status status = wuffs_png__decoder__initialize(
        &dec, sizeof dec, 0xDEADBEEFu, 0);  // deliberately wrong version
    check(status.repr != NULL, "initialize with a wrong WUFFS_VERSION fails");
  }
  {
    wuffs_png__decoder dec;
    wuffs_base__status status = wuffs_png__decoder__initialize(
        &dec, sizeof dec, WUFFS_VERSION,
        WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED);
    check(status.repr == NULL, "initialize");
    // Only the 8-byte PNG signature, marked as a complete input.
    wuffs_base__io_buffer src = wuffs_base__ptr_u8__reader(
        (uint8_t*)g_png, 8, true);
    wuffs_base__image_config ic = ((wuffs_base__image_config){});
    status = wuffs_png__decoder__decode_image_config(&dec, &ic, &src);
    check(status.repr != NULL, "truncated closed input reports an error");
    check(status.repr != wuffs_base__suspension__short_read,
          "truncated closed input does not report short_read");
  }

  printf("OK: %d checks passed, %d failed\n", g_checks - g_failed, g_failed);
  return g_failed ? 1 : 0;
}
