/* blake2b.c - minimal portable BLAKE2b (RFC 7693) vendored for libequihash.
 *
 * CC0 1.0 Universal (same license as libequihash itself).
 *
 * Implements the reference algorithm from RFC 7693 Appendix A / Section 3:
 * 64-bit words, little-endian load/store, 12 rounds over the sigma schedule,
 * parameter-block XOR into h, full-block buffering, zero padding of the final
 * block, last-block flag (f[0] = all-ones), 128-bit counter (high word is 0;
 * inputs here are tiny). Verified against the official vectors:
 *   blake2b-256("") = 0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8
 */

#include "blake2b.h"

#include <string.h>

#define BLAKE2B_BLOCKBYTES 128
#define BLAKE2B_OUTBYTES 64

static const unsigned long long blake2b_iv[8] = {
    0x6a09e667f3bcc908ULL, 0xbb67ae8584caa73bULL,
    0x3c6ef372fe94f82bULL, 0xa54ff53a5f1d36f1ULL,
    0x510e527fade682d1ULL, 0x9b05688c2b3e6c1fULL,
    0x1f83d9abfb41bd6bULL, 0x5be0cd19137e2179ULL
};

static const unsigned char blake2b_sigma[12][16] = {
    { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15},
    {14,10, 4, 8, 9,15,13, 6, 1,12, 0, 2,11, 7, 5, 3},
    {11, 8,12, 0, 5, 2,15,13,10,14, 3, 6, 7, 1, 9, 4},
    { 7, 9, 3, 1,13,12,11,14, 2, 6, 5,10, 4, 0,15, 8},
    { 9, 0, 5, 7, 2, 4,10,15,14, 1,11,12, 6, 8, 3,13},
    { 2,12, 6,10, 0,11, 8, 3, 4,13, 7, 5,15,14, 1, 9},
    {12, 5, 1,15,14,13, 4,10, 0, 7, 6, 3, 9, 2, 8,11},
    {13,11, 7,14,12, 1, 3, 9, 5, 0,15, 4, 8, 6, 2,10},
    { 6,15,14, 9,11, 3, 0, 8,12, 2,13, 7, 1, 4,10, 5},
    {10, 2, 8, 4, 7, 6, 1, 5,15,11, 9,14, 3,12,13, 0},
    { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15},
    {14,10, 4, 8, 9,15,13, 6, 1,12, 0, 2,11, 7, 5, 3}
};

typedef struct {
    unsigned long long h[8];
    unsigned long long t; /* low word of the 128-bit byte counter (high = 0) */
    unsigned char buf[BLAKE2B_BLOCKBYTES];
    size_t buflen;
    size_t outlen;
} blake2b_ctx;

static unsigned long long rotr64(unsigned long long w, unsigned c)
{
    return (w >> c) | (w << (64 - c));
}

static unsigned long long load64_le(const unsigned char *p)
{
    return ((unsigned long long)p[0] << 0) |
           ((unsigned long long)p[1] << 8) |
           ((unsigned long long)p[2] << 16) |
           ((unsigned long long)p[3] << 24) |
           ((unsigned long long)p[4] << 32) |
           ((unsigned long long)p[5] << 40) |
           ((unsigned long long)p[6] << 48) |
           ((unsigned long long)p[7] << 56);
}

static void store64_le(unsigned char *p, unsigned long long w)
{
    p[0] = (unsigned char)(w >> 0);
    p[1] = (unsigned char)(w >> 8);
    p[2] = (unsigned char)(w >> 16);
    p[3] = (unsigned char)(w >> 24);
    p[4] = (unsigned char)(w >> 32);
    p[5] = (unsigned char)(w >> 40);
    p[6] = (unsigned char)(w >> 48);
    p[7] = (unsigned char)(w >> 56);
}

#define G(v, a, b, c, d, x, y) do { \
    v[a] = v[a] + v[b] + (x); \
    v[d] = rotr64(v[d] ^ v[a], 32); \
    v[c] = v[c] + v[d]; \
    v[b] = rotr64(v[b] ^ v[c], 24); \
    v[a] = v[a] + v[b] + (y); \
    v[d] = rotr64(v[d] ^ v[a], 16); \
    v[c] = v[c] + v[d]; \
    v[b] = rotr64(v[b] ^ v[c], 63); \
} while (0)

