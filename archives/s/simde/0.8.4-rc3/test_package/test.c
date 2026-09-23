/* test_package for simde 0.8.4-rc3 — consumer-side validation of the simde
 * portable SIMD API on OHOS/aarch64.
 *
 * 三层真实调用（R34：全部为被测产物的公开 API，非 print-only）：
 *   1. ARM NEON 便携接口（simde_vld1q_s8 / simde_vaddq_s8 / simde_vabdq_s16 /
 *      simde_vceqq_s32 / simde_vmulq_s32 / simde_vmaxq_s16 / simde_vaddq_f32）；
 *   2. 跨 ISA 便携路径（x86 SSE2、wasm simd128、mips MSA 在 aarch64 上的回退实现）；
 *   3. 平台能力（版本宏、向量类型尺寸、SIMDE_ARCH_ARM_NEON 原生探测）。
 *
 * 每个 CHECK 递增计数，失败打印文件行号；退出码非零即失败。
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include <simde/simde-common.h>
#include <simde/simde-arch.h>
#include <simde/arm/neon.h>
#include <simde/x86/sse2.h>
#include <simde/wasm/simd128.h>
#include <simde/mips/msa.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                          \
  do {                                                                       \
    checks++;                                                                \
    if (!(cond)) {                                                           \
      failures++;                                                            \
      fprintf(stderr, "CHECK failed: %s (line %d)\n", #cond, __LINE__);      \
    }                                                                        \
  } while (0)

int main(void) {
  /* ── 1. NEON 便携接口 ─────────────────────────────────────────────── */
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

  simde_int32x4_t vmul = simde_vmulq_s32(vea, veb);
  int32_t mr[4];
  simde_vst1q_s32(mr, vmul);
  CHECK(mr[0] == 1);
  CHECK(mr[1] == 18);
  CHECK(mr[2] == 9);
  CHECK(mr[3] == 32);

  const int16_t na[8] = { -5, 7, -3, 9, 0, -1, 12, -8 };
  const int16_t nb[8] = { 3, -7, 11, -9, 0, 1, -12, 8 };
  simde_int16x8_t vnr = simde_vmaxq_s16(simde_vld1q_s16(na), simde_vld1q_s16(nb));
  int16_t nr[8];
  simde_vst1q_s16(nr, vnr);
  CHECK(nr[0] == 3);
  CHECK(nr[1] == 7);
  CHECK(nr[6] == 12);
  CHECK(nr[7] == 8);

  const float fa[4] = { 1.5f, -2.5f, 3.5f, 0.0f };
  const float fb[4] = { 2.25f, 2.5f, -1.5f, 4.0f };
  simde_float32x4_t vfr = simde_vaddq_f32(simde_vld1q_f32(fa), simde_vld1q_f32(fb));
  float fr[4];
  simde_vst1q_f32(fr, vfr);
  CHECK(fr[0] == 3.75f);
  CHECK(fr[1] == 0.0f);
  CHECK(fr[2] == 2.0f);
  CHECK(fr[3] == 4.0f);
  CHECK(simde_vgetq_lane_s32(vea, 2) == 3);

  /* ── 2. 跨 ISA 便携路径（在 aarch64 上走回退实现） ────────────────── */
  simde__m128i xa = simde_mm_set_epi32(4, 3, 2, 1);
  simde__m128i xb = simde_mm_set_epi32(10, 20, 30, 40);
  simde__m128i xr = simde_mm_add_epi32(xa, xb);
  CHECK(simde_mm_extract_epi32(xr, 0) == 41);
  CHECK(simde_mm_extract_epi32(xr, 1) == 32);
  CHECK(simde_mm_extract_epi32(xr, 3) == 14);

  const int32_t wa[4] = { 7, -8, 9, -10 };
  const int32_t wb[4] = { 3, 8, -9, 10 };
  simde_v128_t vwa = simde_wasm_v128_load(wa);
  simde_v128_t vwb = simde_wasm_v128_load(wb);
  simde_v128_t vwr = simde_wasm_i32x4_add(vwa, vwb);
  int32_t wr[4];
  simde_wasm_v128_store(wr, vwr);
  CHECK(simde_wasm_i32x4_extract_lane(vwr, 0) == 10);
  CHECK(simde_wasm_i32x4_extract_lane(vwr, 1) == 0);
  CHECK(wr[2] == 0);
  CHECK(wr[3] == 0);
  int32_t wround[4];
  simde_wasm_v128_store(wround, vwa);
  CHECK(memcmp(wa, wround, sizeof(wa)) == 0);

  const int32_t ma[4] = { 1000000, -2000000, 3, -4 };
  const int32_t mb[4] = { 2000000, 2000000, -30, 40 };
  simde_v4i32 vma = simde_msa_ld_w(ma, 0);
  simde_v4i32 vmb = simde_msa_ld_w(mb, 0);
  simde_v4i32 vmr = simde_msa_addv_w(vma, vmb);
  int32_t mr2[4];
  simde_msa_st_w(vmr, mr2, 0);
  CHECK(mr2[0] == 3000000);
  CHECK(mr2[1] == 0);
  CHECK(mr2[2] == -27);
  CHECK(mr2[3] == 36);

  /* ── 3. 平台能力（版本 / 类型尺寸 / 原生 NEON 探测） ─────────────── */
  CHECK(SIMDE_VERSION_MAJOR == 0);
  CHECK(SIMDE_VERSION_MINOR == 8);
  CHECK(SIMDE_VERSION_MICRO == 4);
  CHECK(sizeof(simde_int8x16_t) == 16);
  CHECK(sizeof(simde_int32x4_t) == 16);
  CHECK(sizeof(simde_float32x4_t) == 16);

#if defined(__aarch64__)
  /* OHOS aarch64：simde 必须探测到原生 NEON（而非退回标量模拟） */
  CHECK(SIMDE_ARCH_ARM_NEON != 0);
  CHECK(SIMDE_ARCH_AARCH64 != 0);
  printf("platform: aarch64, SIMDE_ARCH_ARM_NEON=%d SIMDE_ARCH_AARCH64=%d\n",
         (int) SIMDE_ARCH_ARM_NEON, (int) SIMDE_ARCH_AARCH64);
#else
  printf("platform: non-aarch64 (native NEON capacity checks skipped)\n");
#endif

  printf("simde test_package (C): %d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
