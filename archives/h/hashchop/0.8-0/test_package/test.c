#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hashchop.h"

/* Deterministic xorshift PRNG so the test never depends on rand(). */
static unsigned int prng_state = 0x12345678u;
static unsigned int prng(void) {
    prng_state ^= prng_state << 13;
    prng_state ^= prng_state >> 17;
    prng_state ^= prng_state << 5;
    return prng_state;
}

static void fill_random(unsigned char *buf, size_t len) {
    for (size_t i = 0; i < len; i++) buf[i] = (unsigned char)(prng() % 256);
}

/* 1. Bits values outside [HASHCHOP_MIN_BITS, HASHCHOP_MAX_BITS] are rejected. */
static void test_reject_invalid_bits(void) {
    assert(hashchop_new(HASHCHOP_MIN_BITS - 1) == NULL);
    assert(hashchop_new(HASHCHOP_MAX_BITS + 1) == NULL);
}

/* 2. sink + finish round-trips the buffered bytes unchanged. */
static void test_sink_finish_roundtrip(void) {
    enum { SZ = 1000 };
    unsigned char in[SZ], out[SZ + 16];
    size_t sz = SZ;
    hashchop *hc = hashchop_new(10);
    assert(hc != NULL);
    fill_random(in, SZ);
    assert(hashchop_sink(hc, in, SZ) == HASHCHOP_OK);
    assert(hashchop_finish(hc, out, &sz) == HASHCHOP_OK);
    assert(sz == SZ);
    assert(memcmp(in, out, SZ) == 0);
    hashchop_free(hc);
}

/* 3. Polling yields a complete chunk stream that covers every input byte. */
static void test_poll_covers_all_bytes(void) {
    enum { SZ = 200000 };
    unsigned char *in = malloc(SZ);
    unsigned char out[1 << 15];
    size_t total = 0;
    hashchop *hc = hashchop_new(10);
    assert(hc != NULL && in != NULL);
    fill_random(in, SZ);
    assert(hashchop_sink(hc, in, SZ) == HASHCHOP_OK);
    for (;;) {
        size_t sz = sizeof(out);
        hashchop_res res = hashchop_poll(hc, out, &sz);
        if (res == HASHCHOP_ERROR_UNDERFLOW) break;
        assert(res == HASHCHOP_OK);
        assert(sz > 0);
        total += sz;
    }
    size_t sz = sizeof(out);
    assert(hashchop_finish(hc, out, &sz) == HASHCHOP_OK);
    total += sz;
    assert(total == SZ);
    hashchop_free(hc);
    free(in);
}

/* 4. The same byte stream sunk in different block sizes produces the
 *    identical chunk-length sequence (content-defined chunking property;
 *    upstream asserts the same property byte-for-byte). */
static void test_chunking_is_block_size_independent(void) {
    enum { SZ = 150000, MAX_CHUNKS = 4096 };
    static unsigned char in[SZ];
    static size_t lengths[2][MAX_CHUNKS];
    fill_random(in, SZ);
    for (int variant = 0; variant < 2; variant++) {
        size_t block = variant == 0 ? 4096 : 1;
        size_t nchunks = 0, off = 0;
        hashchop *hc = hashchop_new(10);
        assert(hc != NULL);
        unsigned char out[1 << 15];
        while (off < SZ) {
            size_t take = block < SZ - off ? block : SZ - off;
            assert(hashchop_sink(hc, in + off, take) == HASHCHOP_OK);
            off += take;
            for (;;) {
                size_t sz = sizeof(out);
                hashchop_res res = hashchop_poll(hc, out, &sz);
                if (res == HASHCHOP_ERROR_UNDERFLOW) break;
                assert(res == HASHCHOP_OK);
                assert(nchunks < MAX_CHUNKS);
                lengths[variant][nchunks++] = sz;
            }
        }
        size_t sz = sizeof(out);
        assert(hashchop_finish(hc, out, &sz) == HASHCHOP_OK);
        assert(nchunks < MAX_CHUNKS);
        lengths[variant][nchunks++] = sz;
        hashchop_free(hc);
        if (variant == 1) {
            assert(memcmp(lengths[0], lengths[1], nchunks * sizeof(size_t)) == 0);
        }
    }
}

/* 5. hashchop_reset() allows reuse of the same handle for a new stream. */
static void test_reset_allows_reuse(void) {
    enum { SZ = 5000 };
    unsigned char in[SZ], out[SZ + 16];
    size_t sz;
    hashchop *hc = hashchop_new(10);
    assert(hc != NULL);
    fill_random(in, SZ);
    for (int round = 0; round < 2; round++) {
        sz = SZ;
        assert(hashchop_sink(hc, in, SZ) == HASHCHOP_OK);
        assert(hashchop_finish(hc, out, &sz) == HASHCHOP_OK);
        assert(sz == SZ && memcmp(in, out, SZ) == 0);
        hashchop_reset(hc);
    }
    hashchop_free(hc);
}

int main(void) {
    test_reject_invalid_bits();
    test_sink_finish_roundtrip();
    test_poll_covers_all_bytes();
    test_chunking_is_block_size_independent();
    test_reset_allows_reuse();
    printf("hashchop consumer tests: 5/5 passed\n");
    return 0;
}
