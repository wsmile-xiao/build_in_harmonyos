// Copyright 2026 The OpenHarmony PC adaptation authors.
//
// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// ----------------

// wuffs test_package consumer — C++ translation unit, header mode.
//
// Includes the packaged file from C++ without WUFFS_IMPLEMENTATION and links
// against the C implementation translation unit. In that mode Wuffs' codec
// structs are deliberately opaque (default construction is deleted, and the
// struct carries dead weight so that `sizeof T` differs from the real size),
// so this TU uses the C++ convenience layer instead:
//
//   wuffs_png__decoder::alloc()  ->  std::unique_ptr, freed automatically
//   dec->decode_image_config(...) etc., the C++ wrappers around the C API
//
// This is the multi-translation-unit use Wuffs documents for its single file C
// library (see example/toy-genlib, which links such a TU against libwuffs). It
// checks that the packaged file is accepted by a C++ compiler, that its C++
// layer works, and that C and C++ translation units of one program share a
// single implementation without duplicate-symbol or linkage problems.

#include "wuffs_test_config.h"

#include "test_data_png.h"

#include <vector>

uint32_t cpp_tu_crc32_of_decoded_rgb(void) {
  wuffs_png__decoder::unique_ptr dec = wuffs_png__decoder::alloc();
  if (!dec) {
    return 0;
  }

  wuffs_base__io_buffer src = wuffs_base__ptr_u8__reader(
      const_cast<uint8_t*>(g_test_png), (size_t)sizeof g_test_png, true);

  wuffs_base__image_config ic = wuffs_base__null_image_config();
  wuffs_base__status status = dec->decode_image_config(&ic, &src);
  if (status.repr != nullptr) {
    return 0;
  }

  // 24bpp RGB, so the decoded bytes are directly comparable with the C TU's.
  wuffs_base__pixel_config__set(
      &ic.pixcfg, WUFFS_BASE__PIXEL_FORMAT__RGB,
      WUFFS_BASE__PIXEL_SUBSAMPLING__NONE, TEST_PNG_WIDTH, TEST_PNG_HEIGHT);

  std::vector<uint8_t> pixels(
      (size_t)TEST_PNG_WIDTH * (size_t)TEST_PNG_HEIGHT * 3);

  wuffs_base__pixel_buffer pb = wuffs_base__null_pixel_buffer();
  status = wuffs_base__pixel_buffer__set_from_slice(
      &pb, &ic.pixcfg,
      wuffs_base__make_slice_u8(pixels.data(), pixels.size()));
  if (status.repr != nullptr) {
    return 0;
  }

  wuffs_base__frame_config fc = wuffs_base__null_frame_config();
  status = dec->decode_frame_config(&fc, &src);
  if (status.repr != nullptr) {
    return 0;
  }

  // decode_frame needs a scratch buffer of at least the decoder's advertised
  // workbuf length (upstream's own callers size theirs from workbuf_len()).
  const uint64_t workbuf_len = dec->workbuf_len().max_incl;
  std::vector<uint8_t> workbuf((size_t)workbuf_len);

  status = dec->decode_frame(
      &pb, &src, WUFFS_BASE__PIXEL_BLEND__SRC,
      wuffs_base__make_slice_u8(workbuf.data(), workbuf.size()), nullptr);
  if (status.repr != nullptr) {
    return 0;
  }

  wuffs_crc32__ieee_hasher::unique_ptr hasher =
      wuffs_crc32__ieee_hasher::alloc();
  if (!hasher) {
    return 0;
  }
  return hasher->update_u32(
      wuffs_base__make_slice_u8(pixels.data(), pixels.size()));
}
