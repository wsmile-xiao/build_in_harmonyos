#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "lzham.h"

/*
 * 消费者验证测试（R34：必须实质调用被测包 API）
 * 使用 lzham 官方 API 执行一次完整的 压缩 -> 解压 -> 字节级比对 往返，
 * 并在 HarmonyOS (OHOS) 平台上报平台宏，验证 __OHOS__ 构建守卫生效。
 */
int main(void) {
    static const lzham_uint8 input[] =
        "lzham conan test_package: HarmonyOS consumer validation. "
        "LZHAM is a lossless data compression codec with zlib-compatible API. "
        "This payload is deliberately repeated to give the compressor real data "
        "to work with: lzham lzham lzham lzham lzham lzham lzham lzham.";

    const size_t src_len = sizeof(input);
    lzham_uint8 cmp_buf[4096];
    lzham_uint8 dec_buf[4096];
    size_t cmp_len = sizeof(cmp_buf);
    size_t dec_len = sizeof(dec_buf);
    lzham_uint32 cmp_adler = 0, dec_adler = 0;

    lzham_compress_params cparams;
    memset(&cparams, 0, sizeof(cparams));
    cparams.m_struct_size = sizeof(cparams);
    cparams.m_dict_size_log2 = 18;          /* 256KB dict, portable */
    cparams.m_level = LZHAM_COMP_LEVEL_UBER;
    cparams.m_max_helper_threads = 1;

    lzham_compress_status_t cs = lzham_compress_memory(
        &cparams, cmp_buf, &cmp_len, input, src_len, &cmp_adler);
    if (cs != LZHAM_COMP_STATUS_SUCCESS) {
        fprintf(stderr, "FAIL: lzham_compress_memory status=%d\n", (int)cs);
        return 1;
    }
    if (cmp_len >= src_len) {
        fprintf(stderr, "FAIL: compressed size %zu >= source %zu\n", cmp_len, src_len);
        return 1;
    }

    lzham_decompress_params dparams;
    memset(&dparams, 0, sizeof(dparams));
    dparams.m_struct_size = sizeof(dparams);
    dparams.m_dict_size_log2 = 18;
    dparams.m_decompress_flags = LZHAM_DECOMP_FLAG_COMPUTE_ADLER32;

    lzham_decompress_status_t ds = lzham_decompress_memory(
        &dparams, dec_buf, &dec_len, cmp_buf, cmp_len, &dec_adler);
    if (ds != LZHAM_DECOMP_STATUS_SUCCESS) {
        fprintf(stderr, "FAIL: lzham_decompress_memory status=%d\n", (int)ds);
        return 1;
    }
    if (dec_len != src_len || memcmp(dec_buf, input, src_len) != 0) {
        fprintf(stderr, "FAIL: roundtrip mismatch (dec_len=%zu src_len=%zu)\n", dec_len, src_len);
        return 1;
    }
    if (cmp_adler != dec_adler || cmp_adler == 0) {
        fprintf(stderr, "FAIL: adler32 mismatch cmp=0x%08X dec=0x%08X\n", cmp_adler, dec_adler);
        return 1;
    }

#ifdef __OHOS__
    printf("PASS: lzham consumer roundtrip on HarmonyOS (__OHOS__), "
           "cmp=%zuB -> dec=%zuB, adler=0x%08X\n", cmp_len, dec_len, cmp_adler);
#else
    printf("PASS: lzham consumer roundtrip, cmp=%zuB -> dec=%zuB, adler=0x%08X\n",
           cmp_len, dec_len, cmp_adler);
#endif
    return 0;
}
