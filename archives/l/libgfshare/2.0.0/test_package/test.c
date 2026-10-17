/*
 * Consumer test for the Conan-packaged libgfshare 2.0.0.
 *
 * Verifies the real public API declared in include/libgfshare.h:
 *   - gfshare_ctx_init_enc / gfshare_ctx_init_dec / gfshare_ctx_free
 *   - gfshare_ctx_enc_setsecret / gfshare_ctx_enc_getshare
 *   - gfshare_ctx_dec_giveshare / gfshare_ctx_dec_newshares / gfshare_ctx_dec_extract
 *   - gfshare_fill_rand / gfshare_bad_idea_but_fill_rand_using_random
 *
 * For each test case the secret is split into N shares with threshold T,
 * then recombined using exactly T shares (two different subsets) and the
 * recovered secret is asserted to be byte-for-byte identical to the input.
 * Four input sizes are exercised: 16 bytes, 256 bytes, 1 byte (minimum
 * non-trivial boundary), and 8 bytes with threshold == sharecount.
 */
#include <libgfshare.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(cond) do { \
    checks_total++; \
    if (!(cond)) { \
        fprintf(stderr, "FAIL [line %d]: %s\n", __LINE__, #cond); \
        checks_failed++; \
    } \
} while (0)

static int checks_total = 0;
static int checks_failed = 0;

/*
 * Split `secret` (size bytes) into `sharecount` shares with `threshold`,
 * then recover using the first `threshold` shares and again using the
 * last `threshold` shares.  Returns 1 if both recoveries are byte-exact,
 * 0 otherwise.  Exercises init_enc/setsecret/getshare/free and
 * init_dec/giveshare/newshares/extract/free.
 */
static int split_recover_ok(const unsigned char *secret, unsigned int size,
                            unsigned int sharecount, unsigned char threshold)
{
    unsigned char sharenrs[8];
    unsigned char active[8];
    unsigned char *shares[8];
    unsigned char *recomb;
    gfshare_ctx *G;
    unsigned int i;

    /* Share numbers must be non-zero (0 marks "not provided" on decode). */
    for (i = 0; i < sharecount; i++)
        sharenrs[i] = (unsigned char)(i + 1);

    for (i = 0; i < sharecount; i++)
        shares[i] = (unsigned char *)malloc(size);
    recomb = (unsigned char *)malloc(size);

    /* ---- encode: split the secret ---- */
    G = gfshare_ctx_init_enc(sharenrs, sharecount, threshold, size);
    if (G == NULL)
        goto cleanup;
    gfshare_ctx_enc_setsecret(G, (unsigned char *)secret);
    for (i = 0; i < sharecount; i++)
        gfshare_ctx_enc_getshare(G, (unsigned char)i, shares[i]);
    gfshare_ctx_free(G);

    /* ---- decode context: load all shares ---- */
    G = gfshare_ctx_init_dec(sharenrs, sharecount, size);
    if (G == NULL)
        goto cleanup;
    for (i = 0; i < sharecount; i++)
        gfshare_ctx_dec_giveshare(G, (unsigned char)i, shares[i]);

    /* ---- recover with the FIRST `threshold` shares ---- */
    for (i = 0; i < sharecount; i++)
        active[i] = (i < threshold) ? sharenrs[i] : 0;
    gfshare_ctx_dec_newshares(G, active);
    memset(recomb, 0xAA, size);
    gfshare_ctx_dec_extract(G, recomb);
    if (memcmp(recomb, secret, size) != 0)
        goto cleanup;

    /* ---- recover with the LAST `threshold` shares ---- */
    for (i = 0; i < sharecount; i++)
        active[i] = (i >= sharecount - threshold) ? sharenrs[i] : 0;
    gfshare_ctx_dec_newshares(G, active);
    memset(recomb, 0xAA, size);
    gfshare_ctx_dec_extract(G, recomb);
    if (memcmp(recomb, secret, size) != 0)
        goto cleanup;

    gfshare_ctx_free(G);
    for (i = 0; i < sharecount; i++)
        free(shares[i]);
    free(recomb);
    return 1;

cleanup:
    if (G)
        gfshare_ctx_free(G);
    for (i = 0; i < sharecount; i++)
        free(shares[i]);
    free(recomb);
    return 0;
}

int main(void)
{
    unsigned int i;
    unsigned char sec16[16];
    unsigned char sec256[256];
    unsigned char sec1[1];
    unsigned char sec8[8];

    /* gfshare_fill_rand MUST be set before any enc_setsecret / ctx_free
     * (free() wipes memory through it).  Use the upstream-provided
     * random()-based filler; seed it for reproducibility. */
    CHECK(gfshare_bad_idea_but_fill_rand_using_random != NULL);
    gfshare_fill_rand = gfshare_bad_idea_but_fill_rand_using_random;
    srandom(0xC0FFEE);

    /* deterministic secrets */
    for (i = 0; i < 16; i++)  sec16[i]  = (unsigned char)(i * 17 + 1);
    for (i = 0; i < 256; i++) sec256[i] = (unsigned char)(i * 31 + 7);
    sec1[0] = 0x5A;
    for (i = 0; i < 8; i++)   sec8[i]   = (unsigned char)(0xF0 ^ i);

    /* Test 1: 16-byte secret, 5 shares, threshold 3 */
    CHECK(split_recover_ok(sec16, 16, 5, 3));

    /* Test 2: 256-byte secret, 4 shares, threshold 2 */
    CHECK(split_recover_ok(sec256, 256, 4, 2));

    /* Test 3: 1-byte secret (minimum boundary), 3 shares, threshold 2 */
    CHECK(split_recover_ok(sec1, 1, 3, 2));

    /* Test 4: threshold == sharecount (no shares dropped), 8-byte secret */
    CHECK(split_recover_ok(sec8, 8, 3, 3));

    /* Test 5: gfshare_ctx_init_enc must reject a zero share number
     * (0 is reserved as "not provided" on the decode side). */
    {
        unsigned char bad_nr[1] = {0};
        gfshare_ctx *bad = gfshare_ctx_init_enc(bad_nr, 1, 1, 4);
        CHECK(bad == NULL);
    }

    printf("consumer test: %d/%d checks passed\n",
           checks_total - checks_failed, checks_total);
    return checks_failed ? 1 : 0;
}
