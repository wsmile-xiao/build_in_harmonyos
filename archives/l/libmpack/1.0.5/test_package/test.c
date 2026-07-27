#include <stdio.h>
#include <string.h>
#include "mpack.h"

int main(void)
{
    char buf[256];
    size_t blen = sizeof(buf);
    char *bp = buf;

    /* Pack a uint value */
    mpack_tokbuf_t wb;
    mpack_tokbuf_init(&wb);
    mpack_token_t tok = mpack_pack_uint(42);
    int rc = mpack_write(&wb, &bp, &blen, &tok);
    if (rc != 0) {
        fprintf(stderr, "mpack_write failed: %d\n", rc);
        return 1;
    }

    /* Read it back */
    const char *rbp = buf;
    size_t rblen = (size_t)(bp - buf);
    mpack_tokbuf_t rb;
    mpack_tokbuf_init(&rb);
    mpack_token_t out_tok;
    rc = mpack_read(&rb, &rbp, &rblen, &out_tok);
    if (rc != 0) {
        fprintf(stderr, "mpack_read failed: %d\n", rc);
        return 1;
    }

    /* Verify */
    mpack_uintmax_t val = mpack_unpack_uint(out_tok);
    if (val != 42) {
        fprintf(stderr, "Expected 42, got %llu\n", (unsigned long long)val);
        return 1;
    }

    printf("libmpack round-trip test passed: wrote and read uint 42\n");
    return 0;
}
