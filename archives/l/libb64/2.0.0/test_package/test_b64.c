/*
 * test_b64.c — libb64 2.0.0 functional test
 *
 * Real functional test using the public libb64 2.0.0 C API (confirmed from
 * include/b64/cencode.h and cdecode.h in the upstream 2.0.0 source):
 *
 *   base64_init_encodestate(base64_encodestate* state_in)
 *   size_t base64_encode_block(const void* plaintext_in, size_t length_in,
 *                              char* code_out, base64_encodestate* state_in)
 *   size_t base64_encode_blockend(char* code_out, base64_encodestate* state_in)
 *   base64_init_decodestate(base64_decodestate* state_in)
 *   size_t base64_decode_block(const char* code_in, size_t length_in,
 *                              void* plaintext_out, base64_decodestate* state_in)
 *   size_t base64_encode_length(size_t plain_len, base64_encodestate* state_in)
 *   size_t base64_decode_maxlength(size_t encode_len)
 *
 * This is NOT an include-only test: it links libb64.a and calls the real
 * encode/decode functions. The expected Base64 value
 * ("Hello, libb64!" -> "SGVsbG8sIGxpYmI2NCE=") was computed independently
 * (printf 'Hello, libb64!' | base64).
 *
 * 2.0.0 vs 1.2.1 behavior (verified by probe on 2026-08-30):
 *   - encode()/decode() return size_t and take (const void*, size_t, ...)
 *     / (const char*, size_t, void*, ...)
 *   - encoder state chars_per_line defaults to 0, so base64_encode_blockend()
 *     emits NO trailing newline (1.2.1 always emitted one).
 *   - padded decode (input still contains '=') returns EXACTLY the plaintext
 *     length with byte-exact match (1.2.1 returned ptlen+1 with a spurious
 *     trailing byte — 2.0.0 fixed this), so no padding-strip workaround is
 *     needed here.
 */
#include <b64/cencode.h>
#include <b64/cdecode.h>

#include <stdio.h>
#include <string.h>

static const char *PLAINTEXT = "Hello, libb64!";
/* Independently computed: printf 'Hello, libb64!' | base64 -> SGVsbG8sIGxpYmI2NCE= */
static const char *EXPECTED_B64 = "SGVsbG8sIGxpYmI2NCE=";

int main(void)
{
    int failures = 0;
    size_t cnt = 0;
    size_t ptlen = strlen(PLAINTEXT); /* "Hello, libb64!" = 14 bytes */

    /* ---- Step 1: Encode PLAINTEXT with the real libb64 API ---- */
    char enc_buf[128];
    char *c = enc_buf;

    base64_encodestate enc_state;
    base64_init_encodestate(&enc_state);

    cnt = base64_encode_block(PLAINTEXT, ptlen, c, &enc_state);
    c += cnt;
    cnt = base64_encode_blockend(c, &enc_state);
    c += cnt;
    *c = '\0'; /* null-terminate the encoded string */

    /* ---- Verification 1: encoded output matches expected Base64 ---- */
    if (strcmp(enc_buf, EXPECTED_B64) != 0) {
        fprintf(stderr, "[fail] encode mismatch: got '%s', expected '%s'\n",
                enc_buf, EXPECTED_B64);
        failures++;
    } else {
        printf("[ok] encode: '%s' -> '%s'\n", PLAINTEXT, enc_buf);
    }

    /* ---- Verification 2: encoded output has no trailing newline (2.0.0) ---- */
    if (strlen(enc_buf) > 0 && enc_buf[strlen(enc_buf) - 1] == '\n') {
        fprintf(stderr, "[fail] 2.0.0 encode unexpectedly has trailing newline\n");
        failures++;
    } else {
        printf("[ok] encode: no trailing newline (chars_per_line=0 default)\n");
    }

    /* ---- Verification 3: one-shot padded decode returns exact plaintext ---- */
    {
        char dec_buf[128] = {0};
        base64_decodestate dec_state;
        base64_init_decodestate(&dec_state);
        cnt = base64_decode_block(EXPECTED_B64, strlen(EXPECTED_B64),
                                  dec_buf, &dec_state);
        if (cnt != ptlen || memcmp(dec_buf, PLAINTEXT, ptlen) != 0) {
            fprintf(stderr,
                    "[fail] padded decode mismatch: cnt=%zu (expected %zu), "
                    "memcmp %s\n",
                    cnt, ptlen,
                    memcmp(dec_buf, PLAINTEXT, ptlen) == 0 ? "match" : "MISMATCH");
            failures++;
        } else {
            printf("[ok] padded decode: cnt=%zu == ptlen=%zu, byte-exact\n",
                   cnt, ptlen);
        }
    }

    /* ---- Verification 4: multi-call streaming decode (realistic usage) ---- */
    {
        char dec_buf[128] = {0};
        base64_decodestate stream_state;
        size_t total = 0;
        const size_t chunk = 7;
        const char *p = EXPECTED_B64;

        base64_init_decodestate(&stream_state);
        while (*p) {
            size_t k = strlen(p);
            if (k > chunk) {
                k = chunk;
            }
            total += base64_decode_block(p, k, dec_buf + total, &stream_state);
            p += k;
        }
        if (total != ptlen || memcmp(dec_buf, PLAINTEXT, ptlen) != 0) {
            fprintf(stderr,
                    "[fail] streaming decode mismatch: total=%zu (expected %zu), "
                    "memcmp %s\n",
                    total, ptlen,
                    memcmp(dec_buf, PLAINTEXT, ptlen) == 0 ? "match" : "MISMATCH");
            failures++;
        } else {
            printf("[ok] streaming decode: total=%zu == ptlen=%zu, byte-exact\n",
                   total, ptlen);
        }
    }

    /* ---- Verification 5: encoded output length is a positive multiple of 4 ---- */
    {
        size_t enc_len = strlen(enc_buf);
        if (enc_len == 0 || (enc_len % 4) != 0) {
            fprintf(stderr, "[fail] encoded length %zu not a positive multiple of 4\n",
                    enc_len);
            failures++;
        } else {
            printf("[ok] encoded length %zu is a multiple of 4\n", enc_len);
        }
    }

    /* ---- Verification 6: helper length functions agree with observed sizes ---- */
    {
        size_t el = base64_encode_length(ptlen, &enc_state);
        size_t dl = base64_decode_maxlength(strlen(EXPECTED_B64));
        if (el != strlen(EXPECTED_B64)) {
            fprintf(stderr, "[fail] base64_encode_length=%zu expected %zu\n",
                    el, strlen(EXPECTED_B64));
            failures++;
        } else {
            printf("[ok] base64_encode_length(%zu)=%zu\n", ptlen, el);
        }
        /* decode_maxlength is an upper bound: >= plaintext length */
        if (dl < ptlen) {
            fprintf(stderr, "[fail] base64_decode_maxlength=%zu < ptlen=%zu\n",
                    dl, ptlen);
            failures++;
        } else {
            printf("[ok] base64_decode_maxlength(%zu)=%zu >= %zu\n",
                   strlen(EXPECTED_B64), dl, ptlen);
        }
    }

    if (failures != 0) {
        fprintf(stderr, "=== %d assertion(s) FAILED ===\n", failures);
        return 1;
    }
    printf("=== All assertions passed ===\n");
    return 0;
}
