/*
 * test.c — drwav 0.14.5 consumer test (Bootstrap 骨架 + HarmonyOS 专项).
 *
 * 真实调用 drwav 公开 API：
 *   A. 内存构造 PCM 16-bit 单声道 8kHz 400Hz ramp WAV，用 drwav_init_memory
 *      解码，断言 sampleRate/channels/bitsPerSample/totalPCMFrameCount 与
 *      解码帧数（非空壳、非仅 include）。
 *   B. HarmonyOS 专项：用 drwav_init_file_write 在真实文件系统写一份 WAV，
 *      再用 drwav_init_file 读回并断言帧数一致——验证 OHOS 平台文件 I/O
 *      路径（aarch64-linux-ohos 原生编译运行）。
 * 任何断言失败 return 1。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DR_WAV_IMPLEMENTATION
#include "drwav/dr_wav.h"

static int g_failures = 0;

#define check(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);          \
            g_failures++;                                                    \
        }                                                                    \
    } while (0)

static int test_memory_decode(void)
{
    /* 构造一段 8kHz 单声道 16-bit 400Hz ramp 的 WAV（440 帧） */
    const drwav_uint32 sampleRate = 8000;
    const drwav_uint16 channels = 1;
    const drwav_uint16 bitsPerSample = 16;
    const drwav_uint64 frameCount = 440;
    const drwav_uint64 dataSize = frameCount * channels * (bitsPerSample / 8);

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
        drwav_uint32 byteRate = sampleRate * channels * (bitsPerSample / 8);
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
            samples[i] = (drwav_int16)(((i % 20) * 32767) / 20 - 16384);
        }
    }

    drwav wavObj;
    drwav_bool32 ok = drwav_init_memory(&wavObj, wav, wavSize, NULL);
    check(ok, "drwav_init_memory() returns DRWAV_TRUE");
    if (ok) {
        check(wavObj.sampleRate == sampleRate, "decoded sampleRate matches header");
        check(wavObj.channels == channels, "decoded channels matches header");
        check(wavObj.bitsPerSample == bitsPerSample, "decoded bitsPerSample matches header");
        check(wavObj.totalPCMFrameCount == frameCount, "totalPCMFrameCount == expected");

        drwav_int16 *pcm = (drwav_int16 *)calloc((size_t)frameCount * channels, sizeof(drwav_int16));
        if (pcm) {
            drwav_uint64 n = drwav_read_pcm_frames_s16(&wavObj, frameCount, pcm);
            check(n == frameCount, "decoded frame count == expected");
            check(pcm[0] >= -16488 && pcm[0] <= -16280, "first sample close to ramp start");
            free(pcm);
        } else {
            check(0, "calloc pcm out of memory");
        }
        drwav_uninit(&wavObj);
    }
    free(wav);
    return 0;
}

static int test_ohos_file_roundtrip(void)
{
    /* HarmonyOS 专项：真实文件写读回环（验证 OHOS 文件 I/O + 写路径） */
    const char *path = "drwav_ohos_roundtrip.wav";
    const drwav_uint32 sampleRate = 16000;
    const drwav_uint32 channels = 2;
    const drwav_uint32 bitsPerSample = 16;
    const drwav_uint64 frameCount = 512;

    drwav_data_format format;
    format.container = drwav_container_riff;
    format.format = DR_WAVE_FORMAT_PCM;
    format.channels = channels;
    format.sampleRate = sampleRate;
    format.bitsPerSample = bitsPerSample;

    drwav writer;
    if (!drwav_init_file_write(&writer, path, &format, NULL)) {
        fprintf(stderr, "FAIL: drwav_init_file_write failed\n");
        return 1;
    }
    {
        drwav_int16 samples[512 * 2];
        for (drwav_uint64 i = 0; i < frameCount; i++) {
            samples[i * 2] = (drwav_int16)(((i % 40) * 32767) / 40 - 16384);
            samples[i * 2 + 1] = samples[i * 2];
        }
        drwav_uint64 n = drwav_write_pcm_frames(&writer, frameCount, samples);
        check(n == frameCount, "written frame count == expected");
    }
    drwav_uninit(&writer);

    drwav reader;
    if (!drwav_init_file(&reader, path, NULL)) {
        fprintf(stderr, "FAIL: drwav_init_file (readback) failed\n");
        return 1;
    }
    check(reader.sampleRate == sampleRate, "readback sampleRate matches");
    check(reader.channels == channels, "readback channels matches");
    check(reader.totalPCMFrameCount == frameCount, "readback totalPCMFrameCount == expected");
    {
        drwav_int16 pcm[512 * 2];
        drwav_uint64 n = drwav_read_pcm_frames_s16(&reader, frameCount, pcm);
        check(n == frameCount, "readback decoded frame count == expected");
        check(pcm[0] == pcm[1], "readback stereo channels identical");
    }
    drwav_uninit(&reader);
    remove(path);
    return 0;
}

int main(void)
{
    /* 汇总两个测试函数的返回值：任何 init/alloc 失败分支（return 1）
       都必须使进程退出码非 0，不得被忽略（W4 审计 P1 修复）。 */
    int r1 = test_memory_decode();
    int r2 = test_ohos_file_roundtrip();

    if (r1 != 0 || r2 != 0 || g_failures > 0) {
        printf("drwav smoke test: FAIL (decode=%d roundtrip=%d, %d check(s) failed)\n",
               r1, r2, g_failures);
        return 1;
    }
    printf("drwav smoke test (decode + OHOS file roundtrip): PASS\n");
    return 0;
}
