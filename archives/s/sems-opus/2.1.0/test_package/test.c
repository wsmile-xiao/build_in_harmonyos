/*
 * sems-opus 鸿蒙特有消费者测试（完整消费者用例：加载 + 实例化 + 真实编解码）
 *
 * 消费路径与 SEMS 主程序的编解码插件加载模型一致：
 *   1. dlopen 加载 opus 编解码插件动态模块（鸿蒙 dlopen 行为验证）
 *   2. dlsym 取上游 amci_exports 导出结构，直接使用 core/amci/amci.h 的真实
 *      ABI（测试内不再推测结构体布局）
 *   3. 校验模块名、amci_exports->payloads 中的 opus payload，以及 codecs 中
 *      payload->codec_id 对应的编解码器条目
 *   4. 按消费者方式实例化 codec：init() 取句柄 → encode() PCM16→opus →
 *      decode() opus→PCM16；帧长取自 init() 返回的 fmt 描述
 *      （AMCI_FMT_FRAME_SIZE），缺省按 payload 采样率 × 20ms 推算
 *   5. 每一步都断言真实结果（句柄、字节数、能量），任一步不满足即以非 0
 *      退出码失败——不存在"只验符号存在即返回成功"的降级分支
 *
 * 表遍历约定（上游 core/amci/amci.h）：
 *   - payload 表以 name == NULL 结束（opus 条目 payload_id 为 -1，动态 payload）
 *   - codec 表以上游 END_CODECS 哨兵 id == -1 结束
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sems/amci/amci.h>
#include <sems/amci/codecs.h>

#define EXPECTED_MODULE_NAME "opus"
/* 上游 opus_fmt_description: {AMCI_FMT_FRAME_LENGTH, 20}, {AMCI_FMT_FRAME_SIZE, 20*rate/1000} */
#define FRAME_MS 20

/* init() 返回的 fmt 描述中取帧长（采样数）；描述数组以 {0,0} 结束 */
static int frame_samples_from_fmt(amci_codec_fmt_info_t* fmt, int fallback)
{
    if (fmt) {
        for (int i = 0; fmt[i].id != 0 || fmt[i].value != 0; i++) {
            if (fmt[i].id == AMCI_FMT_FRAME_SIZE && fmt[i].value > 0)
                return fmt[i].value;
        }
    }
    return fallback;
}

/* payload 表以 name == NULL 结束 */
static const struct amci_payload_t* find_payload(const struct amci_payload_t* payloads, const char* name)
{
    if (!payloads)
        return NULL;
    for (const struct amci_payload_t* p = payloads; p->name != NULL; p++) {
        if (strcmp(p->name, name) == 0)
            return p;
    }
    return NULL;
}

/* codec 表以上游 END_CODECS 哨兵（id == -1）结束 */
static struct amci_codec_t* find_codec(struct amci_codec_t* codecs, int id)
{
    if (!codecs)
        return NULL;
    for (struct amci_codec_t* c = codecs; c->id != -1; c++) {
        if (c->id == id)
            return c;
    }
    return NULL;
}

/* 解码后 PCM 的绝对值能量，用于确认链路真的搬了音频（非静音） */
static long pcm_energy(const unsigned char* pcm, int bytes)
{
    long energy = 0;
    for (int i = 0; i + 1 < bytes; i += 2) {
        short s = (short)(pcm[i] | (pcm[i + 1] << 8));
        energy += (s < 0) ? -(long)s : (long)s;
    }
    return energy;
}

