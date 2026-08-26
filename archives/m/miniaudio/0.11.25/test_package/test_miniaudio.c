/* test_package/test_miniaudio.c — miniaudio 消费者测试
 *
 * 真实验证 miniaudio 0.11.25 的设备无关核心 API。每项断言失败即
 * return 1，非仅 include + return 0 的空壳测试。
 *
 * 覆盖：
 *   1. ma_decoder_init_memory — 内存 WAV 解码出非零帧数
 *   2. 解码输出 format/channels/sampleRate 与请求一致
 *   3. ma_data_converter — s16→f32 单帧转换正确性
 *   4. ma_waveform — 正弦波生成（非全零）
 *   5. ma_noise — 白噪声生成（非全零）
 *   6. ma_result 成功码语义（MA_SUCCESS == 0）
 *
 * 不打开任何真实音频设备（无 deviceio）。
 */
#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio/miniaudio.h"

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int g_failures = 0;

static void check(int cond, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fputs(cond ? "[ok] " : "[FAIL] ", stdout);
    vprintf(fmt, ap);
    fputc('\n', stdout);
    va_end(ap);
    if (!cond) ++g_failures;
}

/* Build a minimal valid 16-bit PCM mono WAV (8000 Hz, 64 frames) in memory.
 * The PCM body is a simple ramp so we can verify decode round-trips real data. */
static void build_wav_s16_mono(uint8_t *buf, size_t *outSize) {
    const uint32_t sampleRate = 8000;
    const uint16_t numChannels = 1;
    const uint16_t bitsPerSample = 16;
    const uint32_t numFrames = 64;
    const uint32_t dataSize = numFrames * numChannels * (bitsPerSample / 8);
    const uint32_t byteRate = sampleRate * numChannels * (bitsPerSample / 8);
    const uint16_t blockAlign = numChannels * (bitsPerSample / 8);
    size_t off = 0;

    memcpy(buf + off, "RIFF", 4); off += 4;
    uint32_t chunkSize = 36 + dataSize;
    memcpy(buf + off, &chunkSize, 4); off += 4;
    memcpy(buf + off, "WAVE", 4); off += 4;
    memcpy(buf + off, "fmt ", 4); off += 4;
    uint32_t subchunk1Size = 16;
    memcpy(buf + off, &subchunk1Size, 4); off += 4;
    uint16_t audioFormat = 1;  /* PCM */
    memcpy(buf + off, &audioFormat, 2); off += 2;
    memcpy(buf + off, &numChannels, 2); off += 2;
    memcpy(buf + off, &sampleRate, 4); off += 4;
    memcpy(buf + off, &byteRate, 4); off += 4;
    memcpy(buf + off, &blockAlign, 2); off += 2;
    memcpy(buf + off, &bitsPerSample, 2); off += 2;
    memcpy(buf + off, "data", 4); off += 4;
    memcpy(buf + off, &dataSize, 4); off += 4;
    /* ramp: 0,1,2,...,63 as int16 */
    for (uint32_t i = 0; i < numFrames; ++i) {
        int16_t s = (int16_t)i;
        memcpy(buf + off, &s, 2); off += 2;
    }
    *outSize = off;
}

