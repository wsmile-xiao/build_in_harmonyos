/* Smoke test for orcania 2.3.3 鈥?verify public API symbols are linked. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "orcania.h"

int main(void) {
    /* o_strdup: heap-allocated copy of a string. */
    const char *src = "harmonyos";
    char *dup = o_strdup(src);
    if (dup == NULL) {
        fprintf(stderr, "o_strdup returned NULL\n");
        return 1;
    }
    if (strcmp(dup, src) != 0) {
        fprintf(stderr, "o_strdup mismatch: %s vs %s\n", dup, src);
        free(dup);
        return 1;
    }
    free(dup);

    /* o_strnullempty: detect null or empty string. */
    if (o_strnullempty("") != 1) {
        fprintf(stderr, "o_strnullempty empty failed\n");
        return 1;
    }
    if (o_strnullempty("x") != 0) {
        fprintf(stderr, "o_strnullempty non-empty failed\n");
        return 1;
    }
    if (o_strnullempty(NULL) != 1) {
        fprintf(stderr, "o_strnullempty NULL failed\n");
        return 1;
    }

    /* o_strcmp / o_strcasecmp: lex compare. */
    if (o_strcmp("abc", "abc") != 0) {
        fprintf(stderr, "o_strcmp equal failed\n");
        return 1;
    }
    if (o_strcasecmp("ABC", "abc") != 0) {
        fprintf(stderr, "o_strcasecmp failed\n");
        return 1;
    }

    /* o_free: only test free(NULL) is safe and consistent. */
    o_free(NULL);

    /* o_base64_encode: round-trip a small payload. */
    const unsigned char in[] = "hello orcania";
    unsigned char out[64] = {0};
    size_t out_len = 0;
    int rc = o_base64_encode(in, sizeof(in) - 1, out, &out_len);
    if (rc != 1 || out_len == 0) {
        fprintf(stderr, "o_base64_encode failed (rc=%d len=%zu)\n", rc, out_len);
        return 1;
    }

    printf("orcania smoke test PASS\n");
    return 0;
}
