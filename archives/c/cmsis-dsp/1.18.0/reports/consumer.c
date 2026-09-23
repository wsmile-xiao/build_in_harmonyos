/*
 * cmsis-dsp 1.18.0 — 消费者用例（业务上层组件视角）
 * 模拟业务应用仅通过库已安装/导出的公开头文件与链接目标使用 cmsis-dsp：
 *   - 仅 include <CMSIS-DSP/arm_math.h>（安装产物公开头）
 *   - 链接 libCMSISDSP.a
 *   - 调用公开 API 并验证可观察结果
 * 编译/链接/运行见 reports/consumer-run.md 记录的实命令。
 */
#include <stdio.h>
#include <math.h>
#include "arm_math.h"

int main(void)
{
    /* 业务意义: 传感器数据流上的 RMS 能量统计（公开 API: arm_rms_f32） */
    const float32_t samples[8] = {1.0f, -1.0f, 1.0f, -1.0f, 1.0f, -1.0f, 1.0f, -1.0f};
    float32_t rms = 0.0f;

    arm_rms_f32(samples, 8, &rms);

    printf("consumer: RMS=%.6f\n", rms);
    /* ±1 方波 RMS = 1.0 */
    if (fabsf(rms - 1.0f) > 1e-4f) {
        printf("consumer: FAIL (rms=%f != 1.0)\n", rms);
        return 1;
    }
    printf("consumer: cmsis-dsp 1.18.0 公开 API arm_rms_f32 验证通过\n");
    return 0;
}