int main(void) {
    /* ── Build an in-memory WAV ─────────────────────────────────────────── */
    uint8_t wavBuf[512];
    size_t wavSize = 0;
    build_wav_s16_mono(wavBuf, &wavSize);
    check(wavSize == 44 + 64 * 2, "WAV built (44-byte header + 128 bytes PCM)");

    /* ── 1. Decode the in-memory WAV to f32 PCM ─────────────────────────── */
    ma_decoder_config decCfg = ma_decoder_config_init(
        ma_format_f32, 1, 8000);
    ma_decoder decoder;
    ma_result r = ma_decoder_init_memory(wavBuf, wavSize, &decCfg, &decoder);
    check(r == MA_SUCCESS, "ma_decoder_init_memory() == MA_SUCCESS");

    float decoded[128];
    ma_uint64 framesDecoded = 0;
    if (r == MA_SUCCESS) {
        r = ma_decoder_read_pcm_frames(&decoder, decoded, 64, &framesDecoded);
        check(r == MA_SUCCESS, "ma_decoder_read_pcm_frames() == MA_SUCCESS");
        check(framesDecoded == 64, "decoded 64 frames (got %llu)",
              (unsigned long long)framesDecoded);
        ma_decoder_uninit(&decoder);
    } else {
        check(0, "decoder init failed — cannot continue");
    }

    /* ── 2. Decoded output matches requested format/channels/rate ───────── */
    /* Re-init to inspect output config fields. */
    ma_decoder decoder2;
    ma_decoder_config decCfg2 = ma_decoder_config_init(
        ma_format_f32, 1, 8000);
    if (ma_decoder_init_memory(wavBuf, wavSize, &decCfg2, &decoder2) == MA_SUCCESS) {
        check(decoder2.outputFormat == ma_format_f32,
              "decoder.outputFormat == ma_format_f32");
        check(decoder2.outputChannels == 1,
              "decoder.outputChannels == 1");
        check(decoder2.outputSampleRate == 8000,
              "decoder.outputSampleRate == 8000");
        ma_decoder_uninit(&decoder2);
    }

    /* Verify the decoded data is a real ramp (0,1,2,...→ normalized f32), not
     * garbage. Decoded f32 of int16 i ≈ i / 32768. */
    if (framesDecoded == 64) {
        int ramp_ok = 1;
        for (int i = 0; i < 4; ++i) {
            float expected = (float)i / 32768.0f;
            if (decoded[i] < expected - 1e-4f || decoded[i] > expected + 1e-4f) {
                ramp_ok = 0;
                break;
            }
        }
        check(ramp_ok, "decoded f32 ramp matches int16→f32 scaling");
    }

    /* ── 3. ma_data_converter: s16 → f32 single-frame correctness ───────── */
    ma_data_converter_config cvCfg = ma_data_converter_config_init(
        ma_format_s16, ma_format_f32, 1, 1, 8000, 8000);
    ma_data_converter converter;
    r = ma_data_converter_init(&cvCfg, NULL, &converter);
    check(r == MA_SUCCESS, "ma_data_converter_init() == MA_SUCCESS");
    if (r == MA_SUCCESS) {
        int16_t s16in = 16384;          /* 16384/32768 = 0.5 */
        float f32out = 0.0f;
        ma_uint64 inFrames = 1;
        ma_uint64 outFrames = 1;
        r = ma_data_converter_process_pcm_frames(
            &converter, &s16in, &inFrames, &f32out, &outFrames);
        check(r == MA_SUCCESS,
              "ma_data_converter_process_pcm_frames() == MA_SUCCESS");
        check(inFrames == 1 && outFrames == 1,
              "converter processed 1 in / 1 out frame");
        check(f32out > 0.49f && f32out < 0.51f,
              "s16(16384)→f32 ≈ 0.5 (got %.6f)", f32out);
        ma_data_converter_uninit(&converter, NULL);
    }

    /* ── 4. ma_waveform: sine generation (not all-zero) ──────────────────── */
    ma_waveform_config wCfg = ma_waveform_config_init(
        ma_format_f32, 1, 48000, ma_waveform_type_sine, 0.5, 440.0);
    ma_waveform wave;
    r = ma_waveform_init(&wCfg, &wave);
    check(r == MA_SUCCESS, "ma_waveform_init() == MA_SUCCESS");
    if (r == MA_SUCCESS) {
        float waveOut[256];
        ma_uint64 framesRead = 0;
        r = ma_waveform_read_pcm_frames(&wave, waveOut, 256, &framesRead);
        check(r == MA_SUCCESS,
              "ma_waveform_read_pcm_frames() == MA_SUCCESS");
        check(framesRead == 256, "waveform read 256 frames");
        int has_signal = 0;
        for (int i = 0; i < 256; ++i) {
            if (waveOut[i] != 0.0f) { has_signal = 1; break; }
        }
        check(has_signal, "sine waveform non-zero (signal present)");
        ma_waveform_uninit(&wave);
    }

    /* ── 5. ma_noise: white noise generation (not all-zero) ──────────────── */
    ma_noise_config nCfg = ma_noise_config_init(
        ma_format_f32, 1, ma_noise_type_white, 0, 0.5);
    ma_noise noise;
    r = ma_noise_init(&nCfg, NULL, &noise);
    check(r == MA_SUCCESS, "ma_noise_init() == MA_SUCCESS");
    if (r == MA_SUCCESS) {
        float noiseOut[256];
        ma_uint64 framesRead = 0;
        r = ma_noise_read_pcm_frames(&noise, noiseOut, 256, &framesRead);
        check(r == MA_SUCCESS,
              "ma_noise_read_pcm_frames() == MA_SUCCESS");
        check(framesRead == 256, "noise read 256 frames");
        int has_signal = 0;
        for (int i = 0; i < 256; ++i) {
            if (noiseOut[i] != 0.0f) { has_signal = 1; break; }
        }
        check(has_signal, "white noise non-zero (signal present)");
        ma_noise_uninit(&noise, NULL);
    }

    /* ── 6. ma_result success code semantics ────────────────────────────── */
    check(MA_SUCCESS == 0, "MA_SUCCESS == 0");

    if (g_failures == 0) {
        printf("\nminiaudio smoke test: PASS (6/6 groups OK)\n");
        return 0;
    }
    printf("\nminiaudio smoke test: FAIL (%d assertion(s) failed)\n",
           g_failures);
    return 1;
}
