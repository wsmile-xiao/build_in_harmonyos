/* test_package for simde 0.8.4-rc3 — 原生别名层验证（OHOS aarch64 能力项）。
 *
 * simde 的原生别名层（SIMDE_ENABLE_NATIVE_ALIASES）把 NEON 短名（vaddq_s8 等）
 * 映射到目标平台原生指令；在 OHOS/aarch64 上这必须是真正走 arm_neon.h 原生
 * intrinsic，而不是退回标量模拟。本 TU：
 *   1. 断言 SIMDE_ARM_NEON_A64V8_NATIVE 已定义（原生 A64 NEON 路径生效）；
 *   2. 对同一输入分别调用短名（原生 intrinsic）与 simde_ 前缀接口，比对结果一致；
 *   3. 断言向量类型与原生类型同尺寸（simde_int8x16_t 即 int8x16_t）。
 * 该验证覆盖「simde 在 OHOS 上正确识别原生 NEON 能力」这一平台语义。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define SIMDE_ENABLE_NATIVE_ALIASES
#include <simde/arm/neon.h>

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
#if defined(SIMDE_ARM_NEON_A64V8_NATIVE)
  const int simde_native_a64v8 = 1;
#else
  const int simde_native_a64v8 = 0;
#endif
#if defined(__aarch64__)
  /* OHOS aarch64：simde 必须走原生 A64 NEON 路径（而非标量模拟） */
  const int expect_native_a64v8 = 1;
  CHECK(simde_native_a64v8 == 1);
  CHECK(sizeof(simde_int8x16_t) == sizeof(int8x16_t));
  CHECK(sizeof(simde_int16x8_t) == sizeof(int16x8_t));
  CHECK(sizeof(simde_float32x4_t) == sizeof(float32x4_t));
#else
  const int expect_native_a64v8 = 0;
  CHECK(simde_native_a64v8 == 0);
  printf("platform: non-aarch64 (native NEON alias equivalence checks skipped)\n");
#endif
  printf("SIMDE_ARM_NEON_A64V8_NATIVE=%d (expected %d)\n",
         simde_native_a64v8, expect_native_a64v8);

  const int8_t a8[16] = { 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 };
  const int8_t b8[16] = { 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1 };
  int8_t alias_r[16], simde_r[16];
  simde_vst1q_s8(alias_r, vaddq_s8(simde_vld1q_s8(a8), simde_vld1q_s8(b8)));
  simde_vst1q_s8(simde_r, simde_vaddq_s8(simde_vld1q_s8(a8), simde_vld1q_s8(b8)));
  CHECK(memcmp(alias_r, simde_r, sizeof(alias_r)) == 0);
  CHECK(alias_r[0] == 17);
  CHECK(alias_r[15] == 17);

  const int32_t a32[4] = { -7, 11, -13, 17 };
  const int32_t b32[4] = { 7, -11, 13, -17 };
  int32_t alias32[4], simde32[4];
  simde_vst1q_s32(alias32, vmaxq_s32(simde_vld1q_s32(a32), simde_vld1q_s32(b32)));
  simde_vst1q_s32(simde32, simde_vmaxq_s32(simde_vld1q_s32(a32), simde_vld1q_s32(b32)));
  CHECK(memcmp(alias32, simde32, sizeof(alias32)) == 0);
  CHECK(alias32[0] == 7);
  CHECK(alias32[1] == 11);
  CHECK(alias32[2] == 13);
  CHECK(alias32[3] == 17);

  const uint16_t ua[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };
  const uint16_t ub[8] = { 8, 7, 6, 5, 4, 3, 2, 1 };
  uint16_t aliasu[8], simdeu[8];
  simde_vst1q_u16(aliasu, vmulq_u16(simde_vld1q_u16(ua), simde_vld1q_u16(ub)));
  simde_vst1q_u16(simdeu, simde_vmulq_u16(simde_vld1q_u16(ua), simde_vld1q_u16(ub)));
  CHECK(memcmp(aliasu, simdeu, sizeof(aliasu)) == 0);
  CHECK(aliasu[0] == 8);
  CHECK(aliasu[7] == 8);

  printf("simde test_package (native aliases): %d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
