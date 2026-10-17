/*
 * psimd consumer test (C++) — HarmonyOS/OHOS aarch64.
 *
 * Layer 1 — backend activation gate (compile time):
 *   On aarch64 NEON is baseline; psimd.h activates its NEON intrinsic paths
 *   (arm_neon.h, vbslq_*, vfmaq_*) when EITHER __ARM_NEON__ OR __ARM_NEON is
 *   defined. The OHOS SDK clang (aarch64-unknown-linux-ohos, 15.0.4) predefines
 *   only the no-underscore spelling __ARM_NEON — the gate therefore accepts
 *   both, mirroring psimd.h's own guards. If neither is defined the backend
 *   silently degrades: fail the COMPILE, not the runtime.
 *
 * Layer 2 — API known-value assertions (12 checks):
 *   splat/add/sub/mul/min/max/abs/blend/signblend f32+s8 lanes, aligned
 *   load/store roundtrip, and the fused (qfma) cancellation case.
 *   All inputs go through opaque() so the optimizer cannot constant-fold the
 *   vector paths (at -O3 constant inputs fold away and leave ZERO vector
 *   instructions in the binary — observed on device).
 *
 * Layer 3 — instruction-level evidence (device verification, not CI):
 *   llvm-objdump on this binary must contain NEON vector instructions
 *   (bsl/bit/bif from psimd_blend_s8's vbslq_s8 path, fmla from
 *   psimd_qfma_f32's vfmaq_f32 path). See reports/knowledge-evidence.md for
 *   the executed commands, counts and negative controls.
 */
/*
 * Gate BEFORE including psimd.h: on a backend-degraded build (no NEON macro
 * on aarch64), psimd.h's own qfma path (`defined(__aarch64__)` branch using
 * float32x4_t without arm_neon.h) fails with a confusing undeclared-identifier
 * error before any consumer-level gate could fire — observed on device.
 * Firing here turns that into an actionable backend message.
 */
#if defined(__aarch64__) && !defined(__ARM_NEON__) && !defined(__ARM_NEON)
#error "psimd backend gate: neither __ARM_NEON__ nor __ARM_NEON defined on aarch64 - NEON paths (arm_neon.h/vbslq/vfmaq) would not activate"
#endif

#include <stdint.h>
#include <stdio.h>
#include <math.h>

#include <psimd.h>

static int g_failures = 0;

#define CHECK(cond, msg)                                  \
    do {                                                  \
        if (!(cond)) {                                    \
            fprintf(stderr, "FAIL: %s\n", (msg));         \
            g_failures++;                                 \
        }                                                 \
    } while (0)

/* Runtime-opaque value: defeats constant folding while preserving the value,
 * so vector code paths survive -O3 and are visible in disassembly. */
template <typename T>
static inline T opaque(T x)
{
#if defined(__GNUC__) || defined(__clang__)
    __asm__ volatile("" : "+r"(x) : : "memory");
#endif
    return x;
}

static int lanes4_eq_f32(psimd_f32 v, float e0, float e1, float e2, float e3)
{
    return v[0] == e0 && v[1] == e1 && v[2] == e2 && v[3] == e3;
}

