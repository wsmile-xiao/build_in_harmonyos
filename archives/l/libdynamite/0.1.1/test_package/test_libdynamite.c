/* Consumer test for libdynamite 0.1.1 on OHOS PC.
 *
 * Exercises the delivered library through its public API only: the
 * explode decompressor is driven with a PKWARE "implode" stream built
 * by this test (raw representation header + literal tokens + the
 * end-of-stream token), and the decoded bytes must match the source
 * text exactly for every supported dictionary size.  Bad-format and
 * unsupported-representation headers must be reported through the
 * documented DynamiteResult values.  Exit code is the verdict.
 */
#include <libdynamite.h>

#include <stdio.h>
#include <string.h>

#define OUT_LIMIT 4096

/* one context shared by both callbacks (dynamite_explode passes a
 * single cookie to reader and writer) */
typedef struct {
    const unsigned char *in;
    size_t in_len;
    size_t in_pos;
    unsigned char out[OUT_LIMIT];
    size_t out_len;
} Context;

static size_t reader_cb(void *buffer, size_t size, void *cookie) {
    Context *ctx = (Context *)cookie;
    size_t remaining = ctx->in_len - ctx->in_pos;
    size_t n = size < remaining ? size : remaining;
    if (n)
        memcpy(buffer, ctx->in + ctx->in_pos, n);
    ctx->in_pos += n;
    return n;
}

static size_t writer_cb(void *buffer, size_t size, void *cookie) {
    Context *ctx = (Context *)cookie;
    if (ctx->out_len + size > OUT_LIMIT)
        return 0;
    memcpy(ctx->out + ctx->out_len, buffer, size);
    ctx->out_len += size;
    return size;
}

/* Bit writer matching the library's bit order: dynamite_read_bit()
 * takes the LSB of the current byte first, so bits are packed
 * little-endian inside each byte. */
typedef struct {
    unsigned char data[2048];
    size_t len;
    unsigned bits;
} BitWriter;

static void emit_bit(BitWriter *bw, unsigned bit) {
    if (bw->bits % 8 == 0)
        bw->data[bw->len++] = 0;
    if (bit)
        bw->data[bw->len - 1] |= (unsigned char)(1u << (bw->bits % 8));
    bw->bits++;
}

static void emit_literal(BitWriter *bw, unsigned char byte) {
    emit_bit(bw, 0); /* literal token */
    for (int i = 0; i < 8; ++i)
        emit_bit(bw, (byte >> i) & 1u); /* payload, least significant first */
}

static void emit_end_of_stream(BitWriter *bw) {
    /* control token whose copy length is 519 (the library's EOF marker):
     * 2+2+2 bits of 0, one more 0, then 8 bits of 1 (264 + 255 = 519) */
    emit_bit(bw, 1);
    emit_bit(bw, 0); emit_bit(bw, 0);
    emit_bit(bw, 0); emit_bit(bw, 0);
    emit_bit(bw, 0); emit_bit(bw, 0);
    emit_bit(bw, 0);
    for (int i = 0; i < 8; ++i)
        emit_bit(bw, 1);
}

static size_t build_stream(unsigned char *out, unsigned char dict_bits,
                           const unsigned char *text, size_t text_len) {
    BitWriter bw;
    memset(&bw, 0, sizeof bw);
    for (size_t i = 0; i < text_len; ++i)
        emit_literal(&bw, text[i]);
    emit_end_of_stream(&bw);
    out[0] = 0;        /* raw representation */
    out[1] = dict_bits; /* dictionary size selector: 4, 5 or 6 */
    memcpy(out + 2, bw.data, bw.len);
    return bw.len + 2;
}

static int failures = 0;

static void check(int condition, const char *what) {
    printf("%s %s\n", condition ? "ok  -" : "FAIL-", what);
    if (!condition)
        ++failures;
}

int main(void) {
    static const unsigned char text[] =
        "Hello, DYNAMITE! PKWARE explode streams decode here.";
    const size_t text_len = sizeof text - 1;
    static const unsigned char dict_bits[3] = {4, 5, 6};

    for (int d = 0; d < 3; ++d) {
        unsigned char stream[2048];
        Context ctx;
        char label[64];

        memset(&ctx, 0, sizeof ctx);
        ctx.in_len = build_stream(stream, dict_bits[d], text, text_len);
        ctx.in = stream;

        DynamiteResult result = dynamite_explode(reader_cb, writer_cb, &ctx);
        snprintf(label, sizeof label,
                 "round trip decodes %zu bytes with dictionary size %u",
                 text_len, (unsigned)dict_bits[d]);
        check(result == DYNAMITE_SUCCESS
                  && ctx.out_len == text_len
                  && memcmp(ctx.out, text, text_len) == 0,
              label);
    }

    /* unsupported representation (header byte 1): must be reported */
    {
        unsigned char stream[8] = {1, 4, 0, 0, 0, 0, 0, 0};
        Context ctx;
        memset(&ctx, 0, sizeof ctx);
        ctx.in = stream;
        ctx.in_len = sizeof stream;
        check(dynamite_explode(reader_cb, writer_cb, &ctx)
                  == DYNAMITE_NOT_IMPLEMENTED,
              "encoded-literal representation reports NOT_IMPLEMENTED");
    }

    /* unexpected representation (header byte 2): bad format */
    {
        unsigned char stream[8] = {2, 4, 0, 0, 0, 0, 0, 0};
        Context ctx;
        memset(&ctx, 0, sizeof ctx);
        ctx.in = stream;
        ctx.in_len = sizeof stream;
        check(dynamite_explode(reader_cb, writer_cb, &ctx)
                  == DYNAMITE_BAD_FORMAT,
              "unknown representation reports BAD_FORMAT");
    }

    /* unsupported dictionary size (header byte 7): bad format */
    {
        unsigned char stream[8] = {0, 7, 0, 0, 0, 0, 0, 0};
        Context ctx;
        memset(&ctx, 0, sizeof ctx);
        ctx.in = stream;
        ctx.in_len = sizeof stream;
        check(dynamite_explode(reader_cb, writer_cb, &ctx)
                  == DYNAMITE_BAD_FORMAT,
              "unsupported dictionary size reports BAD_FORMAT");
    }

    if (failures)
        printf("# %d check(s) failed\n", failures);
    else
        puts("# all checks passed");
    return failures ? 1 : 0;
}
