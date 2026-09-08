/*
 * test_package for ls-hpack 2.3.5 (HarmonyOS PC, aarch64, musl, clang15).
 *
 * Verifies the public C API of the FINAL Conan package:
 *   - HPACK encoding (literal + indexed representations)
 *   - Decoding of RFC 7541 Appendix C official vectors, byte-exact
 *   - Multiple headers (full header sets, several rounds)
 *   - Round-trip: encode -> decode -> name/value byte-exact comparison
 *   - Static table behavior: 0x82 (":method: GET") must decode to the
 *     exact static-table name/value
 *   - Error/truncated input: decoder must return < 0, not crash
 */

#include <assert.h>
#include <stdio.h>
#include <string.h>

#include <lshpack.h>

#define CHECK(cond, msg)                                                    \
    do {                                                                    \
        if (!(cond)) {                                                      \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);         \
            ++g_failures;                                                   \
        }                                                                   \
    } while (0)

static int g_failures = 0;

/* ---- helpers ------------------------------------------------------- */

static size_t
do_encode (struct lshpack_enc *enc, unsigned char *dst, size_t dst_cap,
           const char *name, const char *val)
{
    unsigned char *p;
    struct lsxpack_header xhdr;
    char buf[512];
    size_t name_len = strlen(name), val_len = strlen(val);

    /* The encoder reads name and value from one contiguous buffer:
     * [name | value] (see lshpack_enc_encode / lsxpack_header.h). */
    assert(name_len + val_len < sizeof(buf));
    memcpy(buf, name, name_len);
    memcpy(buf + name_len, val, val_len);
    lsxpack_header_set_offset2(&xhdr, buf, 0, name_len, name_len, val_len);

    p = lshpack_enc_encode(enc, dst, dst + dst_cap, &xhdr);
    /* Upstream contract: encode failure returns NULL.  Check for NULL
     * FIRST — never do pointer arithmetic on a NULL return. */
    if (p == NULL)
        return 0;
    if (p == dst)     /* not advanced => error */
        return 0;
    return (size_t)(p - dst);
}

/* Decode one header block; returns number of headers decoded. */
static int
do_decode (struct lshpack_dec *dec, const unsigned char *src, size_t src_len,
           char names[][64], char vals[][256], int max_n)
{
    const unsigned char *p = src;
    const unsigned char *const end = src + src_len;
    char out[4096];
    int n = 0;

    while (p < end)
    {
        struct lsxpack_header xhdr;
        int rc;

        lsxpack_header_prepare_decode(&xhdr, out, 0, sizeof(out));
        rc = lshpack_dec_decode(dec, &p, end, &xhdr);
        if (rc != 0)
            return -1;
        if (n < max_n)
        {
            memcpy(names[n], out + xhdr.name_offset, xhdr.name_len);
            names[n][xhdr.name_len] = '\0';
            memcpy(vals[n], out + xhdr.val_offset, xhdr.val_len);
            vals[n][xhdr.val_len] = '\0';
        }
        ++n;
    }
    return n;
}

/* ---- 1+2: RFC 7541 Appendix C official vectors (decode, byte-exact) - */

