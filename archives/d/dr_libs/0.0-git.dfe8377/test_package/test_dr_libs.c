/*
 * Consumer smoke test — dr_libs 0.0-git.dfe8377
 *
 * 1) 同一翻译单元编译三个头的实现段（三头共存编译验证）：
 *    DR_WAV_IMPLEMENTATION / DR_FLAC_IMPLEMENTATION / DR_MP3_IMPLEMENTATION
 * 2) 三头版本号字符串断言（锚定快照 dfe8377 的头版本）
 * 3) dr_wav 内存写读往返断言：内存构造 8kHz/1ch/16-bit/440 帧 ramp
 *    → drwav_init_memory_write 写出 → drwav_init_memory 读回，
 *    断言格式参数与解码样本逐帧一致（纯内存操作，无文件系统依赖）。
 */
#define DR_WAV_IMPLEMENTATION
#define DR_FLAC_IMPLEMENTATION
#define DR_MP3_IMPLEMENTATION

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "dr_wav.h"
#include "dr_flac.h"
#include "dr_mp3.h"

static int g_failures = 0;

static void check(int cond, const char *msg)
{
    if (!cond) {
        g_failures++;
        printf("  [FAIL] %s\n", msg);
    } else {
        printf("  [ OK ] %s\n", msg);
    }
}

int main(void)
{
    /* ── 1) 三头版本号断言（快照 dfe8377: 0.14.6 / 0.13.4 / 0.7.4）── */
    printf("dr_wav version:   %s\n", drwav_version_string());
    printf("dr_flac version:  %s\n", drflac_version_string());
    printf("dr_mp3 version:   %s\n", drmp3_version_string());
    check(strcmp(drwav_version_string(),  "0.14.6") == 0,
          "drwav_version_string() == \"0.14.6\"");
    check(strcmp(drflac_version_string(),  "0.13.4") == 0,
          "drflac_version_string() == \"0.13.4\"");
    check(strcmp(drmp3_version_string(),   "0.7.4")  == 0,
          "drmp3_version_string() == \"0.7.4\"");

    /* ── 2) dr_wav 内存写读往返 ── */
    const drwav_uint32 sampleRate = 8000;
    const drwav_uint32 channels   = 1;
    const drwav_uint32 bitsPerSample = 16;
    const drwav_uint64 frameCount = 440;

    /* ramp 波形：帧 i 的样本 = -16384 + i*16（与 dr_wav 0.13.17 归档
     * 测试同构，覆盖连续正值区间的有符号 16-bit 编码） */
    drwav_int16 *ramp =
        (drwav_int16 *)calloc((size_t)frameCount, sizeof(drwav_int16));
    if (!ramp) {
        printf("  [FAIL] calloc ramp\n");
        return 1;
    }
    for (drwav_uint64 i = 0; i < frameCount; i++) {
        ramp[i] = (drwav_int16)(-16384 + (drwav_int32)(i * 16));
    }

    /* 2a) 内存写出 */
    drwav_data_format format;
    memset(&format, 0, sizeof(format));
    format.container  = drwav_container_riff;
    format.format     = DR_WAVE_FORMAT_PCM;
    format.channels   = channels;
    format.sampleRate = sampleRate;
    format.bitsPerSample = bitsPerSample;

    void  *wavBlob = NULL;
    size_t wavSize = 0;
    drwav writer;
    check(drwav_init_memory_write(&writer, &wavBlob, &wavSize,
                                  &format, NULL) != 0,
          "drwav_init_memory_write() succeeds");
    drwav_uint64 written = drwav_write_pcm_frames(&writer, frameCount, ramp);
    check(written == frameCount, "drwav_write_pcm_frames() wrote 440 frames");
    check(drwav_uninit(&writer) == DRWAV_SUCCESS, "drwav_uninit(writer) returns DRWAV_SUCCESS (blob flushed)");
    check(wavBlob != NULL && wavSize > 44,
          "memory blob non-trivial (RIFF header + PCM payload)");

    /* 2b) 内存读回 */
    drwav reader;
    check(drwav_init_memory(&reader, wavBlob, wavSize, NULL) != 0,
          "drwav_init_memory() succeeds on the blob");
    check(reader.sampleRate == sampleRate,
          "readback sampleRate == 8000");
    check(reader.channels == channels,
          "readback channels == 1");
    check(reader.bitsPerSample == bitsPerSample,
          "readback bitsPerSample == 16");
    check(reader.totalPCMFrameCount == frameCount,
          "readback totalPCMFrameCount == 440");

    drwav_int16 *pcm =
        (drwav_int16 *)calloc((size_t)frameCount, sizeof(drwav_int16));
    if (!pcm) {
        printf("  [FAIL] calloc pcm\n");
        drwav_free(wavBlob, NULL);
        return 1;
    }
    drwav_uint64 readBack =
        drwav_read_pcm_frames_s16(&reader, frameCount, pcm);
    check(readBack == frameCount, "drwav_read_pcm_frames_s16() read 440 frames");

    /* 2c) 逐帧样本一致（ramp 无损往返：PCM16 → PCM16 无转换损失） */
    int mismatch = 0;
    for (drwav_uint64 i = 0; i < frameCount; i++) {
        if (pcm[i] != ramp[i]) { mismatch = 1; break; }
    }
    check(mismatch == 0, "all 440 readback samples identical to ramp (lossless round-trip)");
    /* 首帧值锚点：-16384 */
    check(pcm[0] == -16384, "first sample == -16384 (ramp start)");

    free(pcm);
    drwav_free(wavBlob, NULL);
    free(ramp);

    printf("\ndr_libs smoke test: %s (%d check(s) failed)\n",
           g_failures == 0 ? "PASS" : "FAIL", g_failures);
    return g_failures == 0 ? 0 : 1;
}
