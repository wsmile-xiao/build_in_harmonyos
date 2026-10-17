/*
 * libpopcnt 2.0 — HarmonyOS PC (aarch64) specific verification test (C).
 *
 * Part of the libpopcnt 2.0 local delivery evidence (R02 adapt).
 * Calls the real libpopcnt public API (`popcnt`/`popcnt64`) with crafted and
 * large-array inputs and verifies exact bit counts on the OHOS aarch64
 * verification path (host aarch64 userland, clang 15.0.4 OHOS toolchain from
 * /data/service/hnp/bin). Runtime CPU feature detection chooses
 * POPCNT/AVX2/AVX512/NEON automatically; the large-array case exercises the
 * vectorized path on this platform.
 */
#include "libpopcnt.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
  /* crafted byte pattern: 0x0f = 4 set bits per byte */
  uint8_t data[16];
  memset(data, 0x0f, sizeof(data));
  assert(popcnt(data, sizeof(data)) == 16u * 4u);

  /* all-ones array: 8 bits per byte */
  memset(data, 0xff, sizeof(data));
  assert(popcnt(data, sizeof(data)) == sizeof(data) * 8u);

  /* single byte with 4 set bits (0x1d = 0001 1101) */
  assert(popcnt("\x1d", 1) == 4u);

  /* scalar popcnt64 */
  assert(popcnt64(0x00ULL) == 0u);
  assert(popcnt64(0xffffffffffffffffULL) == 64u);
  assert(popcnt64(0x0102030405060708ULL) == 13u);

  /* large array path (>= 512 bytes triggers unrolled/vector code) */
  static uint8_t big[4096];
  memset(big, 0x55, sizeof(big)); /* 0x55 = 4 bits per byte */
  assert(popcnt(big, sizeof(big)) == sizeof(big) * 4u);

  printf("[hmos] libpopcnt real popcnt API checks PASSED (crafted + large-array)\n");
  printf("[hmos] ALL HARMONYOS-SPECIFIC TESTS PASSED\n");
  return 0;
}