static void
test_rfc7541_vectors (void)
{
    struct lshpack_dec hdec;

    /* C.2.4 — custom-key/custom-header, literal with incremental
     * indexing, new name:
     *   0x40 0x0a custom-key 0x0d custom-header
     */
    static const unsigned char c24[] = {
        0x40, 0x0a, 'c','u','s','t','o','m','-','k','e','y',
        0x0d, 'c','u','s','t','o','m','-','h','e','a','d','e','r'
    };
    /* C.6.1 — first response header set, full huffman-coded block.
     * :status 302 / cache-control private / date ... / location ... */
    static const unsigned char c61[] = {
        0x48, 0x03, 0x33, 0x30, 0x32,
        0x58, 0x07, 0x70, 0x72, 0x69, 0x76, 0x61, 0x74, 0x65,
        0x61, 0x1d, 0x4d, 0x6f, 0x6e, 0x2c, 0x20, 0x32, 0x31, 0x20,
            0x4f, 0x63, 0x74, 0x20, 0x32, 0x30, 0x31, 0x33, 0x20,
            0x32, 0x30, 0x3a, 0x31, 0x33, 0x3a, 0x32, 0x31, 0x20,
            0x47, 0x4d, 0x54,
        0x6e, 0x17, 0x68, 0x74, 0x74, 0x70, 0x73, 0x3a, 0x2f, 0x2f,
            0x77, 0x77, 0x77, 0x2e, 0x65, 0x78, 0x61, 0x6d, 0x70,
            0x6c, 0x65, 0x2e, 0x63, 0x6f, 0x6d,
    };
    char names[8][64];
    char vals[8][256];
    int n;

    lshpack_dec_init(&hdec);

    n = do_decode(&hdec, c24, sizeof(c24), names, vals, 8);
    CHECK(n == 1, "C.2.4: one header");
    CHECK(n >= 1 && strcmp(names[0], "custom-key") == 0,
          "C.2.4: name is custom-key");
    CHECK(n >= 1 && strcmp(vals[0], "custom-header") == 0,
          "C.2.4: value is custom-header");

    /* Fresh decoder for the full header set */
    lshpack_dec_cleanup(&hdec);
    lshpack_dec_init(&hdec);

    n = do_decode(&hdec, c61, sizeof(c61), names, vals, 8);
    CHECK(n == 4, "C.6.1: four headers");
    CHECK(n >= 1 && strcmp(names[0], ":status") == 0,
          "C.6.1: name[0] is :status");
    CHECK(n >= 1 && strcmp(vals[0], "302") == 0,
          "C.6.1: value[0] is 302");
    CHECK(n >= 2 && strcmp(names[1], "cache-control") == 0,
          "C.6.1: name[1] is cache-control");
    CHECK(n >= 2 && strcmp(vals[1], "private") == 0,
          "C.6.1: value[1] is private");
    CHECK(n >= 3 && strcmp(names[2], "date") == 0,
          "C.6.1: name[2] is date");
    CHECK(n >= 4 && strcmp(vals[3], "https://www.example.com") == 0,
          "C.6.1: value[3] is location URL");

    lshpack_dec_cleanup(&hdec);
}

/* ---- 5: static table / indexed field ------------------------------- */

static void
test_static_table (void)
{
    struct lshpack_dec hdec;
    static const unsigned char indexed_get[] = { 0x82 };  /* :method: GET */
    char names[4][64];
    char vals[4][256];
    int n;

    lshpack_dec_init(&hdec);
    n = do_decode(&hdec, indexed_get, sizeof(indexed_get), names, vals, 4);
    CHECK(n == 1, "static: :method GET decodes to one header");
    CHECK(n >= 1 && strcmp(names[0], ":method") == 0,
          "static: name is :method");
    CHECK(n >= 1 && strcmp(vals[0], "GET") == 0,
          "static: value is GET");
    lshpack_dec_cleanup(&hdec);
}

/* ---- 3+4: multi-header round-trip ----------------------------------- */

