// 消费者用例（模拟业务上层组件/应用）：
// 仅通过 shoco 已安装导出的公开头文件 shoco.h 与公开 API
// （shoco_compress / shoco_decompress）与正常链接目标（libshoco.a）
// 使用该三方库，验证第三方使用者在 OHOS PC 上可编译、链接、调用并正常运行。
#include <stdio.h>
#include <string.h>

#include "shoco.h"

/* 模拟上层应用：将一组短字符串压缩后存入"存储层"再从"存储层"解压还原 */
static int store_and_load(const char *text, size_t len) {
    char compressed[4096];
    char restored[4096];
    size_t clen, rlen;

    clen = shoco_compress(text, len, compressed, sizeof(compressed));
    if (clen == 0 || clen > sizeof(compressed)) {
        fprintf(stderr, "consumer: compress failed (ret=%zu)\n", clen);
        return 1;
    }

    rlen = shoco_decompress(compressed, clen, restored, sizeof(restored));
    if (rlen != len || memcmp(restored, text, len) != 0) {
        fprintf(stderr, "consumer: roundtrip mismatch (in=%zu out=%zu)\n", len, rlen);
        return 1;
    }
    printf("consumer: '%s' (%zu B) -> %zu B (%.0f%% saved), roundtrip OK\n",
           text, len, clen, 100.0 * (1.0 - (double)clen / (double)len));
    return 0;
}

int main(void) {
    int rc = 0;

    rc |= store_and_load("consumer application log line: resource manager started", strlen("consumer application log line: resource manager started"));
    rc |= store_and_load("app://com.example.demo/pages/index", 34);
    rc |= store_and_load("hello", 5);
    rc |= store_and_load("a", 1);

    if (rc == 0) {
        puts("consumer: all public-API roundtrips passed");
        return 0;
    }
    puts("consumer: FAILED");
    return 1;
}