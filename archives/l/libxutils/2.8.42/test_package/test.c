#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "xutils/xver.h"
#include "xutils/crypt/base64.h"

/* 消费者视角验证（R34）：实际调用被测库 API 并断言结果 */
int main(void)
{
    const char *version = XUtils_Version();
    if (!version || strlen(version) == 0) {
        fprintf(stderr, "FAIL: XUtils_Version() returned empty\n");
        return 1;
    }

    const uint8_t plain[] = "hello libxutils on OHOS";
    size_t len = strlen((const char *)plain);
    char *enc = XBase64_Encrypt(plain, &len);
    if (!enc) {
        fprintf(stderr, "FAIL: XBase64_Encrypt() returned NULL\n");
        return 1;
    }
    len = strlen(enc);
    char *dec = XBase64_Decrypt((const uint8_t *)enc, &len);
    if (!dec) {
        fprintf(stderr, "FAIL: XBase64_Decrypt() returned NULL\n");
        free(enc);
        return 1;
    }
    int ok = (strcmp(dec, (const char *)plain) == 0);
    free(enc);
    free(dec);
    if (!ok) {
        fprintf(stderr, "FAIL: base64 roundtrip mismatch\n");
        return 1;
    }

    printf("test libxutils %s: OK (base64 roundtrip passed)\n", version);
    return 0;
}