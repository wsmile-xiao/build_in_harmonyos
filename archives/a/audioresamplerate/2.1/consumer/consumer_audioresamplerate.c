/*
** consumer_audioresamplerate.c — 消费者可用性用例 (业务上层组件视角)
**
** 模拟一个音视频业务上层组件：仅通过库安装后导出的公开头文件 samplerate.h
** 与公开 API（src_new / src_process / src_delete / src_get_version /
** src_strerror）使用 audioresamplerate 的 libresamplerate 库。
** 行为：将 16000Hz 单声道 0.1 秒音频流重采样到 48000Hz，
** 校验输出帧数、输出能量与采样率比，可观察结果即重采样输出。
**
** 不使用库私有头文件、内部符号或库内部测试构建目录。
*/
#include <stdio.h>
#include <stdlib.h>
#include "samplerate.h"

#define CHANNELS        1
#define INPUT_FRAMES    1600    /* 0.1s @ 16 kHz */
#define RATIO           3.0     /* 16k -> 48k */

int main(void)
{
    SRC_STATE *state = NULL;
    SRC_DATA data;
    float *in, *out;
    int error = 0;
    long expect_out;

    /* 公开 API: 版本查询 */
    printf("libsamplerate version: %s\n", src_get_version() ? src_get_version() : "(null)");

    /* 公开 API: 创建转换器状态 */
    state = src_new(SRC_SINC_MEDIUM_QUALITY, CHANNELS, &error);
    if (state == NULL)
    {
        fprintf(stderr, "FAIL: src_new: %s\n", src_strerror(error));
        return 1;
    }

    in = (float *)calloc(INPUT_FRAMES, sizeof(float));
    out = (float *)calloc((size_t)INPUT_FRAMES * 3 + 64, sizeof(float));
    if (in == NULL || out == NULL)
    {
        fprintf(stderr, "FAIL: calloc\n");
        return 1;
    }

    /* 业务输入：16kHz 单声道离散斜坡信号 */
    for (long i = 0; i < INPUT_FRAMES; i++)
        in[i] = 0.5f * ((float)(i % 20) / 20.0f - 0.5f);

    data.data_in = in;
    data.data_out = out;
    data.input_frames = INPUT_FRAMES;
    data.output_frames = INPUT_FRAMES * 3 + 64;
    data.src_ratio = RATIO;
    data.end_of_input = 1;

    /* 公开 API: 执行重采样 */
    if (src_process(state, &data) != 0)
    {
        fprintf(stderr, "FAIL: src_process: %s\n", src_strerror(src_error(state)));
        src_delete(state);
        free(in);
        free(out);
        return 1;
    }

    expect_out = (long)(INPUT_FRAMES * RATIO);
    printf("input=%ld used=%ld output_generated=%ld (expect ~%ld)\n",
           data.input_frames, data.input_frames_used,
           data.output_frames_gen, expect_out);

    if (data.output_frames_gen <= 0 || data.output_frames_gen < expect_out / 2 ||
        data.output_frames_gen > expect_out * 2)
    {
        fprintf(stderr, "FAIL: output frame count %ld out of range of ~%ld\n",
                data.output_frames_gen, expect_out);
        src_delete(state);
        free(in);
        free(out);
        return 1;
    }

    /* 可观察结果：输出非零（真实重采样发生） */
    double energy = 0.0;
    for (long i = 0; i < data.output_frames_gen; i++)
        energy += (double)out[i] * (double)out[i];
    printf("output energy = %.4f (%ld frames)\n", energy, data.output_frames_gen);
    if (energy <= 0.0)
    {
        fprintf(stderr, "FAIL: output all zeros\n");
        src_delete(state);
        free(in);
        free(out);
        return 1;
    }

    /* 公开 API: 释放状态 */
    src_delete(state);
    free(in);
    free(out);
    printf("consumer_audioresamplerate: PASS\n");
    return 0;
}
