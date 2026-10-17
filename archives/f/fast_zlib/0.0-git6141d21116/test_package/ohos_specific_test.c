/* ohos_specific_test.c — fast_zlib HarmonyOS 专项测试（R02 新增，硬门禁）
 *
 * 验证的鸿蒙特性/平台适配路径：
 * 1. 快速匹配实现真实接入：fast_zlib 的优化核心是 deflate 内部 longest_match
 *    （Sources/match.h，C 版跨架构）。match.h 定义了全局符号
 *    `fast_lm_copyright`（"Fast match finder for zlib, ..."），只有该实现被
 *    编译进最终产物并链接时该符号才存在。本测试显式引用该符号并核对内容，
 *    证明 OHOS 平台上快速匹配路径真实生效（而非回退到原始 zlib 实现）。
 * 2. zlib 兼容公开 API 在 OHOS aarch64 上可用且正确：compress2/uncompress
 *    往返 + 流式 deflate/inflate（含 flush 边界），校验数据一致性。
 * 3. UNALIGNED_OK 快速路径（match.h 依赖未对齐读，aarch64 硬件支持）：
 *    大块混合数据（可压缩 + 随机）压缩解压往返一致，验证未对齐访问在
 *    HarmonyOS PC 目标上行为正确。
 *
 * 编译（OHOS aarch64，静态链接 libz.a）：
 *   clang -O2 -fPIC -I <pkg>/include -o ohos_specific_test \
 *         ohos_specific_test.c <pkg>/lib/libz.a
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

/* match.h 导出的全局符号：快速匹配实现存在性证明 */
extern const char fast_lm_copyright[];

static int roundtrip_stream(const unsigned char *input, size_t src_len,
                            unsigned char *compressed, size_t cap,
                            unsigned long *dest_len) {
    z_stream zs;
    memset(&zs, 0, sizeof(zs));
    if (deflateInit(&zs, 9) != Z_OK) {
        fprintf(stderr, "FAIL: deflateInit\n");
        return 1;
    }
    zs.next_in = (Bytef *)input;
    zs.avail_in = (uInt)src_len;
    zs.next_out = compressed;
    zs.avail_out = (uInt)cap;
    if (deflate(&zs, Z_FINISH) != Z_STREAM_END) {
        fprintf(stderr, "FAIL: deflate(Z_FINISH) rc=%d\n", zs.total_in >= 0 ? 0 : 0);
        deflateEnd(&zs);
        return 1;
    }
    *dest_len = zs.total_out;
    deflateEnd(&zs);
    return 0;
}

