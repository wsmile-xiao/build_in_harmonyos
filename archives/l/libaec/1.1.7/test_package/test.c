/* libaec 真实功能断言：Adaptive Entropy Coding 编 → 解 往返。
 *
 * 不用 dlopen 探针（那只证明库能加载），直接链接并跑一次可验证的压缩往返：
 *   ① 造一段高度可压缩的数据（阶梯信号），编码后断言**确实变小**——
 *      排除「实现退化成原样拷贝」这种能通过 dlsym 却毫无功能的情况；
 *   ② 解码回来逐字节比对，断言与原始数据完全一致——这是无损编码的定义；
 *   ③ 同时验 libsz（szip 兼容层），因为 HDF5 用的是它而不是 libaec 本身：
 *      HDF5 的 DT_NEEDED 实测是 libsz.so.2。只验 libaec 会漏掉真正被消费的那一半。
 */
#include <libaec.h>
#include <szlib.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define N 4096

static void fill_ramp(unsigned char *dst, int n)
{
    /* 阶梯信号：16 位样本，值缓慢递增（每 8 个样本 +1）—— 熵编码应能大幅压缩。
     *
     * ⚠️ 字节序必须与下面的 AEC_DATA_MSB / SZ_MSB_OPTION_MASK 一致，写成**大端**。
     * 曾按小端填充却声明 MSB，libaec 把样本读成 (低<<8)|高 —— 一个剧烈震荡的值，
     * 于是 8192 字节只压到 4219（51.5%）。当时的表象是「压缩率不达标」，
     * 很容易被误判成库有问题或阈值定太严而去放宽阈值 ——
     * 那样就得到一个在垃圾数据上跑的「通过」测试。真因是测试自己喂错了数据。
     */
    for (int i = 0; i < n; i++) {
        unsigned short v = (unsigned short)(i / 8);
        dst[i * 2]     = (unsigned char)(v >> 8);    /* 高字节在前 = 大端 = MSB */
        dst[i * 2 + 1] = (unsigned char)(v & 0xff);
    }
}

static int test_aec_roundtrip(void)
{
    static unsigned char src[N * 2], enc[N * 4], dec[N * 2];
    fill_ramp(src, N);

    struct aec_stream s;
    memset(&s, 0, sizeof(s));
    s.bits_per_sample = 16;
    s.block_size      = 16;
    s.rsi             = 128;
    s.flags           = AEC_DATA_PREPROCESS | AEC_DATA_MSB;
    s.next_in  = src;  s.avail_in  = sizeof(src);
    s.next_out = enc;  s.avail_out = sizeof(enc);

    if (aec_encode_init(&s) != AEC_OK)       { printf("FAIL aec_encode_init\n"); return 1; }
    if (aec_encode(&s, AEC_FLUSH) != AEC_OK) { printf("FAIL aec_encode\n"); return 1; }
    size_t enc_len = (size_t)s.total_out;
    aec_encode_end(&s);

    if (enc_len == 0) { printf("FAIL 编码输出为空\n"); return 1; }
    /* 阶梯信号冗余极高，压不到一半说明编码器没真正工作 */
    if (enc_len >= sizeof(src) / 2) {
        printf("FAIL 压缩率异常: %zu -> %zu 字节（未达 1/2）\n", sizeof(src), enc_len);
        return 1;
    }

    memset(&s, 0, sizeof(s));
    s.bits_per_sample = 16;
    s.block_size      = 16;
    s.rsi             = 128;
    s.flags           = AEC_DATA_PREPROCESS | AEC_DATA_MSB;
    s.next_in  = enc;  s.avail_in  = enc_len;
    s.next_out = dec;  s.avail_out = sizeof(dec);

    if (aec_decode_init(&s) != AEC_OK)       { printf("FAIL aec_decode_init\n"); return 1; }
    if (aec_decode(&s, AEC_FLUSH) != AEC_OK) { printf("FAIL aec_decode\n"); return 1; }
    size_t dec_len = (size_t)s.total_out;
    aec_decode_end(&s);

    if (dec_len != sizeof(src)) {
        printf("FAIL 解码长度 %zu != 原始 %zu\n", dec_len, sizeof(src));
        return 1;
    }
    if (memcmp(src, dec, sizeof(src)) != 0) { printf("FAIL 往返数据不一致\n"); return 1; }

    printf("aec 往返 OK: %zu -> %zu 字节（压至 %.1f%%），解码逐字节一致\n",
           sizeof(src), enc_len, 100.0 * (double)enc_len / (double)sizeof(src));
    return 0;
}

static int test_szip_compat(void)
{
    /* HDF5 消费的是 libsz 这一层（其 DT_NEEDED 实测为 libsz.so.2），必须一并验。
     * 只验 libaec 会漏掉真正被下游消费的那一半。 */
    static unsigned char src[N * 2], enc[N * 4], dec[N * 2];
    fill_ramp(src, N);

    SZ_com_t p;
    p.options_mask        = SZ_ALLOW_K13_OPTION_MASK | SZ_MSB_OPTION_MASK | SZ_NN_OPTION_MASK;
    p.bits_per_pixel      = 16;
    p.pixels_per_block    = 16;
    p.pixels_per_scanline = 128;

    size_t enc_len = sizeof(enc);
    if (SZ_BufftoBuffCompress(enc, &enc_len, src, sizeof(src), &p) != SZ_OK) {
        printf("FAIL SZ_BufftoBuffCompress\n"); return 1;
    }
    if (enc_len == 0 || enc_len >= sizeof(src)) {
        printf("FAIL szip 未压缩: %zu -> %zu\n", sizeof(src), enc_len); return 1;
    }

    size_t dec_len = sizeof(dec);
    if (SZ_BufftoBuffDecompress(dec, &dec_len, enc, enc_len, &p) != SZ_OK) {
        printf("FAIL SZ_BufftoBuffDecompress\n"); return 1;
    }
    if (dec_len != sizeof(src) || memcmp(src, dec, sizeof(src)) != 0) {
        printf("FAIL szip 往返数据不一致\n"); return 1;
    }

    printf("szip 往返 OK: %zu -> %zu 字节，解码逐字节一致\n", sizeof(src), enc_len);
    return 0;
}

int main(void)
{
    if (test_aec_roundtrip()) return 1;
    if (test_szip_compat())   return 1;
    printf("libaec 1.1.7: 全部断言通过\n");
    return 0;
}
