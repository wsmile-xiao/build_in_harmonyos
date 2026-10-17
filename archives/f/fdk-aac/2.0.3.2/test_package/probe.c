/* fdk_aac_probe — fdk-aac 2.0.3.2 鸿蒙 PC 适配消费者端到端探针
 *
 * 验证被适配的 libfdk-aac 的完整可用性:
 *   1. 编码器:确定性合成 PCM(441Hz 正弦表 + LCG 噪声,2s@44.1kHz mono)
 *      → AAC-LC/ADTS 编码,逐帧喂入,末段 flush,断言输出非空且全量消费输入;
 *   2. 解码器:ADTS 流逐块 Fill + DecodeFrame 往返解码(镜像上游
 *      test-encode-decode.c 的 decode() 语义),流末 EOS flush;
 *   3. 结构断言:ADTS 帧数、样本数、能量、往返误差(按编码器 nDelay
 *      对齐后比较)、非法参数拒绝;
 *   4. 聚合 SHA-1 哈希输出(与上游官方套件同口径)。
 *
 * 合成信号为纯整数运算(编译期嵌入正弦表 + 整数 LCG),与 libm 无关,
 * 同架构跨工具链位元可复现。注意:FDK 在 aarch64 上使用 16-bit 系数表
 * + 32x16 定点乘法(FDK_archdef.h 的 ARCH_PREFER_MULT_32x16 等),码流
 * 跨架构设计上非位元一致,探针哈希按平台比对(见 notes.md)。
 *
 * 仅依赖 C 标准库 + fdk-aac 头文件,sha1 实现 vendored 自官方发行包。
 */
#include <fdk-aac/aacenc_lib.h>
#include <fdk-aac/aacdecoder_lib.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "sha1.h"

static int checks = 0;
static int fails = 0;
#define CHECK(cond, name)                                                     \
    do {                                                                      \
        checks++;                                                             \
        if (cond) {                                                           \
            printf("[OK] %s\n", name);                                        \
        } else {                                                              \
            fails++;                                                          \
            printf("[FAIL] %s\n", name);                                      \
        }                                                                     \
    } while (0)

#define RATE 44100
#define SECS 2
#define N (RATE * SECS) /* 88200 个样本 */

/* 441Hz 正弦表:44100/441 = 100 样本/周期,幅值 16000,编译期常量,
 * 保证合成信号与 libm 实现无关(跨平台/跨工具链位元一致)。 */
static const int16_t SINE_TAB[100] = {
    0, 1005, 2005, 2998, 3979, 4944, 5890, 6812, 7708, 8573,
    9405, 10199, 10953, 11663, 12328, 12944, 13509, 14021, 14477, 14876,
    15217, 15497, 15717, 15874, 15968, 16000, 15968, 15874, 15717, 15497,
    15217, 14876, 14477, 14021, 13509, 12944, 12328, 11663, 10953, 10199,
    9405, 8573, 7708, 6812, 5890, 4944, 3979, 2998, 2005, 1005,
    0, -1005, -2005, -2998, -3979, -4944, -5890, -6812, -7708, -8573,
    -9405, -10199, -10953, -11663, -12328, -12944, -13509, -14021, -14477, -14876,
    -15217, -15497, -15717, -15874, -15968, -16000, -15968, -15874, -15717, -15497,
    -15217, -14876, -14477, -14021, -13509, -12944, -12328, -11663, -10953, -10199,
    -9405, -8573, -7708, -6812, -5890, -4944, -3979, -2998, -2005, -1005,
};

/* ADTS 同步字数帧:0xFFF 同步 + layer==00 */
static int count_adts_frames(const uint8_t *buf, size_t len) {
    int n = 0;
    size_t i;
    for (i = 0; i + 1 < len; i++) {
        if (buf[i] == 0xFF && (buf[i + 1] & 0xF6) == 0xF0)
            n++;
    }
    return n;
}

