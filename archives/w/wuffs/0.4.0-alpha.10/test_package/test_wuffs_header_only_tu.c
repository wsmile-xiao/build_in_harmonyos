// Copyright 2026 The OpenHarmony PC adaptation authors.
//
// SPDX-License-Identifier: Apache-2.0 OR MIT
//
// ----------------

// wuffs test_package consumer — second C translation unit, header mode.
//
// This TU includes the packaged file WITHOUT defining WUFFS_IMPLEMENTATION, so
// the codec structs stay opaque incomplete types (as Wuffs intends for every
// other translation unit) and only the declarations are visible. It is linked
// against test_wuffs.c, which carries the single implementation.
//
// The documented way to use an opaque codec from such a TU is to allocate
// sizeof__<type>() bytes and pass that size to initialize(); upstream's own
// comment on the opaque types says exactly that ("Use malloc or memcpy and the
// sizeof__wuffs_foo__bar function instead"). If the packaged file could not be
// used as a header, this TU would neither compile nor link.

#include "wuffs_test_config.h"

#include "test_data_png.h"

#include <stdlib.h>

uint32_t header_only_tu_crc32_of_png(void) {
  const size_t size = sizeof__wuffs_crc32__ieee_hasher();
  if (size == 0) {
    return 0;
  }
  uint8_t* mem = (uint8_t*)malloc(size);
  if (mem == NULL) {
    return 0;
  }

  wuffs_crc32__ieee_hasher* h = (wuffs_crc32__ieee_hasher*)mem;
  wuffs_base__status status = wuffs_crc32__ieee_hasher__initialize(
      h, size, WUFFS_VERSION,
      WUFFS_INITIALIZE__LEAVE_INTERNAL_BUFFERS_UNINITIALIZED);

  uint32_t checksum = 0;
  if (status.repr == NULL) {
    checksum = wuffs_crc32__ieee_hasher__update_u32(
        h, wuffs_base__make_slice_u8((uint8_t*)g_test_png,
                                     (size_t)sizeof g_test_png));
  }
  free(mem);
  return checksum;
}
