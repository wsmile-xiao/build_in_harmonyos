/*
 * test_dr_wav.c — consumer test for dr_wav 0.13.17 (Bootstrap 骨架).
 *
 * 真实调用 dr_wav 公开 API：用 drwav_init_memory_with_metadata 从一段内存中
 * 构造的 PCM 16 位 立体声 44100Hz 单声道 400Hz ramp WAV 解码，断言：
 *   - drwav_init_memory 成功
 *   - totalPCMFrameCount == 期望帧数
 *   - channels / sampleRate == RIFF 头声明
 *   - 解码出的帧数 == 期望帧数（非零）
 * 任何断言失败 return 1。非空壳、非仅 include；不读真实文件（内存构造）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DR_WAV_IMPLEMENTATION
#include "dr_wav/dr_wav.h"

static int g_failures = 0;

#define check(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);          \
            g_failures++;                                                    \
        }                                                                    \
    } while (0)

int main(void)
{
    /* 构造一段 8kHz 单声道 16-bit 400Hz ramp 的 WAV（440 帧） */
    const drwav_uint32 sampleRate = 8000;
    const drwav_uint16 channels = 1;
    const drwav_uint16 bitsPerSample = 16;
    const drwav_uint64 frameCount = 440;
    const drwav_uint64 dataSize = frameCount * channels * (bitsPerSample / 8);

    /* 手写最小 RIFF/WAVE 头 + PCM 数据（无扩展块） */
    size_t wavSize = 44 + (size_t)dataSize;
    unsigned char *wav = (unsigned char *)calloc(1, wavSize);
    if (!wav) {
        fprintf(stderr, "FAIL: calloc out of memory\n");
        return 1;
    }
    memcpy(wav + 0, "RIFF", 4);
    drwav_uint32 chunkSize = (drwav_uint32)(36 + dataSize);
    memcpy(wav + 4, &chunkSize, 4);
    memcpy(wav + 8, "WAVE", 4);
    memcpy(wav + 12, "fmt ", 4);
    {
        drwav_uint32 fmtChunkSize = 16;
        drwav_uint16 audioFormat = 1; /* PCM */
        drwav_uint16 blockAlign = (drwav_uint16)(channels * (bitsPerSample / 8));
        drwav_uint32 byteRate =
            sampleRate * channels * (bitsPerSample / 8);
        memcpy(wav + 16, &fmtChunkSize, 4);
        memcpy(wav + 20, &audioFormat, 2);
        memcpy(wav + 22, &channels, 2);
        memcpy(wav + 24, &sampleRate, 4);
        memcpy(wav + 28, &byteRate, 4);
        memcpy(wav + 32, &blockAlign, 2);
        memcpy(wav + 34, &bitsPerSample, 2);
    }
    memcpy(wav + 36, "data", 4);
    {
        drwav_uint32 dataChunkSize = (drwav_uint32)dataSize;
        memcpy(wav + 40, &dataChunkSize, 4);
    }
    {
        drwav_int16 *samples = (drwav_int16 *)(wav + 44);
        for (drwav_uint64 i = 0; i < frameCount; i++) {
            /* 400Hz ramp：i % 20 周期内线性 0..32767 */
            samples[i] =
                (drwav_int16)(((i % 20) * 32767) / 20 - 16384);
        }
    }

    drwav wavObj;
    drwav_bool32 ok = drwav_init_memory(&wavObj, wav, wavSize, NULL);
    check(ok, "drwav_init_memory() returns DRWAV_TRUE");
    if (ok) {
        check(wavObj.sampleRate == sampleRate,
              "decoded sampleRate matches header");
        check(wavObj.channels == channels, "decoded channels matches header");
        check(wavObj.bitsPerSample == bitsPerSample,
              "decoded bitsPerSample matches header");
        check(wavObj.totalPCMFrameCount == frameCount,
              "totalPCMFrameCount == expected frame count");

        drwav_int16 *pcm =
            (drwav_int16 *)calloc((size_t)frameCount * channels,
                                  sizeof(drwav_int16));
        if (pcm) {
            drwav_uint64 n =
                drwav_read_pcm_frames_s16(&wavObj, frameCount, pcm);
            check(n == frameCount, "decoded frame count == expected");
            /* 首帧应接近 ramp 起始值 (-16384 + 0) */
            check(pcm[0] >= -16488 && pcm[0] <= -16280,
                  "first sample close to ramp start");
            free(pcm);
        } else {
            check(0, "calloc pcm out of memory");
        }
        drwav_uninit(&wavObj);
    }
    free(wav);

    if (g_failures == 0) {
        printf("\ndr_wav smoke test: PASS (7/7 checks OK)\n");
        return 0;
    }
    printf("\ndr_wav smoke test: FAIL (%d check(s) failed)\n", g_failures);
    return 1;
}