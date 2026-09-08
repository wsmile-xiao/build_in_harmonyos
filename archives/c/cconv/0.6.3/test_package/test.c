/*
 * test_package 消费者测试 — 实际调用 libcconv API 做简体→繁体转换验证
 * R34: 测试必须实质调用被测包 API，禁止空壳 print。
 */
#include <stdio.h>
#include <string.h>
#include "cconv.h"

int main(void)
{
    const char *in = "头发剪了，后天才到";
    char *pin = (char *)in;
    size_t inlen = strlen(in);
    char out[1024] = {0};
    char *pout = out;
    size_t outlen = sizeof(out) - 1;
    cconv_t cd;
    size_t ret;

    /* 简体 UTF8-HANS -> 繁体 UTF8-HANT */
    cd = cconv_open(CCONV_CODE_UHT, CCONV_CODE_UHS);
    if (cd == (cconv_t)(-1)) {
        printf("FAIL: cconv_open(UTF8-HANT, UTF8-HANS)\n");
        return 1;
    }

    ret = cconv(cd, &pin, &inlen, &pout, &outlen);
    if (ret == (size_t)(-1)) {
        printf("FAIL: cconv returned (size_t)-1 (EILSEQ)\n");
        cconv_close(cd);
        return 1;
    }
    cconv_close(cd);

    printf("converted(%zu bytes): %s\n", ret, out);
    /* 期望：全部核心字转换为繁体 */
    if (strcmp(out, "頭髮剪了，後天才到") == 0) {
        printf("PASS: simplified->traditional conversion OK\n");
        return 0;
    }
    printf("FAIL: unexpected output '%s'\n", out);
    return 1;
}