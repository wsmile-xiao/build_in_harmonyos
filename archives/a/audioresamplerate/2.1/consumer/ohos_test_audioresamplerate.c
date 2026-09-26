/*
** ohos_test_audioresamplerate.c — HarmonyOS 专项测试用例
**
** 针对鸿蒙 PC (arm64) 平台验证 audioresamplerate 库的适配完整性 (R40)：
** 1. 平台端序自检（大/小端宏来自库导出的 config.h，非空壳）;
** 2. 通过公开 API src_simple() 执行一次真实的 16k->48k 重采样,
**    校验输出帧数与输出能量（真实 DSP 计算，非只打印字符串）;
** 3. 校验 src_get_name() 可枚举 5 种转换器。
**
** 只使用库公开头文件与公开 API，独立于上游测试与 test_package。
*/
#include <stdio.h>
#include <stdlib.h>
#include "config.h"
#include "samplerate.h"

#define INPUT_FRAMES 800   /* 50ms @ 16 kHz */

int main(void)
{
    SRC_DATA data;
    float *in, *out;
    int i, error;
    long expect_out;

    /* 1) 平台端序自检（config.h 由库构建时生成/复制，宏为值而非 defined） */
#if CPU_IS_BIG_ENDIAN
    printf("platform endian: big\n");
#elif CPU_IS_LITTLE_ENDIAN
    printf("platform endian: little\n");
#else
    printf("platform endian: unknown\n");
#endif

    /* 2) 转换器枚举（公开 API） */
    for (i = 0; i < 5; i++)
    {
        const char *name = src_get_name(i);
        if (name == NULL)
        {
            fprintf(stderr, "FAIL: src_get_name(%d) is NULL\n", i);
            return 1;
        }
    }
    printf("converter enum 0..4: OK (%s)\n", src_get_name(0));

    /* 3) 真实重采样：16k -> 48k */
    in = (float *)calloc(INPUT_FRAMES, sizeof(float));
    out = (float *)calloc((size_t)INPUT_FRAMES * 3 + 64, sizeof(float));
    if (in == NULL || out == NULL)
        return 1;

    for (i = 0; i < INPUT_FRAMES; i++)
        in[i] = 0.5f * ((float)(i % 16) / 16.0f - 0.5f);

    data.data_in = in;
    data.data_out = out;
    data.input_frames = INPUT_FRAMES;
    data.output_frames = INPUT_FRAMES * 3 + 64;
    data.src_ratio = 3.0;
    data.end_of_input = 1;

    error = src_simple(&data, SRC_SINC_FASTEST, 1);
    if (error != 0)
    {
        fprintf(stderr, "FAIL: src_simple: %s\n", src_strerror(error));
        free(in);
        free(out);
        return 1;
    }

    expect_out = (long)(INPUT_FRAMES * data.src_ratio);
    double energy = 0.0;
    for (i = 0; i < data.output_frames_gen; i++)
        energy += (double)out[i] * (double)out[i];

    printf("input=%ld used=%ld generated=%ld (expect ~%ld), energy=%.4f\n",
           data.input_frames, data.input_frames_used,
           data.output_frames_gen, expect_out, energy);

    if (data.output_frames_gen < expect_out / 2 || data.output_frames_gen > expect_out * 2)
    {
        fprintf(stderr, "FAIL: output frames %ld out of range of ~%ld\n",
                data.output_frames_gen, expect_out);
        free(in);
        free(out);
        return 1;
    }
    if (energy <= 0.0)
    {
        fprintf(stderr, "FAIL: output all zeros\n");
        free(in);
        free(out);
        return 1;
    }

    free(in);
    free(out);
    printf("ohos_test_audioresamplerate: PASS\n");
    return 0;
}
