/* test_package/test.c — janet 1.41.2 链接 + 真实符号调用 (R34) */
#include <stdio.h>
#include "janet.h"

int main(void) {
    /* 调用 janet C API 核心符号，证明库可用 */
    janet_init();
    printf("janet: janet_init() ok (version=%s)\n", JANET_VERSION);
    janet_deinit();
    printf("janet: janet_deinit() ok\n");
    return 0;
}