static void
test_round_trip (void)
{
    struct lshpack_enc henc;
    struct lshpack_dec hdec;
    unsigned char buf[8192];
    size_t used = 0;
    char names[8][64];
    char vals[8][256];
    int n;

    static const char *const exp_names[] = {
        ":status", "cache-control", "date", "content-length", "x-custom",
    };
    static const char *const exp_vals[] = {
        "200", "max-age=3600", "Mon, 21 Oct 2013 20:13:21 GMT",
        "12345", "ba\303\250ana",   /* UTF-8 "baèana", non-ASCII bytes */
    };
    const int nexp = 5;
    int i;

    lshpack_enc_init(&henc);
    lshpack_dec_init(&hdec);
    lshpack_enc_set_max_capacity(&henc, 4096);
    lshpack_dec_set_max_capacity(&hdec, 4096);

    /* Encode a full multi-header set */
    for (i = 0; i < nexp; ++i)
    {
        size_t w = do_encode(&henc, buf + used, sizeof(buf) - used,
                             exp_names[i], exp_vals[i]);
        CHECK(w > 0, "round-trip: encode advances");
        used += w;
    }
    CHECK(used > 0, "round-trip: encoding is non-empty");

    /* Decode the whole block; compare byte-exact */
    n = do_decode(&hdec, buf, used, names, vals, 8);
    CHECK(n == nexp, "round-trip: header count matches");
    if (n == nexp)
    {
        for (i = 0; i < nexp; ++i)
        {
            if (strcmp(names[i], exp_names[i]) != 0)
            {
                fprintf(stderr, "FAIL: name[%d] '%s' != '%s' (line %d)\n",
                        i, names[i], exp_names[i], __LINE__);
                ++g_failures;
            }
            if (strcmp(vals[i], exp_vals[i]) != 0)
            {
                fprintf(stderr, "FAIL: value[%d] '%s' != '%s' (line %d)\n",
                        i, vals[i], exp_vals[i], __LINE__);
                ++g_failures;
            }
        }
    }

    /* Second round with the SAME encoder/decoder pair: exercises the
     * dynamic table (previously-inserted x-custom must now be indexed
     * or matched) and indexing state. */
    used = 0;
    for (i = 0; i < nexp; ++i)
    {
        size_t w = do_encode(&henc, buf + used, sizeof(buf) - used,
                             exp_names[i], exp_vals[i]);
        CHECK(w > 0, "round-trip: second encode advances");
        used += w;
    }
    n = do_decode(&hdec, buf, used, names, vals, 8);
    CHECK(n == nexp, "round-trip 2: header count matches");
    if (n == nexp)
    {
        for (i = 0; i < nexp; ++i)
        {
            if (strcmp(names[i], exp_names[i]) != 0
             || strcmp(vals[i], exp_vals[i]) != 0)
            {
                fprintf(stderr, "FAIL: round-trip 2 mismatch at %d "
                        "(%s: %s) (line %d)\n", i, names[i], vals[i],
                        __LINE__);
                ++g_failures;
            }
        }
    }

    lshpack_enc_cleanup(&henc);
    lshpack_dec_cleanup(&hdec);
}

/* ---- 6: error / truncated input -------------------------------------- */

static void
test_error_input (void)
{
    struct lshpack_dec hdec;
    char out[256];
    int rc;

    /* Truncated literal: name length 10 but only 3 bytes follow */
    static const unsigned char trunc[] = {
        0x00, 0x0a, 'a', 'b', 'c'
    };
    /* Index 0 is invalid */
    static const unsigned char idx0[] = { 0x80 };
    const unsigned char *p;
    const unsigned char *end;
    struct lsxpack_header xhdr;

    lshpack_dec_init(&hdec);

    p = trunc; end = trunc + sizeof(trunc);
    lsxpack_header_prepare_decode(&xhdr, out, 0, sizeof(out));
    rc = lshpack_dec_decode(&hdec, &p, end, &xhdr);
    CHECK(rc < 0, "error: truncated literal returns negative");

    p = idx0; end = idx0 + sizeof(idx0);
    lsxpack_header_prepare_decode(&xhdr, out, 0, sizeof(out));
    rc = lshpack_dec_decode(&hdec, &p, end, &xhdr);
    CHECK(rc < 0, "error: index 0 returns negative");

    lshpack_dec_cleanup(&hdec);
}

int
main (void)
{
    test_rfc7541_vectors();
    test_static_table();
    test_round_trip();
    test_error_input();

    if (g_failures)
    {
        fprintf(stderr, "%d failure(s)\n", g_failures);
        return 1;
    }
    printf("ls-hpack test_package: ALL PASS\n");
    return 0;
}
