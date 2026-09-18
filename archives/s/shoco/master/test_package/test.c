#include <stdio.h>
#include <string.h>

#include "shoco.h"

int main(void) {
    /* test_package L1 测试：可真实验证 shoco 公开 API 在 OHOS 上的可用性。
     * 注意：不依赖 assert()——OHOS profile 为 Release（NDEBUG 下 assert 被编译掉，
     * 显式 if + 非零返回保证验证在 Release 构建中真实生效（W4 审计 P2）。 */
    const char *in = "HarmonyOS PC shoco test_package consumer";
    char comp[1024];
    char out[1024];
    size_t comp_len, out_len;

    /* 1) 压缩公开 API */
    comp_len = shoco_compress(in, strlen(in), comp, sizeof(comp));
    if (comp_len == 0 || comp_len > strlen(in)) {
        fprintf(stderr, "FAIL: compress invalid ret=%zu in=%zu\n", comp_len, strlen(in));
        return 1;
    }

    /* 2) 解压公开 API 并要求回环一致 */
    out_len = shoco_decompress(comp, comp_len, out, sizeof(out));
    if (out_len != strlen(in)) {
        fprintf(stderr, "FAIL: decompress len mismatch out=%zu in=%zu\n", out_len, strlen(in));
        return 1;
    }
    if (memcmp(out, in, out_len) != 0) {
        fprintf(stderr, "FAIL: roundtrip content mismatch\n");
        return 1;
    }

    printf("shoco roundtrip OK: %zu bytes -> %zu bytes\n", strlen(in), comp_len);
    puts("test shoco master: PASS");
    return 0;
}