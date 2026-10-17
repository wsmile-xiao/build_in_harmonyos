/* test_package for libtomcrypt 1.18.2 — exercises the Conan-packaged
 * library through its public API only. All expected values are public
 * standard test vectors (FIPS-180, NIST SP 800-38A, RFC 4648) or
 * round-trips — nothing is invented here.
 *
 *  1. SHA-256 KAT          — FIPS 180-4 / NIST example vectors
 *  2. AES-128 ECB KAT      — NIST SP 800-38A Appendix F.1.1
 *  3. AES-128 ECB round-trip (encrypt then decrypt == plaintext)
 *  4. Base64 KAT           — RFC 4648 test vectors
 *  5. PRNG (yarrow)        — seeded, deterministic output length check
 *  6. Error path           — hash_memory with a too-small out buffer
 *                            must fail with CRYPT_BUFFER_OVERFLOW
 */
#include <stdio.h>
#include <string.h>
#include <tomcrypt.h>

static int failures = 0;

static void check(int cond, const char *what)
{
    printf("%-52s %s\n", what, cond ? "OK" : "FAIL");
    if (!cond) failures++;
}

static void hex_dump(const unsigned char *p, unsigned long n)
{
    unsigned long i;
    for (i = 0; i < n; ++i) printf("%02x", p[i]);
    printf("\n");
}

int main(void)
{
    int err, idx;
    unsigned long outlen;
    unsigned char out[64];

    /* ---- 1. SHA-256 known-answer (FIPS 180-4) ---- */
    if (register_hash(&sha256_desc) == -1) { printf("register_hash failed\n"); return 1; }
    idx = find_hash("sha256");
    check(idx >= 0, "find_hash(\"sha256\")");

    /* "abc" -> ba7816bf 8f01cfea 414140de 5dae2223 b00361a3 96177a9c b410ff61 f20015ad */
    outlen = sizeof(out);
    err = hash_memory(idx, (const unsigned char *)"abc", 3, out, &outlen);
    check(err == CRYPT_OK, "hash_memory(sha256, \"abc\") returns CRYPT_OK");
    {
        const unsigned char want[32] = {
            0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
            0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad
        };
        if (err == CRYPT_OK && outlen == 32) {
            check(memcmp(out, want, 32) == 0, "sha256(\"abc\") == FIPS 180-4 vector");
        } else {
            check(0, "sha256(\"abc\") digest produced");
        }
    }

    /* "" -> e3b0c442 98fc1c14 9afbf4c8 996fb924 27ae41e4 649b934c a495991b 7852b855 */
    outlen = sizeof(out);
    err = hash_memory(idx, (const unsigned char *)"", 0, out, &outlen);
    {
        const unsigned char want[32] = {
            0xe3,0xb0,0xc4,0x42,0x98,0xfc,0x1c,0x14,0x9a,0xfb,0xf4,0xc8,0x99,0x6f,0xb9,0x24,
            0x27,0xae,0x41,0xe4,0x64,0x9b,0x93,0x4c,0xa4,0x95,0x99,0x1b,0x78,0x52,0xb8,0x55
        };
        check(err == CRYPT_OK && outlen == 32 && memcmp(out, want, 32) == 0,
              "sha256(\"\") == FIPS 180-4 empty vector");
    }

    /* ---- 2. AES-128 ECB known-answer (NIST SP 800-38A F.1.1) ---- */
    if (register_cipher(&aes_desc) == -1) { printf("register_cipher failed\n"); return 1; }
    {
        symmetric_key skey;
        unsigned char key[16] = {
            0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f
        };
        unsigned char pt[16]  = {
            0x00,0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff
        };
        unsigned char ct[16], rt[16];
        const unsigned char want[16] = {
            0x69,0xc4,0xe0,0xd8,0x6a,0x7b,0x04,0x30,0xd8,0xcd,0xb7,0x80,0x70,0xb4,0xc5,0x5a
        };

        err = aes_setup(key, 16, 0, &skey);
        check(err == CRYPT_OK, "aes_setup(128-bit key)");
        err = aes_ecb_encrypt(pt, ct, &skey);
        check(err == CRYPT_OK, "aes_ecb_encrypt");
        check(memcmp(ct, want, 16) == 0, "AES-128 ECB == NIST SP 800-38A F.1.1");
        err = aes_ecb_decrypt(ct, rt, &skey);
        check(err == CRYPT_OK, "aes_ecb_decrypt");
        check(memcmp(rt, pt, 16) == 0, "AES-128 round-trip recovers plaintext");
        aes_done(&skey);
    }

    /* ---- 3. Base64 (RFC 4648) ---- */
    {
        unsigned char b64[32];
        unsigned char dec[16];
        const char *in  = "Man";
        const unsigned char *want = (const unsigned char *)"TWFu";
        outlen = sizeof(b64);
        err = base64_encode((const unsigned char *)in, 3, b64, &outlen);
        check(err == CRYPT_OK && outlen == 4 && memcmp(b64, want, 4) == 0,
              "base64_encode(\"Man\") == \"TWFu\" (RFC 4648)");
        outlen = sizeof(dec);
        err = base64_decode(want, 4, dec, &outlen);
        check(err == CRYPT_OK && outlen == 3 && memcmp(dec, in, 3) == 0,
              "base64_decode(\"TWFu\") == \"Man\" (RFC 4648)");
    }

    /* ---- 4. PRNG: yarrow seeded deterministically ---- */
    {
        prng_state prng;
        unsigned char seed[32], a[16], b[16];
        unsigned long i, got;
        for (i = 0; i < sizeof(seed); ++i) seed[i] = (unsigned char)i;

        if (register_prng(&yarrow_desc) == -1) { printf("register_prng failed\n"); return 1; }
        idx = find_prng("yarrow");
        check(idx >= 0, "find_prng(\"yarrow\")");
        err = yarrow_start(&prng);
        check(err == CRYPT_OK, "yarrow_start");
        err = yarrow_add_entropy(seed, sizeof(seed), &prng);
        check(err == CRYPT_OK, "yarrow_add_entropy(32 bytes)");
        err = yarrow_ready(&prng);
        check(err == CRYPT_OK, "yarrow_ready");
        got = yarrow_read(a, sizeof(a), &prng);
        check(got == sizeof(a), "yarrow_read returns requested length");
        got = yarrow_read(b, sizeof(b), &prng);
        check(got == sizeof(b), "yarrow_read(2nd block) returns requested length");
        check(memcmp(a, b, sizeof(a)) != 0, "consecutive yarrow outputs differ");
        yarrow_done(&prng);
    }

    /* ---- 5. Error path: undersized output buffer ---- */
    {
        unsigned char small[8];
        outlen = sizeof(small);   /* too small for a 32-byte digest */
        err = hash_memory(find_hash("sha256"), (const unsigned char *)"abc", 3,
                          small, &outlen);
        check(err == CRYPT_BUFFER_OVERFLOW,
              "hash_memory with 8-byte buffer fails CRYPT_BUFFER_OVERFLOW");
        /* error_to_string must map it to a human-readable message */
        printf("    error_to_string(CRYPT_BUFFER_OVERFLOW) = \"%s\"\n",
               error_to_string(err));
        check(error_to_string(err) != NULL && error_to_string(err)[0] != '\0',
              "error_to_string returns non-empty message");
    }

    printf("\n%s (%d failure%s)\n", failures ? "TEST PACKAGE FAILED" : "TEST PACKAGE PASSED",
           failures, failures == 1 ? "" : "s");
    return failures ? 1 : 0;
}
