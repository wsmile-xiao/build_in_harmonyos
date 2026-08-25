#include <stdio.h>
#include <string.h>

/* skalibs headers — substantively exercise the library API (R34) */
#include <skalibs/stralloc.h>
#include <skalibs/bytestr.h>
#include <skalibs/buffer.h>

int main(void)
{
    /* Test 1: stralloc — allocate, copy, cat, shrink (core skalibs data struct) */
    stralloc sa = STRALLOC_ZERO;
    if (!stralloc_ready(&sa, 64)) {
        fprintf(stderr, "FAIL: stralloc_ready returned 0\n");
        return 1;
    }
    if (!stralloc_copys(&sa, "Hello, skalibs!")) {
        fprintf(stderr, "FAIL: stralloc_copys returned 0\n");
        stralloc_free(&sa);
        return 2;
    }
    if (!stralloc_cats(&sa, " Appended.")) {
        fprintf(stderr, "FAIL: stralloc_cats returned 0\n");
        stralloc_free(&sa);
        return 3;
    }
    /* sa.s now contains "Hello, skalibs! Appended." */
    if (sa.len != strlen("Hello, skalibs! Appended.")) {
        fprintf(stderr, "FAIL: stralloc len=%zu expected=%zu\n",
                sa.len, strlen("Hello, skalibs! Appended."));
        stralloc_free(&sa);
        return 4;
    }

    /* Test 2: bytestr — byte_diff / byte_chr (core string utilities) */
    const char *s = "skalibs-test";
    if (byte_chr(s, strlen(s), 'k') != 1) {
        fprintf(stderr, "FAIL: byte_chr did not find 'k' at position 1\n");
        stralloc_free(&sa);
        return 5;
    }
    if (byte_diff(s, 7, "skalibs") != 0) {
        fprintf(stderr, "FAIL: byte_diff mismatch on prefix\n");
        stralloc_free(&sa);
        return 6;
    }

    stralloc_shrink(&sa);
    stralloc_free(&sa);

    printf("skalibs API assertions: 6 passed\n");
    return 0;
}
