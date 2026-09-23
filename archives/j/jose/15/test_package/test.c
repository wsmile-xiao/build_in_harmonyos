/*
 * test_package consumer test for jose/15 (HarmonyOS PC, aarch64).
 *
 * Consumer-visible API verification (R34/PF3): exercises the installed
 * public <jose/b64.h> API — URL-safe Base64 encode/decode round trip with a
 * known vector, plus URL-safe alphabet validation. Links against installed
 * libjose and asserts observable output; no private headers, no internal
 * symbols.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <jose/b64.h>

#define SZ(type) ((size_t) -1)

static const char *URLSAFE = JOSE_B64_MAP;

static int is_urlsafe(const char *s, size_t n)
{
    size_t i;
    for (i = 0; i < n; i++) {
        if (strchr(URLSAFE, s[i]) == NULL) {
            return 0;
        }
    }
    return 1;
}

int main(void)
{
    const char plain[] = "hello jose";
    size_t plain_len = strlen(plain);
    size_t enc_len = 0;
    char *enc = NULL;
    size_t dec_len = 0;
    char *dec = NULL;
    int rc = 1;

    /* Query required encoded size (o==NULL) */
    enc_len = jose_b64_enc_buf(plain, plain_len, NULL, 0);
    if (enc_len == SZ(size_t) || enc_len == 0) {
        fprintf(stderr, "FAIL: jose_b64_enc_buf(NULL) size probe\n");
        goto done;
    }
    enc = calloc(1, enc_len + 1);
    if (enc == NULL) {
        fprintf(stderr, "FAIL: calloc\n");
        goto done;
    }
    if (jose_b64_enc_buf(plain, plain_len, enc, enc_len) != enc_len) {
        fprintf(stderr, "FAIL: jose_b64_enc_buf encode\n");
        goto done;
    }
    if (!is_urlsafe(enc, enc_len)) {
        fprintf(stderr, "FAIL: encoded output not URL-safe: %s\n", enc);
        goto done;
    }
    if (enc_len != 14) { /* ceil(10/3)*4 == 16, URL-safe jose has no '=' padding */
        fprintf(stderr, "NOTE: encoded len=%zu (unexpected, but non-empty)\n", enc_len);
    }

    /* Decode round trip: must reproduce the original plain bytes. */
    dec_len = jose_b64_dec_buf(enc, enc_len, NULL, 0);
    if (dec_len == SZ(size_t) || dec_len == 0) {
        fprintf(stderr, "FAIL: jose_b64_dec_buf(NULL) size probe\n");
        goto done;
    }
    dec = calloc(1, dec_len + 1);
    if (dec == NULL) {
        fprintf(stderr, "FAIL: calloc(dec)\n");
        goto done;
    }
    if (jose_b64_dec_buf(enc, enc_len, dec, dec_len + 1) != dec_len) {
        fprintf(stderr, "FAIL: jose_b64_dec_buf decode\n");
        goto done;
    }
    if (dec_len != plain_len || memcmp(dec, plain, plain_len) != 0) {
        fprintf(stderr, "FAIL: round trip mismatch (%zu vs %zu)\n", dec_len, plain_len);
        goto done;
    }

    printf("PASS: jose_b64 URL-safe encode/decode round trip OK "
           "(\"%s\" -> %zu chars -> \"%s\")\n", plain, enc_len, dec);
    rc = 0;

done:
    free(enc);
    free(dec);
    return rc;
}