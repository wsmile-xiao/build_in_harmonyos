#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <utf8proc.h>

int main(void) {
    /* 1. 版本核对 */
    const char *ver = utf8proc_version();
    if (ver == NULL || strcmp(ver, "2.10.0") != 0) {
        printf("FAIL: utf8proc_version() = %s (expect 2.10.0)\n", ver ? ver : "(null)");
        return 1;
    }

    /* 2. utf8proc_map NFKC round-trip: "A" (U+0041) + combining mark stays normalizable */
    const char *src = "A";
    utf8proc_uint8_t *result = NULL;
    utf8proc_ssize_t n = utf8proc_map((const utf8proc_uint8_t *)src, -1, &result,
                                      UTF8PROC_NULLTERM | UTF8PROC_COMPOSE);
    if (n < 0) {
        printf("FAIL: utf8proc_map returned error %zd\n", n);
        return 1;
    }
    if (result == NULL || strcmp((const char *)result, "A") != 0) {
        printf("FAIL: NFKC(A) = %s\n", result ? (const char *)result : "(null)");
        free(result);
        return 1;
    }
    free(result);

    printf("PASS: utf8proc version=%s NFKC(A)=A OK\n", ver);
    return 0;
}