#define ROUND(v, m, s) do { \
    G(v, 0, 4, 8, 12, m[s[0]], m[s[1]]); \
    G(v, 1, 5, 9, 13, m[s[2]], m[s[3]]); \
    G(v, 2, 6, 10, 14, m[s[4]], m[s[5]]); \
    G(v, 3, 7, 11, 15, m[s[6]], m[s[7]]); \
    G(v, 0, 5, 10, 15, m[s[8]], m[s[9]]); \
    G(v, 1, 6, 11, 12, m[s[10]], m[s[11]]); \
    G(v, 2, 7, 8, 13, m[s[12]], m[s[13]]); \
    G(v, 3, 4, 9, 14, m[s[14]], m[s[15]]); \
} while (0)

static void blake2b_compress(blake2b_ctx *ctx, const unsigned char *block, int last)
{
    unsigned long long m[16];
    unsigned long long v[16];
    int i, r;

    for (i = 0; i < 16; ++i)
        m[i] = load64_le(block + (size_t)i * 8);
    for (i = 0; i < 8; ++i)
        v[i] = ctx->h[i];
    for (i = 0; i < 8; ++i)
        v[i + 8] = blake2b_iv[i];
    v[12] ^= ctx->t; /* low counter word; high word is 0 for our input sizes */
    if (last)
        v[14] = ~v[14];
    for (r = 0; r < 12; ++r)
        ROUND(v, m, blake2b_sigma[r]);
    for (i = 0; i < 8; ++i)
        ctx->h[i] ^= v[i] ^ v[i + 8];
}

static int blake2b_init(blake2b_ctx *ctx, size_t outlen, size_t keylen)
{
    int i;

    if (outlen == 0 || outlen > BLAKE2B_OUTBYTES || keylen > 64)
        return -1;
    for (i = 0; i < 8; ++i)
        ctx->h[i] = blake2b_iv[i];
    /* Sequential parameter block: digest_length | key_length << 8 |
     * fanout(1) << 16 | depth(1) << 24; everything else is zero. */
    ctx->h[0] ^= 0x01010000ULL ^ ((unsigned long long)keylen << 8) ^ (unsigned long long)outlen;
    ctx->t = 0;
    ctx->buflen = 0;
    ctx->outlen = outlen;
    return 0;
}

static void blake2b_update(blake2b_ctx *ctx, const unsigned char *in, size_t inlen)
{
    size_t left, fill;

    if (inlen == 0)
        return;
    left = ctx->buflen;
    fill = sizeof(ctx->buf) - left;
    if (left && inlen >= fill) {
        memcpy(ctx->buf + left, in, fill);
        ctx->t += BLAKE2B_BLOCKBYTES;
        blake2b_compress(ctx, ctx->buf, 0);
        ctx->buflen = 0;
        in += fill;
        inlen -= fill;
        left = 0;
    }
    while (inlen > BLAKE2B_BLOCKBYTES) {
        ctx->t += BLAKE2B_BLOCKBYTES;
        blake2b_compress(ctx, in, 0);
        in += BLAKE2B_BLOCKBYTES;
        inlen -= BLAKE2B_BLOCKBYTES;
    }
    memcpy(ctx->buf + ctx->buflen, in, inlen);
    ctx->buflen += inlen;
}

static void blake2b_final(blake2b_ctx *ctx, unsigned char *out)
{
    unsigned char outbuf[BLAKE2B_OUTBYTES];
    int i;

    ctx->t += (unsigned long long)ctx->buflen;
    memset(ctx->buf + ctx->buflen, 0, sizeof(ctx->buf) - ctx->buflen);
    blake2b_compress(ctx, ctx->buf, 1);
    for (i = 0; i < 8; ++i)
        store64_le(outbuf + (size_t)i * 8, ctx->h[i]);
    memcpy(out, outbuf, ctx->outlen);
    memset(outbuf, 0, sizeof(outbuf));
    memset(ctx, 0, sizeof(*ctx));
}

int equihash_blake2b(unsigned char *out, size_t outlen,
                     const unsigned char *in, size_t inlen,
                     const unsigned char *key, size_t keylen)
{
    blake2b_ctx ctx;
    unsigned char keyblock[BLAKE2B_BLOCKBYTES];

    if (!out || (inlen && !in) || (keylen && !key))
        return -1;
    if (blake2b_init(&ctx, outlen, keylen) != 0)
        return -1;
    if (keylen > 0) {
        memset(keyblock, 0, sizeof(keyblock));
        memcpy(keyblock, key, keylen);
        blake2b_update(&ctx, keyblock, sizeof(keyblock));
        memset(keyblock, 0, sizeof(keyblock));
    }
    blake2b_update(&ctx, in, inlen);
    blake2b_final(&ctx, out);
    return 0;
}