int main(void)
{
    void* h = NULL;
    struct amci_exports_t* exports = NULL;
    struct amci_codec_t* codec = NULL;
    const struct amci_payload_t* payload = NULL;
    unsigned char* pcm_in = NULL;
    unsigned char* opus_out = NULL;
    unsigned char* pcm_out = NULL;
    long h_codec = 0;
    int samples = 0, enc = 0, dec = 0;
    const char* err = NULL;
    char errbuf[256];

    const char* plugin_path = getenv("SEMS_OPUS_PLUGIN");
    if (!plugin_path || !*plugin_path) {
        fprintf(stderr, "FAIL: SEMS_OPUS_PLUGIN not set\n");
        return 2;
    }

    /* 1. 鸿蒙 dlopen 加载插件 */
    h = dlopen(plugin_path, RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "FAIL: dlopen(%s): %s\n", plugin_path, dlerror());
        return 1;
    }
    printf("PASS: dlopen %s\n", plugin_path);

    /* 2. amci_exports 导出结构（上游 BEGIN_EXPORTS 契约） */
    dlerror();
    exports = (struct amci_exports_t*)dlsym(h, "amci_exports");
    const char* sym_err = dlerror();
    if (sym_err || !exports) {
        snprintf(errbuf, sizeof errbuf, "dlsym(amci_exports): %s",
                 sym_err ? sym_err : "NULL symbol");
        err = errbuf;
        goto cleanup;
    }
    if (!exports->name || strcmp(exports->name, EXPECTED_MODULE_NAME) != 0) {
        snprintf(errbuf, sizeof errbuf, "module name '%s', expected '%s'",
                 exports->name ? exports->name : "(null)", EXPECTED_MODULE_NAME);
        err = errbuf;
        goto cleanup;
    }
    printf("PASS: amci_exports->name = '%s'\n", exports->name);

    /* 3. payload 与 codec 表校验 */
    payload = find_payload(exports->payloads, EXPECTED_MODULE_NAME);
    if (!payload) {
        snprintf(errbuf, sizeof errbuf,
                 "no '%s' entry in amci_exports->payloads", EXPECTED_MODULE_NAME);
        err = errbuf;
        goto cleanup;
    }
    printf("PASS: payload '%s' rate=%d advertised=%d channels=%d codec_id=%d\n",
           payload->name, payload->sample_rate, payload->advertised_sample_rate,
           payload->channels, payload->codec_id);

    if (payload->codec_id != CODEC_OPUS) {
        snprintf(errbuf, sizeof errbuf, "payload codec_id %d != CODEC_OPUS %d",
                 payload->codec_id, CODEC_OPUS);
        err = errbuf;
        goto cleanup;
    }

    codec = find_codec(exports->codecs, payload->codec_id);
    if (!codec) {
        snprintf(errbuf, sizeof errbuf, "codec id %d missing from amci_exports->codecs",
                 payload->codec_id);
        err = errbuf;
        goto cleanup;
    }
    if (!codec->init || !codec->encode || !codec->decode) {
        snprintf(errbuf, sizeof errbuf,
                 "codec %d incomplete: init=%s encode=%s decode=%s (all required)",
                 codec->id, codec->init ? "yes" : "NULL", codec->encode ? "yes" : "NULL",
                 codec->decode ? "yes" : "NULL");
        err = errbuf;
        goto cleanup;
    }
    printf("PASS: codec id=%d (CODEC_OPUS=%d) exports init/encode/decode\n",
           codec->id, CODEC_OPUS);

    /* 4. 消费者实例化：init() 返回句柄，失败为 -1（core/amci/amci.h） */
    const char* params_out = NULL;
    amci_codec_fmt_info_t* fmt_info = NULL;
    h_codec = codec->init(NULL, &params_out, &fmt_info);
    if (h_codec <= 0) {
        snprintf(errbuf, sizeof errbuf, "codec->init() returned %ld", h_codec);
        err = errbuf;
        goto cleanup;
    }
    printf("PASS: codec->init() handle=%ld\n", h_codec);

    samples = frame_samples_from_fmt(fmt_info, payload->sample_rate * FRAME_MS / 1000);
    if (samples <= 0) {
        snprintf(errbuf, sizeof errbuf,
                 "no usable frame length (fmt=%s, payload rate=%d, %dms)",
                 fmt_info ? "present" : "absent", payload->sample_rate, FRAME_MS);
        err = errbuf;
        goto cleanup;
    }

    const unsigned int pcm_in_bytes = (unsigned int)samples * 2; /* 单声道 16bit */
    pcm_in = (unsigned char*)malloc(pcm_in_bytes);
    opus_out = (unsigned char*)malloc(AUDIO_BUFFER_SIZE + 1024);
    pcm_out = (unsigned char*)malloc((size_t)pcm_in_bytes * 2);
    if (!pcm_in || !opus_out || !pcm_out) {
        err = "malloc failed";
        goto cleanup;
    }

    /* 20ms 单声道 16bit 方波（±12000），无需 libm */
    for (int i = 0; i < samples; i++) {
        short s = ((i % 40) < 20) ? 12000 : -12000;
        pcm_in[2 * i] = (unsigned char)(s & 0xff);
        pcm_in[2 * i + 1] = (unsigned char)((s >> 8) & 0xff);
    }

    /* 5. 真实编码：PCM16 -> opus（上游 pcm16_2_opus） */
    enc = codec->encode(opus_out, pcm_in, pcm_in_bytes, 1,
                        (unsigned int)payload->sample_rate, h_codec);
    if (enc <= 0) {
        snprintf(errbuf, sizeof errbuf, "encode() returned %d (PCM %u bytes, %d samples)",
                 enc, pcm_in_bytes, samples);
        err = errbuf;
        goto cleanup;
    }
    printf("PASS: encode %u PCM bytes (%d samples @%d Hz) -> %d opus bytes\n",
           pcm_in_bytes, samples, payload->sample_rate, enc);

    /* 6. 真实解码：opus -> PCM16（上游 opus_2_pcm16），长度须回到同一帧长 */
    dec = codec->decode(pcm_out, opus_out, (unsigned int)enc, 1,
                        (unsigned int)payload->sample_rate, h_codec);
    if (dec != (int)pcm_in_bytes) {
        snprintf(errbuf, sizeof errbuf, "decode() returned %d PCM bytes, expected %u",
                 dec, pcm_in_bytes);
        err = errbuf;
        goto cleanup;
    }
    long energy = pcm_energy(pcm_out, dec);
    if (energy <= 0) {
        snprintf(errbuf, sizeof errbuf, "decoded PCM is silent (energy=%ld)", energy);
        err = errbuf;
        goto cleanup;
    }
    printf("PASS: decode %d opus bytes -> %d PCM bytes, energy=%ld\n", enc, dec, energy);

cleanup:
    if (err)
        fprintf(stderr, "FAIL: %s\n", err);
    if (codec && h_codec > 0 && codec->destroy)
        codec->destroy(h_codec);
    free(pcm_in);
    free(opus_out);
    free(pcm_out);
    if (h)
        dlclose(h);
    if (err)
        return 1;

    printf("RESULT: sems-opus 2.1.0 plugin consumer test OK "
           "(amci_exports: init+encode+decode, %d samples/%d ms)\n",
           samples, FRAME_MS);
    return 0;
}
