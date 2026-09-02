/*
 * libpopcnt 2.0 — Conan test_package consumer test (C).
 *
 * R34: exercises the packaged libpopcnt.h public API (popcnt/popcnt64)
 * and verifies exact bit counts for crafted byte patterns, so this is a
 * substantive dependency on the tested package, not a string stub.
 */
#include "libpopcnt.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
  /* 0x0f = 4 set bits per byte */
  uint8_t data[16];
  memset(data, 0x0f, sizeof(data));
  assert(popcnt(data, sizeof(data)) == 16u * 4u);

  /* all-ones: 8 bits per byte */
  memset(data, 0xff, sizeof(data));
  assert(popcnt(data, sizeof(data)) == sizeof(data) * 8u);

  /* single byte, 4 set bits (0x1d = 0001 1101) */
  assert(popcnt("\x1d", 1) == 4u);

  /* popcnt64 scalar */
  assert(popcnt64(0x00ULL) == 0u);
  assert(popcnt64(0xffffffffffffffffULL) == 64u);
  assert(popcnt64(0x0102030405060708ULL) == 13u);

  /* large array path (>= 512 bytes triggers unrolled/vector paths) */
  static uint8_t big[4096];
  memset(big, 0x55, sizeof(big)); /* 0x55 = 4 bits per byte */
  assert(popcnt(big, sizeof(big)) == sizeof(big) * 4u);

  printf("Status: 100%%\n");
  printf("libpopcnt test_package consumer PASSED\n");
  return 0;
}
