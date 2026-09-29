#include <stdio.h>
#include <string.h>
#include "strings.h"
#include "strutil.h"

int main(void) {
    /* 真实调用 erhling-clibs API：str_strlcpy / str_strlcat / str_hash */
    char buf[64];
    int rc = 0;

    memset(buf, 0, sizeof(buf));
    size_t n = str_strlcpy(buf, "erhling-clibs", sizeof(buf));
    if (n != 13 || strcmp(buf, "erhling-clibs") != 0) {
        printf("FAIL str_strlcpy: n=%zu buf=%s\n", n, buf);
        return 1;
    }

    size_t m = str_strlcat(buf, "-ok", sizeof(buf));
    if (m != 16 || strcmp(buf, "erhling-clibs-ok") != 0) {
        printf("FAIL str_strlcat: m=%zu buf=%s\n", m, buf);
        return 1;
    }

    unsigned int h1 = str_hash("hello");
    unsigned int h2 = str_hash("hello");
    if (h1 != h2 || h1 == 0) {
        printf("FAIL str_hash: h1=%u h2=%u\n", h1, h2);
        return 1;
    }

    const char *esc = str_escape("a\"b\nc", buf, sizeof(buf));
    if (!esc || strcmp(esc, "a\\\"b\\nc") != 0) {
        printf("FAIL str_escape: %s\n", esc ? esc : "(null)");
        return 1;
    }

    printf("test erhling-clibs 2.1.1: OK (str_strlcpy/str_strlcat/str_hash/str_escape)\n");
    return rc;
}