int main(void)
{
    /* 1. splat */
    CHECK(lanes4_eq_f32(psimd_splat_f32(opaque(2.5f)), 2.5f, 2.5f, 2.5f, 2.5f),
          "psimd_splat_f32(2.5) lanes");

    /* 2. add */
    {
        float fa[4] = { opaque(1.0f), opaque(2.0f), opaque(3.0f), opaque(4.0f) };
        float fb[4] = { opaque(10.0f), opaque(20.0f), opaque(30.0f), opaque(40.0f) };
        CHECK(lanes4_eq_f32(psimd_add_f32(psimd_load_f32(fa), psimd_load_f32(fb)),
                            11.0f, 22.0f, 33.0f, 44.0f),
              "psimd_add_f32 known values");

        /* 3. sub */
        CHECK(lanes4_eq_f32(psimd_sub_f32(psimd_load_f32(fb), psimd_load_f32(fa)),
                            9.0f, 18.0f, 27.0f, 36.0f),
              "psimd_sub_f32 known values");

        /* 4. mul */
        CHECK(lanes4_eq_f32(psimd_mul_f32(psimd_load_f32(fa), psimd_splat_f32(opaque(2.0f))),
                            2.0f, 4.0f, 6.0f, 8.0f),
              "psimd_mul_f32 known values");

        /* 5. max / 6. min */
        float fc[4] = { opaque(3.0f), opaque(-2.0f), opaque(1.0f), opaque(-1.0f) };
        CHECK(lanes4_eq_f32(psimd_max_f32(psimd_load_f32(fa), psimd_load_f32(fc)),
                            3.0f, 2.0f, 3.0f, 4.0f),
              "psimd_max_f32 lane-wise max");
        CHECK(lanes4_eq_f32(psimd_min_f32(psimd_load_f32(fa), psimd_load_f32(fc)),
                            1.0f, -2.0f, 1.0f, -1.0f),
              "psimd_min_f32 lane-wise min");

        /* 7. abs */
        float fn[4] = { opaque(-1.0f), opaque(2.0f), opaque(-3.0f), opaque(4.0f) };
        CHECK(lanes4_eq_f32(psimd_abs_f32(psimd_load_f32(fn)),
                            1.0f, 2.0f, 3.0f, 4.0f),
              "psimd_abs_f32 lane-wise abs");

        /* 9. signblend_f32: x<0 -> a else b */
        CHECK(lanes4_eq_f32(psimd_signblend_f32(psimd_load_f32(fn),
                                                psimd_splat_f32(opaque(1.0f)),
                                                psimd_splat_f32(opaque(2.0f))),
                            1.0f, 2.0f, 1.0f, 2.0f),
              "psimd_signblend_f32 sign select");

        /* 10. aligned load/store roundtrip */
        float out[4];
        psimd_store_f32(out, psimd_load_f32(fa));
        CHECK(opaque(out[0]) == 1.0f && opaque(out[1]) == 2.0f &&
              opaque(out[2]) == 3.0f && opaque(out[3]) == 4.0f,
              "psimd_load_f32/psimd_store_f32 roundtrip");
    }

    /* 8. blend_s8 (NEON vbslq_s8 path on aarch64) */
    {
        int8_t mask_bytes[16];
        const int8_t pattern[16] = {
            -1, -1, -1, -1, 0, 0, 0, 0, -1, -1, 0, 0, -1, 0, -1, 0
        };
        for (int i = 0; i < 16; i++) {
            mask_bytes[i] = opaque(pattern[i]);
        }
        const psimd_s8 mask = psimd_load_s8(mask_bytes);
        const psimd_s8 x = psimd_splat_s8(opaque((int8_t) 0x55));
        const psimd_s8 y = psimd_splat_s8(opaque((int8_t) 0xAA));
        int8_t out[16];
        psimd_store_s8(out, psimd_blend_s8(mask, x, y));
        int ok = 1;
        for (int i = 0; i < 16; i++) {
            const int8_t want = pattern[i] ? (int8_t) 0x55 : (int8_t) 0xAA;
            if (opaque(out[i]) != want) {
                ok = 0;
            }
        }
        CHECK(ok, "psimd_blend_s8 bit select (vbslq path)");
    }

    /* 11./12. qfma fused cancellation: fa*fb = 1 - 2^-46 exactly;   */
    /* (fa*fb) - 1 = -2^-46 only with a single rounding.             */
    /* Unfused evaluation gives round(1 - 2^-46) - 1 = 0.0f.         */
    {
        const float eps = opaque(1.0f) / 8388608.0f; /* 2^-23, exact in float */
        const float fa = opaque(1.0f + eps);         /* nextafter(1, 2) */
        const float fb = opaque(1.0f - eps);         /* nextafter(1, 0) */
        const psimd_f32 got = psimd_qfma_f32(psimd_splat_f32(opaque(-1.0f)),
                                             psimd_splat_f32(fa),
                                             psimd_splat_f32(fb));
        const float want = fmaf(fa, fb, -1.0f); /* libc fused reference */
        CHECK(lanes4_eq_f32(got, want, want, want, want) && want != 0.0f,
              "psimd_qfma_f32 fused single-rounding (== fmaf, != 0)");
    }

    if (g_failures == 0) {
        printf("test_psimd: OK (psimd API verified; aarch64 NEON gate passed at compile time)\n");
        return 0;
    }
    printf("test_psimd: FAILED (%d checks failed)\n", g_failures);
    return 1;
}
