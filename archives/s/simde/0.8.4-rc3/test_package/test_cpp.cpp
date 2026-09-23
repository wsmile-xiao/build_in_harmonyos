/* test_package for simde 0.8.4-rc3 — C++ 消费者验证。
 *
 * 上游 meson 矩阵对每个测试族同时注册 C 与 C++ 两个变体（本包上游测试统计
 * 中的 c/cpp 双份即来自该注册方式），因此消费者的 C++ 使用面必须单独取证：
 * 本 TU 以 C++ 编译同一组 simde 公开 API，确认头文件在 C++ 模式下（而非仅 C）
 * 可用、且便携路径在 C++ 重载/模板环境下结果一致。
 */
#include <cstdint>
#include <cstdio>
#include <cstring>

#include <simde/simde-common.h>
#include <simde/arm/neon.h>
#include <simde/x86/sse2.h>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                          \
  do {                                                                       \
    checks++;                                                                \
    if (!(cond)) {                                                           \
      failures++;                                                            \
      std::fprintf(stderr, "CHECK failed: %s (line %d)\n", #cond, __LINE__); \
    }                                                                        \
  } while (0)

int main() {
  const std::int16_t a[8] = { 1, -2, 3, -4, 5, -6, 7, -8 };
  const std::int16_t b[8] = { 10, 20, 30, 40, 50, 60, 70, 80 };
  simde_int16x8_t va = simde_vld1q_s16(a);
  simde_int16x8_t vb = simde_vld1q_s16(b);
  simde_int16x8_t vmax = simde_vmaxq_s16(va, vb);
  std::int16_t r[8];
  simde_vst1q_s16(r, vmax);
  CHECK(r[0] == 10);
  CHECK(r[1] == 20);
  CHECK(r[4] == 50);
  CHECK(r[7] == 80);

  simde_uint16x8_t vabs = simde_vcgtq_s16(vb, va);
  std::uint16_t ra[8];
  simde_vst1q_u16(ra, vabs);
  CHECK(ra[0] == 0xFFFFu);
  CHECK(ra[1] == 0xFFFFu);
  CHECK(ra[7] == 0xFFFFu);

  const float fa[4] = { 1.0f, 2.0f, 3.0f, 4.0f };
  const float fb[4] = { 0.5f, 0.25f, 0.125f, 0.0625f };
  simde_float32x4_t vf = simde_vmulq_f32(simde_vld1q_f32(fa), simde_vld1q_f32(fb));
  float rf[4];
  simde_vst1q_f32(rf, vf);
  CHECK(rf[0] == 0.5f);
  CHECK(rf[1] == 0.5f);
  CHECK(rf[2] == 0.375f);
  CHECK(rf[3] == 0.25f);

  simde__m128i xa = simde_mm_set_epi32(1, 2, 3, 4);
  simde__m128i xb = simde_mm_set_epi32(10, 20, 30, 40);
  simde__m128i xs = simde_mm_sub_epi32(xb, xa);
  CHECK(simde_mm_extract_epi32(xs, 0) == 36);
  CHECK(simde_mm_extract_epi32(xs, 3) == 9);

  CHECK(sizeof(simde_int16x8_t) == 16);
  CHECK(SIMDE_VERSION_MINOR == 8);
  CHECK(SIMDE_VERSION_MICRO == 4);

  std::printf("simde test_package (C++): %d checks, %d failures\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