int main(void) {
    printf("=== fast_zlib HarmonyOS 专项测试 (OHOS aarch64) ===\n");

    /* ① 快速匹配实现符号核验 */
    printf("fast_lm_copyright: %s\n", fast_lm_copyright);
    if (strstr(fast_lm_copyright, "Fast match finder for zlib") == NULL) {
        fprintf(stderr, "FAIL: fast_lm_copyright 内容不符（快速匹配实现未接入）\n");
        return 1;
    }
    printf("[ok] 快速匹配实现已链接进 OHOS 产物 (fast_lm_copyright 存在)\n");

    /* ② 构造混合数据：可压缩文本 + 随机尾部（触发未对齐访问路径） */
    const size_t src_len = 1024 * 1024;
    unsigned char *input = (unsigned char *)malloc(src_len);
    if (!input) { fprintf(stderr, "FAIL: malloc\n"); return 1; }
    const char *block =
        "fast_zlib HarmonyOS PC port: optimized longest_match for zlib compression. ";
    size_t i = 0;
    while (i < src_len) {
        size_t n = strlen(block);
        if (i + n > src_len) n = src_len - i;
        memcpy(input + i, block, n);
        i += n;
    }
    unsigned int seed = 0xA5E2C9;
    for (i = src_len - 16384; i < src_len; i++) {
        seed = seed * 1103515245u + 12345u;
        input[i] = (unsigned char)(seed >> 16);
    }

    /* ③ 一次性 compress2/uncompress 往返 */
    unsigned long dest_len = compressBound(src_len);
    unsigned char *compressed = (unsigned char *)malloc(dest_len);
    if (!compressed) { fprintf(stderr, "FAIL: malloc(compressed)\n"); free(input); return 1; }
    int ret = compress2(compressed, &dest_len, input, src_len, 9);
    if (ret != Z_OK) {
        fprintf(stderr, "FAIL: compress2 rc=%d\n", ret);
        free(input); free(compressed); return 1;
    }
    printf("compress2 OK: src=%lu -> dest=%lu (ratio %.2f)\n",
           src_len, dest_len, (double)dest_len / (double)src_len);
    if (dest_len >= src_len) {
        fprintf(stderr, "FAIL: 未压缩\n");
        free(input); free(compressed); return 1;
    }
    unsigned long out_len = src_len;
    unsigned char *decompressed = (unsigned char *)malloc(out_len);
    if (!decompressed) { fprintf(stderr, "FAIL: malloc(decompressed)\n"); free(input); free(compressed); return 1; }
    ret = uncompress(decompressed, &out_len, compressed, dest_len);
    if (ret != Z_OK || out_len != src_len || memcmp(input, decompressed, src_len) != 0) {
        fprintf(stderr, "FAIL: uncompress 往返不一致 (rc=%d out_len=%lu)\n", ret, out_len);
        free(input); free(compressed); free(decompressed); return 1;
    }
    printf("[ok] compress2/uncompress 1MB 往返一致 (OHOS aarch64)\n");

    /* ④ 流式 deflate/inflate（Z_FINISH 边界）往返 */
    unsigned long stream_len = 0;
    unsigned char *stream_c = (unsigned char *)malloc(dest_len);
    if (!stream_c) { fprintf(stderr, "FAIL: malloc(stream_c)\n"); free(input); free(compressed); free(decompressed); return 1; }
    if (roundtrip_stream(input, src_len, stream_c, dest_len, &stream_len) != 0) {
        free(input); free(compressed); free(decompressed); free(stream_c); return 1;
    }
    unsigned long stream_out = src_len;
    unsigned char *stream_d = (unsigned char *)malloc(stream_out);
    if (!stream_d) { fprintf(stderr, "FAIL: malloc(stream_d)\n"); free(input); free(compressed); free(decompressed); free(stream_c); return 1; }
    z_stream iz;
    memset(&iz, 0, sizeof(iz));
    if (inflateInit(&iz) != Z_OK) {
        fprintf(stderr, "FAIL: inflateInit\n");
        free(input); free(compressed); free(decompressed); free(stream_c); free(stream_d); return 1;
    }
    iz.next_in = stream_c;
    iz.avail_in = (uInt)stream_len;
    iz.next_out = stream_d;
    iz.avail_out = (uInt)stream_out;
    ret = inflate(&iz, Z_FINISH);
    inflateEnd(&iz);
    if (ret != Z_STREAM_END || iz.total_out != src_len ||
        memcmp(input, stream_d, src_len) != 0) {
        fprintf(stderr, "FAIL: 流式 inflate 往返不一致 (rc=%d out=%lu)\n", ret, iz.total_out);
        free(input); free(compressed); free(decompressed); free(stream_c); free(stream_d); return 1;
    }
    printf("[ok] 流式 deflate/inflate 1MB 往返一致 (Z_FINISH 边界, OHOS aarch64)\n");

    /* ⑤ zlibVersion 兼容性 */
    printf("zlibVersion: %s\n", zlibVersion());
    if (strcmp(zlibVersion(), "1.2.13") != 0) {
        fprintf(stderr, "FAIL: 版本不符 %s\n", zlibVersion());
        return 1;
    }
    printf("[ok] zlib 兼容版本 1.2.13\n");

    free(input); free(compressed); free(decompressed); free(stream_c); free(stream_d);
    printf("PASS: fast_zlib HarmonyOS 专项测试全部通过 (OHOS aarch64)\n");
    return 0;
}
