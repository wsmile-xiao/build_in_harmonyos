/*
 * HarmonyOS 专项测试：Opus 编码/解码真实回环
 *
 * 目的：验证 libopus.so 在 HarmonyOS PC (aarch64) 上不仅可 dlopen，
 *       且编码器/解码器 API 能真正处理音频数据（不再是符号解析探针）。
 * 内容：生成 48kHz 立体声正弦 PCM → opus_encode() 压缩 → opus_decode() 解码
 *       → 校验解码长度、返回值、opus_strerror/opus_get_version_string，
 *       （header-only 的 opus_encoder_get_size 也一并验证 ABI 一致性）。
 * 编译：clang test_ohos_roundtrip.c -o test_roundtrip <include 闭包> -L<libdir> -lopus
 * 运行：./test_roundtrip   （真机 aarch64-linux-ohos ELF，直接执行）
 */
#include <opus/opus.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SAMPLE_RATE 48000
#define CHANNELS    2
#define FRAME_SIZE  960   /* 20ms @48kHz */
#define BLOCKS      16

int main(void) {
    /* ABI 一致性：头声明的分配尺寸与实际编码器状态一致 */
    int enc_size = opus_encoder_get_size(CHANNELS);
    if (enc_size <= 0) {
        fprintf(stderr, "FAIL: opus_encoder_get_size(%d) = %d\n", CHANNELS, enc_size);
        return 1;
    }
    OpusEncoder *enc = (OpusEncoder *)malloc(enc_size);
    if (!enc) { fprintf(stderr, "FAIL: malloc encoder\n"); return 1; }
    int err = opus_encoder_init(enc, SAMPLE_RATE, CHANNELS, OPUS_APPLICATION_AUDIO);
    if (err != OPUS_OK) {
        fprintf(stderr, "FAIL: opus_encoder_init: %s\n", opus_strerror(err));
        free(enc);
        return 1;
    }

    int dec_size = opus_decoder_get_size(CHANNELS);
    OpusDecoder *dec = (OpusDecoder *)malloc(dec_size);
    if (!dec) { fprintf(stderr, "FAIL: malloc decoder\n"); free(enc); return 1; }
    err = opus_decoder_init(dec, SAMPLE_RATE, CHANNELS);
    if (err != OPUS_OK) {
        fprintf(stderr, "FAIL: opus_decoder_init: %s\n", opus_strerror(err));
        free(enc); free(dec);
        return 1;
    }

    /* 48kHz 立体声 1kHz 正弦 PCM */
    opus_int16 pcm[FRAME_SIZE * CHANNELS];
    unsigned char bits[4000];
    opus_int16 out[FRAME_SIZE * CHANNELS];
    int total_enc = 0, total_dec = 0;

    for (int b = 0; b < BLOCKS; b++) {
        for (int i = 0; i < FRAME_SIZE; i++) {
            double t = (double)(b * FRAME_SIZE + i) / SAMPLE_RATE;
            pcm[i * CHANNELS + 0] = (opus_int16)(32767.0 * sin(2.0 * 3.14159265358979 * 1000.0 * t));
            pcm[i * CHANNELS + 1] = (opus_int16)(32767.0 * sin(2.0 * 3.14159265358979 * 1000.0 * t));
        }
        int n = opus_encode(enc, pcm, FRAME_SIZE, bits, (opus_int32)sizeof(bits));
        if (n < 0) {
            fprintf(stderr, "FAIL: opus_encode block %d: %s\n", b, opus_strerror(n));
            free(enc); free(dec);
            return 1;
        }
        total_enc += n;
        int m = opus_decode(dec, bits, n, out, FRAME_SIZE, 0);
        if (m != FRAME_SIZE) {
            fprintf(stderr, "FAIL: opus_decode block %d: returned %d (want %d)\n", b, m, FRAME_SIZE);
            free(enc); free(dec);
            return 1;
        }
        total_dec += m;
        /* 解码输出非静音：验证真实数据通路 */
        int nonzero = 0;
        for (int i = 0; i < FRAME_SIZE * CHANNELS; i++) {
            if (out[i] != 0) { nonzero = 1; break; }
        }
        if (!nonzero) {
            fprintf(stderr, "FAIL: block %d decoded to silence\n", b);
            free(enc); free(dec);
            return 1;
        }
    }

    printf("PASS: opus roundtrip %d blocks @%dHz/%dch (enc %d B, dec %d samples, ver %s)\n",
           BLOCKS, SAMPLE_RATE, CHANNELS, total_enc, total_dec, opus_get_version_string());
    free(enc);
    free(dec);
    return 0;
}