int main(void) {
    /* ---- 确定性合成 PCM:441Hz 正弦表 + LCG 噪声(纯整数) ---- */
    static int16_t pcm[N];
    uint32_t lcg = 0x12345678u;
    int i;
    for (i = 0; i < N; i++) {
        lcg = lcg * 1103515245u + 12345u;
        int noise = (int)((lcg >> 16) % 61u) - 30;
        int v = (int)SINE_TAB[i % 100] + noise;
        if (v > 32767) v = 32767;
        if (v < -32768) v = -32768;
        pcm[i] = (int16_t)v;
    }

    /* ---- 编码器 ---- */
    HANDLE_AACENCODER enc = NULL;
    AACENC_ERROR e = aacEncOpen(&enc, 0, 1);
    CHECK(e == AACENC_OK && enc != NULL, "aacEncOpen (mono)");
    if (enc == NULL) {
        printf("PROBE ABORTED\n");
        return 1;
    }

    {
        int setrc = 0;
        setrc |= (int)aacEncoder_SetParam(enc, AACENC_AOT, 2);          /* AAC-LC */
        setrc |= (int)aacEncoder_SetParam(enc, AACENC_SAMPLERATE, RATE);
        setrc |= (int)aacEncoder_SetParam(enc, AACENC_CHANNELMODE, MODE_1);
        setrc |= (int)aacEncoder_SetParam(enc, AACENC_BITRATE, 64000);
        setrc |= (int)aacEncoder_SetParam(enc, AACENC_TRANSMUX, 2);     /* ADTS */
        setrc |= (int)aacEncoder_SetParam(enc, AACENC_AFTERBURNER, 1);
        CHECK(setrc == 0, "aacEncoder_SetParam x6");
    }

    e = aacEncEncode(enc, NULL, NULL, NULL, NULL); /* 初始化 */
    CHECK(e == AACENC_OK, "encoder init");

    AACENC_InfoStruct info;
    memset(&info, 0, sizeof(info));
    e = aacEncInfo(enc, &info);
    CHECK(e == AACENC_OK && info.frameLength == 1024 && info.inputChannels == 1,
          "aacEncInfo frameLength=1024 mono");
    printf("encoder nDelay=%u frameLength=%u\n", info.nDelay, info.frameLength);

    /* 负向:非法采样率必须被拒绝 */
    CHECK(aacEncoder_SetParam(enc, AACENC_SAMPLERATE, 12345) != AACENC_OK,
          "invalid samplerate rejected");

    /* ---- 编码循环(镜像上游 test-encode-decode.c 语义) ---- */
    static uint8_t stream[262144];
    size_t stream_len = 0;
    int pos = 0;
    int enc_errors = 0;
    while (1) {
        int in_identifier = IN_AUDIO_DATA, out_identifier = OUT_BITSTREAM_DATA;
        int in_size = 0, in_elem_size = 2, out_size, out_elem_size = 1;
        void *in_ptr = NULL, *out_ptr;
        AACENC_BufDesc in_buf = {0}, out_buf = {0};
        AACENC_InArgs in_args = {0};
        AACENC_OutArgs out_args = {0};
        uint8_t outbuf[20480];

        if (pos < N) {
            /* read/pos 均为样本数:每次喂最多一个 frameLength(1024) 样本 */
            int read = N - pos;
            if (read > (int)info.frameLength)
                read = (int)info.frameLength;
            read = (read / 2) * 2; /* 保持偶数样本 */
            in_ptr = (void *)(pcm + pos);
            in_size = read * 2; /* 字节数 */
            in_buf.numBufs = 1;
            in_buf.bufs = &in_ptr;
            in_buf.bufferIdentifiers = &in_identifier;
            in_buf.bufSizes = &in_size;
            in_buf.bufElSizes = &in_elem_size;
            in_args.numInSamples = read;
            pos += read;
        } else {
            /* flush:numInSamples=-1,仅输出 */
            in_args.numInSamples = -1;
        }
        out_ptr = outbuf;
        out_size = (int)sizeof(outbuf);
        out_buf.numBufs = 1;
        out_buf.bufs = &out_ptr;
        out_buf.bufferIdentifiers = &out_identifier;
        out_buf.bufSizes = &out_size;
        out_buf.bufElSizes = &out_elem_size;

        e = aacEncEncode(enc, &in_buf, &out_buf, &in_args, &out_args);
        /* EOF 可能携带最后一段码流,必须先落盘再退出 */
        if (out_args.numOutBytes > 0) {
            if (stream_len + (size_t)out_args.numOutBytes > sizeof(stream)) {
                CHECK(0, "stream buffer capacity");
                break;
            }
            memcpy(stream + stream_len, outbuf, (size_t)out_args.numOutBytes);
            stream_len += (size_t)out_args.numOutBytes;
        }
        if (e == AACENC_ENCODE_EOF)
            break;
        if (e != AACENC_OK) {
            enc_errors++;
            break;
        }
        if (pos >= N && out_args.numOutBytes == 0)
            break; /* flush 结束 */
    }
    CHECK(enc_errors == 0, "all encode calls OK");
    CHECK(stream_len > 0, "encoded stream non-empty");
    CHECK(count_adts_frames(stream, stream_len) >= 86,
          "ADTS frame count >= 86");
    CHECK(pos == N, "all input samples consumed");
    printf("stream bytes=%u adts_frames=%d\n",
           (unsigned)stream_len, count_adts_frames(stream, stream_len));
    aacEncClose(&enc);

    /* ---- 解码器 ---- */
    HANDLE_AACDECODER dec = aacDecoder_Open(TT_MP4_ADTS, 1);
    CHECK(dec != NULL, "aacDecoder_Open (ADTS)");
    if (dec == NULL) {
        printf("PROBE ABORTED\n");
        return 1;
    }
    /* 与上游 test-encode-decode 相同的解码器参数 */
    aacDecoder_SetParam(dec, AAC_CONCEAL_METHOD, 1);
    aacDecoder_SetParam(dec, AAC_PCM_LIMITER_ENABLE, 0);

    static int16_t out_all[N + 4096];
    int out_total = 0;
    int dec_frames = 0;
    int dec_errors = 0;
    int overflow = 0;
    size_t off = 0;
    while (off < stream_len) {
        int chunk = (int)(stream_len - off);
        if (chunk > 1024)
            chunk = 1024;
        {
            const uint8_t *ptr = stream + off;
            UINT valid = (UINT)chunk, bsz = (UINT)chunk;
            AAC_DECODER_ERROR derr = aacDecoder_Fill(dec, (UCHAR **)&ptr, &bsz, &valid);
            off += (size_t)(bsz - valid);
            if (derr == AAC_DEC_NOT_ENOUGH_BITS)
                continue;
            if (derr != AAC_DEC_OK) {
                dec_errors++;
                break;
            }
        }
        while (1) {
            INT_PCM *op = (INT_PCM *)(out_all + out_total);
            int cap = N + 4096 - out_total;
            AAC_DECODER_ERROR derr = aacDecoder_DecodeFrame(dec, op, cap, 0);
            if (derr == AAC_DEC_NOT_ENOUGH_BITS)
                break;
            if (derr != AAC_DEC_OK) {
                dec_errors++;
                break;
            }
            CStreamInfo *si = aacDecoder_GetStreamInfo(dec);
            int got = (int)si->frameSize * (int)si->numChannels;
            if (out_total + got > N + 4096) {
                overflow = 1;
                break;
            }
            out_total += got;
            dec_frames++;
        }
        if (dec_errors || overflow)
            break;
    }
    /* EOS flush:零字节 Fill 排出缓冲区内残余帧 */
    if (!dec_errors && !overflow) {
        UINT bsz = 0, valid = 0;
        const uint8_t *dummy = NULL;
        AAC_DECODER_ERROR derr = aacDecoder_Fill(dec, (UCHAR **)&dummy, &bsz, &valid);
        if (derr != AAC_DEC_OK)
            dec_errors++;
        while (1) {
            INT_PCM *op = (INT_PCM *)(out_all + out_total);
            int cap = N + 4096 - out_total;
            derr = aacDecoder_DecodeFrame(dec, op, cap, 0);
            if (derr == AAC_DEC_NOT_ENOUGH_BITS)
                break;
            if (derr != AAC_DEC_OK) {
                dec_errors++;
                break;
            }
            CStreamInfo *si = aacDecoder_GetStreamInfo(dec);
            int got = (int)si->frameSize * (int)si->numChannels;
            if (out_total + got > N + 4096) {
                overflow = 1;
                break;
            }
            out_total += got;
            dec_frames++;
        }
    }
    CHECK(dec_errors == 0, "all decoder calls OK");
    CHECK(!overflow, "decode buffer capacity");
    CHECK(dec_frames >= 86, "decoded frame count >= 86");
    CHECK(out_total >= N - 2048 && out_total <= N + 4096,
          "decoded sample count ~= input");
    printf("decoded frames=%d samples=%d\n", dec_frames, out_total);

    /* ---- 往返差异(按编码器 nDelay 对齐,镜像上游 decoder_output_skip) ---- */
    {
        int skip = (int)info.nDelay; /* mono,channels=1 */
        int avail = out_total - skip;
        int cmp = avail < N ? avail : N;
        long long dsum = 0, energy = 0;
        int dmax = 0;
        for (i = 0; i < cmp; i++) {
            int d = (int)out_all[skip + i] - (int)pcm[i];
            if (d < 0) d = -d;
            if (d > dmax) dmax = d;
            dsum += d;
            energy += (long long)out_all[skip + i] * out_all[skip + i];
        }
        printf("compare samples=%d skip=%d dmax=%d dmean=%lld\n",
               cmp, skip, dmax, dsum / cmp);
        CHECK(energy > 0, "decoded output non-silent");
        CHECK(dmax < 6000, "max roundtrip diff < 6000");
        CHECK(dsum / cmp < 1000, "mean roundtrip diff < 1000");
    }

    /* ---- 聚合 SHA-1(与上游 test-encode-decode 同口径,含全部解码样本) ---- */
    {
        SHA1Context eh, dh;
        unsigned char ed[SHA_DIGEST_LENGTH], dd[SHA_DIGEST_LENGTH];
        SHA1Reset(&eh);
        SHA1Reset(&dh);
        SHA1Input(&eh, stream, (unsigned)stream_len);
        SHA1Input(&dh, (const unsigned char *)out_all,
                  (unsigned)(out_total * (int)sizeof(int16_t)));
        SHA1Result(&eh, ed);
        SHA1Result(&dh, dd);
        printf("encode hash: ");
        for (i = 0; i < SHA_DIGEST_LENGTH; i++)
            printf("%02x", ed[i]);
        printf("\n");
        printf("decode hash: ");
        for (i = 0; i < SHA_DIGEST_LENGTH; i++)
            printf("%02x", dd[i]);
        printf("\n");
    }
    CHECK(1, "sha1 aggregates computed");

    aacDecoder_Close(dec);
    printf("\n%d checks, %d failed\n", checks, fails);
    return fails ? 1 : 0;
}
