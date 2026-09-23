#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lzx_compress.h"

typedef struct {
    const unsigned char *data;
    size_t size;
    size_t pos;
} inbuf_t;

typedef struct {
    unsigned char *data;
    size_t cap;
    size_t len;
} outbuf_t;

static int test_get_bytes(void *arg, int n, void *buf)
{
    inbuf_t *ib = (inbuf_t *)arg;
    size_t avail = ib->size - ib->pos;
    size_t take = (n > avail) ? avail : (size_t)n;
    if (take > 0) {
        memcpy(buf, ib->data + ib->pos, take);
        ib->pos += take;
    }
    return (int)take;
}

static int test_put_bytes(void *arg, int n, void *buf)
{
    outbuf_t *ob = (outbuf_t *)arg;
    if ((size_t)(ob->len + n) > ob->cap) {
        size_t ncap = ob->cap ? ob->cap * 2 : 4096;
        while (ncap < (size_t)(ob->len + n))
            ncap *= 2;
        unsigned char *nd = (unsigned char *)realloc(ob->data, ncap);
        if (!nd)
            return 0;
        ob->data = nd;
        ob->cap = ncap;
    }
    memcpy(ob->data + ob->len, buf, (size_t)n);
    ob->len += n;
    return n;
}

static int test_at_eof(void *arg)
{
    inbuf_t *ib = (inbuf_t *)arg;
    return ib->pos >= ib->size;
}

static void test_mark_frame(void *arg, uint32_t uncomp, uint32_t comp)
{
    (void)arg;
    (void)uncomp;
    (void)comp;
}

int main(void)
{
    /* ~512KB of highly repetitive data: compressible well below window size (15 => 32KB) */
    const size_t INPUT_SIZE = 512 * 1024;
    unsigned char *input = (unsigned char *)malloc(INPUT_SIZE);
    if (!input)
        return 2;
    static const char pattern[] =
        "OpenHarmony PC liblzxcomp LZX compression test 20050705 - "
        "window sliding LZ77 with Huffman coding. ";
    size_t pidx = 0;
    for (size_t i = 0; i < INPUT_SIZE; i++) {
        input[i] = (unsigned char)pattern[pidx];
        pidx = (pidx + 1) % (sizeof(pattern) - 1);
    }

    inbuf_t ib = {input, INPUT_SIZE, 0};
    outbuf_t ob = {NULL, 0, 0};
    lzx_data *lzxd = NULL;
    lzx_results lzxr;

    int rc = lzx_init(&lzxd, 15, test_get_bytes, &ib, test_at_eof,
                      test_put_bytes, &ob, test_mark_frame, NULL);
    if (rc != 0 || !lzxd) {
        fprintf(stderr, "lzx_init failed rc=%d\n", rc);
        return 2;
    }

    while (!test_at_eof(&ib)) {
        rc = lzx_compress_block(lzxd, 1 << 15, 1);
        if (rc < 0) {
            fprintf(stderr, "lzx_compress_block failed rc=%d\n", rc);
            return 2;
        }
    }

    rc = lzx_finish(lzxd, &lzxr);
    if (rc != 0) {
        fprintf(stderr, "lzx_finish failed rc=%d\n", rc);
        return 2;
    }

    long in_len = lzxr.len_uncompressed_input;
    long out_len = lzxr.len_compressed_output;
    fprintf(stderr, "compressed: %ld, uncompressed %ld\n", out_len, in_len);

    free(ob.data);
    free(input);

    if (in_len != (long)INPUT_SIZE) {
        fprintf(stderr, "uncompressed length mismatch: %ld != %zu\n", in_len, INPUT_SIZE);
        return 2;
    }
    if (out_len <= 0 || out_len >= in_len) {
        fprintf(stderr, "no real compression achieved: %ld >= %ld\n", out_len, in_len);
        return 2;
    }
    printf("test liblzxcomp 20050705: OK (in=%ld out=%ld)\n", in_len, out_len);
    return 0;
}