/* test_package for simde 0.8.2 — consumer-side validation of the simde
 * portable SIMD API. Exercises real simde neon/sse intrinsics (vadd,
 * vabd, vceq) and returns non-zero on any failed check.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <simde/arm/neon.h>
#include <simde/x86/sse2.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                  \
  do {                                               \
    checks++;                                        \
    if (!(cond)) {                                   \
      failures++;                                    \
      fprintf(stderr, "CHECK failed: %s (line %d)\n", #cond, __LINE__); \
    }                                                \
  } while (0)

int main(void) {
  /* simde_vaddq_s8: element-wise 8-bit signed add */
  const int8_t a[16] = { 1, 2, 3, 4, 5, 6, 7, 8, -1, -2, -3, -4, -5, -6, -7, -8 };
  const int8_t b[16] = { 9, 8, 7, 6, 5, 4, 3, 2,  1,  0, -1, -2, -3, -4, -5, -6 };
  simde_int8x16_t va = simde_vld1q_s8(a);
  simde_int8x16_t vb = simde_vld1q_s8(b);
  simde_int8x16_t vr = simde_vaddq_s8(va, vb);
  int8_t r[16];
  simde_vst1q_s8(r, vr);
  CHECK(r[0] == 10);
  CHECK(r[3] == 10);
  CHECK(r[8] == 0);
  CHECK(r[15] == -14);

  /* simde_vabdq_s16: element-wise absolute difference */
  const int16_t ca[8] = { 100, -50, 30, -20, 10, -5, 0, 7 };
  const int16_t cb[8] = { 50, 50, -30, 20, -10, 5, 0, -7 };
  simde_int16x8_t vca = simde_vld1q_s16(ca);
  simde_int16x8_t vcb = simde_vld1q_s16(cb);
  simde_int16x8_t vcr = simde_vabdq_s16(vca, vcb);
  int16_t cr[8];
  simde_vst1q_s16(cr, vcr);
  CHECK(cr[0] == 50);
  CHECK(cr[1] == 100);
  CHECK(cr[2] == 60);
  CHECK(cr[7] == 14);

  /* simde_vceqq_s32: element-wise compare equal */
  const int32_t ea[4] = { 1, 2, 3, 4 };
  const int32_t eb[4] = { 1, 9, 3, 8 };
  simde_int32x4_t vea = simde_vld1q_s32(ea);
  simde_int32x4_t veb = simde_vld1q_s32(eb);
  simde_uint32x4_t ver = simde_vceqq_s32(vea, veb);
  uint32_t er[4];
  simde_vst1q_u32(er, ver);
  CHECK(er[0] == UINT32_MAX);
  CHECK(er[1] == 0);
  CHECK(er[2] == UINT32_MAX);
  CHECK(er[3] == 0);

  /* simde_mm_add_epi32: x86 SSE2 path (portable implementation) */
  simde__m128i xa = simde_mm_set_epi32(4, 3, 2, 1);
  simde__m128i xb = simde_mm_set_epi32(10, 20, 30, 40);
  simde__m128i xr = simde_mm_add_epi32(xa, xb);
  CHECK(simde_mm_extract_epi32(xr, 0) == 41);
  CHECK(simde_mm_extract_epi32(xr, 1) == 32);
  CHECK(simde_mm_extract_epi32(xr, 3) == 14);

  printf("simde test_package: %d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
