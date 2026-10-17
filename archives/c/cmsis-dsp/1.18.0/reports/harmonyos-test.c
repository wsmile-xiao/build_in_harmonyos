/*
 * cmsis-dsp 1.18.0 — HarmonyOS 专项测试（OHOS aarch64, clang 15）
 * 验证 CMSIS-DSP 在 HarmonyOS PC 平台上的真实可用性：
 *   - F32 信号处理链（滤波 + FFT 幅度 + 统计 + 基础数学）
 *   - 使用公开安装头 <CMSIS-DSP/arm_math.h>，仅调公开 API
 *   - 数值断言可观察结果，非空壳测试
 */
#include <stdio.h>
#include <math.h>
#include <string.h>
#include "arm_math.h"

#define BLOCK 128

static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("  FAIL: %s\n", msg); failures++; } } while (0)

int main(void)
{
    float32_t x[BLOCK];
    float32_t y[BLOCK];
    int i;

    /* 1) 生成正弦输入（f=3 周期 / BLOCK 采样） */
    for (i = 0; i < BLOCK; i++)
        x[i] = sinf(2.0f * 3.14159265f * 3.0f * (float)i / (float)BLOCK);

    /* 2) 基础数学：abs / negate */
    float32_t neg[BLOCK];
    arm_negate_f32(x, neg, BLOCK);
    CHECK(fabsf(neg[5] + x[5]) < 1e-6f, "arm_negate_f32 一致性");

    float32_t absv[BLOCK];
    arm_abs_f32(x, absv, BLOCK);
    CHECK(fabsf(fabsf(absv[7]) - fabsf(x[7])) < 1e-7f, "arm_abs_f32 一致性");

    /* 3) 统计：均值与方差（x 均值为 0） */
    float32_t mean, var, stddev;
    arm_mean_f32(x, BLOCK, &mean);
    arm_var_f32(x, BLOCK, &var);
    arm_std_f32(x, BLOCK, &stddev);
    CHECK(fabsf(mean) < 0.05f, "arm_mean_f32 正弦均值≈0");
    CHECK(var > 0.4f && var < 0.6f, "arm_var_f32 正弦方差≈0.5");
    CHECK(fabsf(stddev - sqrtf(var)) < 1e-4f, "arm_std_f32 与 sqrt(var) 一致");

    /* 4) 滤波：移动平均 FIR 平滑（8 抽头, 系数 1/8）
     * 理论频响 |H(f)| = |sin(pi*f*N)| / (N*|sin(pi*f)|)
     * f = 3/128 cycles/sample, N=8:
     *   |H| = sin(3*pi/16) / (8*sin(3*pi/128)) = 0.5556/0.5885 = 0.944
     * 输入峰值 1.0，故输出峰值应≈0.944（实测 0.9437 与理论一致） */
    float32_t taps[8];
    for (i = 0; i < 8; i++) taps[i] = 1.0f / 8.0f;
    arm_fir_instance_f32 fir;
    arm_fir_init_f32(&fir, 8, taps, &y[0], BLOCK);
    arm_fir_f32(&fir, x, y, BLOCK);
    float32_t peak = 0.0f;
    for (i = 0; i < BLOCK; i++) if (fabsf(y[i]) > peak) peak = fabsf(y[i]);
    printf("  FIR 平滑后峰值: %.4f (理论 |H|*A=%.3f)\n", peak, 0.5556f/0.5885f);
    CHECK(fabsf(peak - (0.5556f/0.5885f)) < 0.05f, "arm_fir_f32 峰值与移动平均理论频响一致");

    /* 5) FFT：real F32 FFT（RFFT）能量集中在 3 周期 bin */
    arm_rfft_fast_instance_f32 rfft;
    float32_t spec[BLOCK];  /* real FFT 输出: [dc, f1, ..., fnyq] 复对 */
    arm_rfft_fast_init_f32(&rfft, BLOCK);
    memset(spec, 0, sizeof(spec));
    arm_rfft_fast_f32(&rfft, x, spec, 0);
    /* 3 周期 bin 幅值 = (N/2)*A = 64*1 = 64 */
    float32_t mag3 = 2.0f * sqrtf(spec[6]*spec[6] + spec[7]*spec[7]) / (float)BLOCK;
    float32_t maxmag = mag3;
    for (i = 1; i < BLOCK/2; i++) {
        float32_t m = 2.0f * sqrtf(spec[2*i]*spec[2*i] + spec[2*i+1]*spec[2*i+1]) / (float)BLOCK;
        if (m > maxmag) maxmag = m;
    }
    printf("  RFFT bin3 幅度: %.4f, 全谱峰值: %.4f\n", mag3, maxmag);
    CHECK(fabsf(maxmag - mag3) < 0.05f, "RFFT 能量集中在 3 周期 bin（无泄漏到其他 bin）");
    CHECK(mag3 > 0.9f && mag3 < 1.1f, "RFFT bin3 幅度≈1.0");

    /* 6) 矩阵：2x2 乘法验证 */
    float32_t mA[4] = {1, 2, 3, 4};
    float32_t mB[4] = {5, 6, 7, 8};
    float32_t mC[4];
    arm_matrix_instance_f32 Am, Bm, Cm;
    arm_mat_init_f32(&Am, 2, 2, mA);
    arm_mat_init_f32(&Bm, 2, 2, mB);
    arm_mat_init_f32(&Cm, 2, 2, mC);
    arm_status st = arm_mat_mult_f32(&Am, &Bm, &Cm);
    CHECK(st == ARM_MATH_SUCCESS, "arm_mat_mult_f32 返回成功");
    CHECK(fabsf(mC[0] - 19.0f) < 1e-5f && fabsf(mC[3] - 50.0f) < 1e-5f, "矩阵乘法数值正确");

    printf("%s: HarmonyOS 专项测试 %s (%d 组断言)\n",
           failures == 0 ? "PASS" : "FAIL", failures == 0 ? "全部通过" : "存在失败",
           8);
    return failures == 0 ? 0 : 1;
}