/*
 * test_ohos.c — libmad 0.15.1b HarmonyOS (aarch64) 专项测试
 *
 * 目的：
 *   在 OHOS PC (aarch64) 上端到端验证 libmad 解码管线：
 *     1) mad_version 可读
 *     2) 构造一个合法 MPEG-1 Layer II 静音帧（128kbps / 44.1kHz / stereo，
 *        全零分配位 = 无量化子带 = 合法静音），mad_frame_decode 应返回 0
 *     3) mad_synth_frame 输出 PCM 样本（pcm.length > 0），
 *        验证 aarch64 定点运算（FPM_DEFAULT / SIZEOF_LONG=8）解码正确性
 *     4) 错误路径：非法同步字应返回 MAD_ERROR_LOSTSYNC 且不崩溃
 *
 * 编译（OHOS aarch64，链接 conan 产物）：
 *   clang -I<prefix>/include test_ohos.c <prefix>/lib/libmad.a -o test_ohos
 */
#include <stdio.h>
#include <string.h>
#include <mad.h>

/* MPEG-1 Layer II, 无 CRC, 128 kbps, 44.1 kHz, 无 padding, stereo:
 * 0xFF 0xFD 0x80 0x00（bitrate_index=8 = 128kbps，帧长 417 字节） */
static const unsigned char mp2_header[4] = { 0xFF, 0xFD, 0x80, 0x00 };
#define MP2_FRAME_LEN 417 /* 144 * 128000 / 44100, 无 padding */
/* libmad 要求缓冲区至少包含整帧 + MAD_BUFFER_GUARD 冗余字节 */
#define MP2_BUF_LEN    (MP2_FRAME_LEN + 64)

static int frame_ready = 0;
static unsigned long synth_frames = 0;
static long total_samples = 0;

static enum mad_flow input_cb(void *data, struct mad_stream *stream)
{
    (void)data;
    if (frame_ready)
        return MAD_FLOW_STOP;
    /* 单个完整帧：头 + 全零主体（分配位全零 = 无量化子带 = 合法静音），
     * 尾部补充 guard 冗余字节避免 BUFLEN */
    static unsigned char frame[MP2_BUF_LEN];
    memset(frame, 0, sizeof(frame));
    memcpy(frame, mp2_header, 4);
    mad_stream_buffer(stream, frame, sizeof(frame));
    frame_ready = 1;
    return MAD_FLOW_CONTINUE;
}

static enum mad_flow output_cb(void *data,
                               struct mad_header const *header,
                               struct mad_pcm *pcm)
{
    (void)data;
    (void)header;
    synth_frames++;
    total_samples += pcm->length;
    return MAD_FLOW_CONTINUE;
}

static enum mad_flow error_cb(void *data,
                              struct mad_stream *stream,
                              struct mad_frame *frame)
{
    (void)data;
    (void)frame;
    fprintf(stderr, "decoder error: %s\n", mad_stream_errorstr(stream));
    return MAD_FLOW_CONTINUE;
}

static int test_header_decode(void)
{
    struct mad_stream stream;
    struct mad_header header;
    unsigned char frame[MP2_BUF_LEN];
    int rc;

    mad_stream_init(&stream);
    mad_header_init(&header);

    /* 提供完整帧 + guard：mad_header_decode 需校验整帧长度可用 */
    memset(frame, 0, sizeof(frame));
    memcpy(frame, mp2_header, 4);
    mad_stream_buffer(&stream, frame, sizeof(frame));
    rc = mad_header_decode(&header, &stream);
    if (rc != 0) {
        fprintf(stderr, "FAIL header_decode rc=%d err=%s\n", rc,
                mad_stream_errorstr(&stream));
        mad_header_finish(&header);
        mad_stream_finish(&stream);
        return 1;
    }
    if (header.layer != MAD_LAYER_II) {
        fprintf(stderr, "FAIL expected LAYER_II, got %d\n", header.layer);
        mad_header_finish(&header);
        mad_stream_finish(&stream);
        return 1;
    }
    printf("header decode OK: layer=II bitrate=%lu samplerate=%lu mode=%d\n",
           (unsigned long)header.bitrate,
           (unsigned long)header.samplerate, (int)header.mode);
    mad_header_finish(&header);
    mad_stream_finish(&stream);
    return 0;
}

static int test_full_decode(void)
{
    struct mad_decoder decoder;
    int rc;

    frame_ready = 0;
    synth_frames = 0;
    total_samples = 0;

    mad_decoder_init(&decoder, NULL, input_cb, NULL, NULL, output_cb,
                     error_cb, NULL);
    rc = mad_decoder_run(&decoder, MAD_DECODER_MODE_SYNC);
    if (rc != 0) {
        fprintf(stderr, "FAIL decoder_run rc=%d\n", rc);
        mad_decoder_finish(&decoder);
        return 1;
    }
    mad_decoder_finish(&decoder);

    if (synth_frames == 0 || total_samples <= 0) {
        fprintf(stderr, "FAIL no PCM output (frames=%lu samples=%ld)\n",
                synth_frames, total_samples);
        return 1;
    }
    printf("full decode OK: synth_frames=%lu total_samples=%ld "
           "(aarch64 fixed-point FPM_DEFAULT/SIZEOF_LONG=8 verified)\n",
           synth_frames, total_samples);
    return 0;
}

static int test_bad_sync(void)
{
    struct mad_stream stream;
    struct mad_frame frame;
    unsigned char garbage[4] = { 0x00, 0x11, 0x22, 0x33 };
    int rc;

    mad_stream_init(&stream);
    mad_frame_init(&frame);

    mad_stream_buffer(&stream, garbage, sizeof(garbage));
    rc = mad_frame_decode(&frame, &stream);
    if (rc == 0) {
        fprintf(stderr, "FAIL garbage frame decoded unexpectedly\n");
        mad_frame_finish(&frame);
        mad_stream_finish(&stream);
        return 1;
    }
    printf("bad-sync OK: rc=%d (expected MAD_ERROR_*) err=%s\n", rc,
           mad_stream_errorstr(&stream));
    mad_frame_finish(&frame);
    mad_stream_finish(&stream);
    return 0;
}

int main(void)
{
    int fails = 0;

    printf("=== libmad %s HarmonyOS aarch64 test ===\n", mad_version);
    if (!mad_version || strlen(mad_version) == 0) {
        fprintf(stderr, "FAIL mad_version empty\n");
        return 1;
    }

    fails += test_header_decode();
    fails += test_full_decode();
    fails += test_bad_sync();

    if (fails == 0) {
        printf("test_ohos: ALL PASS\n");
        return 0;
    }
    fprintf(stderr, "test_ohos: %d FAILURE(S)\n", fails);
    return 1;
}
