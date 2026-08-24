/*
 * test_b64.c — libb64 1.2.1 functional test
 *
 * Real functional test using the public libb64 C API (confirmed from
 * include/b64/cencode.h and cdecode.h in the upstream 1.2.1 source):
 *
 *   base64_init_encodestate(base64_encodestate* state_in)
 *   int base64_encode_block(const char* plaintext_in, int length_in,
 *                           char* code_out, base64_encodestate* state_in)
 *   int base64_encode_blockend(char* code_out, base64_encodestate* state_in)
 *   base64_init_decodestate(base64_decodestate* state_in)
 *   int base64_decode_block(const char* code_in, const int length_in,
 *                           char* plaintext_out, base64_decodestate* state_in)
 *
 * This is NOT an include-only test: it links libb64.a and calls the real
 * encode/decode functions. The expected Base64 value
 * ("Hello, libb64!" -> "SGVsbG8sIGxpYmI2NCE=") was computed independently
 * (printf 'Hello, libb64!' | base64).
 *
 * ====================================================================
 * Decode test design — two explicitly separated paths
 * ====================================================================
 *
 * The libb64 1.2.1 streaming decoder does NOT treat '=' as a padding
 * terminator. In src/cdecode.c the '=' character enters the "skip"
 * branch (handled like whitespace): it is ignored as a data carrier but
 * does NOT reset the 4-char group accumulator. As a result, decoding a
 * padded Base64 string directly yields a byte count that differs from
 * the real plaintext length — a spurious trailing byte carrying the
 * leftover partial bits.
 *
 * To avoid masking this upstream behavior behind a "strict decode PASS"
 * label, the decode side is split into two distinct paths:
 *
 *   Path A — padded original input behavior verification
 *     Decodes "SGVsbG8sIGxpYmI2NCE=" directly with the original public
 *     decode API, WITHOUT stripping '='. Records the true return length
 *     and bytes, and asserts that the result is NON-strict (cnt != ptlen)
 *     to confirm the test genuinely exercises the padding/skip path. This
 *     is NOT a correctness assertion — it documents a known upstream
 *     limitation. Upstream source is NOT modified to "fix" this.
 *
 *   Path B — strict round-trip using padding-stripped input
 *     Copies our own encode output into a work buffer, strips trailing
 *     '=' padding, then calls the original base64_decode_block. Enforces
 *     STRICT length equality (decoded_len == original_len) AND a
 *     byte-exact memcmp match. This is the length-correct caller
 *     workaround; it does NOT alter upstream decoder semantics.
 */
#include <b64/cencode.h>
#include <b64/cdecode.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *PLAINTEXT = "Hello, libb64!";
/* Independently computed: printf 'Hello, libb64!' | base64 -> SGVsbG8sIGxpYmI2NCE= */
static const char *EXPECTED_B64 = "SGVsbG8sIGxpYmI2NCE=";

/* Strip trailing '=' padding from a Base64 string in-place; return new length.
 * '=' carries no data bits and the libb64 1.2.1 streaming decoder ignores it
 * (treats it as whitespace via the skip branch), emitting a spurious trailing
 * byte. Stripping it before decode yields a strict, length-correct result.
 * This does NOT alter upstream decoder semantics. */
static int strip_b64_padding(char *s, int len)
{
    while (len > 0 && s[len - 1] == '=') {
        s[--len] = '\0';
    }
    return len;
}

int main(void)
{
    int failures = 0;
    int ret = 0;
    int cnt = 0;
    int ptlen = (int)strlen(PLAINTEXT); /* "Hello, libb64!" = 14 bytes */

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

    /* libb64 appends a trailing newline after blockend; trim it for comparison. */
    if (c > enc_buf && *(c - 1) == '\n') {
        *(c - 1) = '\0';
    }

    /* ---- Verification 1: encoded output matches expected Base64 ---- */
    if (strcmp(enc_buf, EXPECTED_B64) != 0) {
        fprintf(stderr, "[fail] encode mismatch: got '%s', expected '%s'\n",
                enc_buf, EXPECTED_B64);
        failures++;
    } else {
        printf("[ok] encode: '%s' -> '%s'\n", PLAINTEXT, enc_buf);
    }

    /* ==================================================================
     * Path A — padded original input: upstream behavior verification
     * ==================================================================
     * Decode EXPECTED_B64 ("SGVsbG8sIGxpYmI2NCE=") directly WITHOUT
     * stripping '='. Per libb64 1.2.1 src/cdecode.c, '=' enters the skip
     * branch, so the decoder does NOT terminate on padding and returns a
     * count that differs from the real plaintext length (spurious trailing
     * byte). This records the TRUE upstream behavior — it is NOT a strict
     * decode pass. Upstream source is NOT modified. */
    {
        char dec_buf[128] = {0};
        int padded_len = (int)strlen(EXPECTED_B64);

        base64_decodestate dec_state;
        base64_init_decodestate(&dec_state);
        cnt = base64_decode_block(EXPECTED_B64, padded_len, dec_buf, &dec_state);

        printf("[known upstream behavior] padded decode returned %d bytes for %d-byte plaintext\n",
               cnt, ptlen);
        printf("[known upstream behavior] decoded bytes (hex):");
        for (int i = 0; i < cnt && i < ptlen + 8; i++) {
            printf(" %02x", (unsigned char)dec_buf[i]);
        }
        printf("\n");

        /* Verify this is the known 1.2.1 padding behavior: the padded input
         * does NOT decode to the exact plaintext length. If this assertion
         * fails, the upstream source behavior changed (or our understanding
         * is wrong) — investigate before adjusting the test. */
        if (cnt == ptlen) {
            fprintf(stderr,
                    "[fail] expected known non-strict padded behavior (cnt != %d), "
                    "got cnt=%d — upstream may have changed\n",
                    ptlen, cnt);
            failures++;
        } else {
            printf("[ok] padded path covered: cnt=%d != ptlen=%d "
                   "(known non-strict upstream behavior, '=' skip branch)\n",
                   cnt, ptlen);
        }
    }

    /* ==================================================================
     * Path B — strict round-trip using padding-stripped input
     * ==================================================================
     * Copy our own encoded output into a work buffer, strip trailing '='
     * padding, then call the original base64_decode_block. Assert STRICT
     * length equality (decoded_len == original_len) AND byte-exact memcmp.
     * This is the length-correct workaround — upstream semantics unchanged. */
    {
        char dec_buf[128] = {0};
        char enc_in[128];
        int enc_len;

        strcpy(enc_in, enc_buf); /* copy our own encoded output */
        enc_len = strip_b64_padding(enc_in, (int)strlen(enc_in));

        base64_decodestate rt_state;
        base64_init_decodestate(&rt_state);
        cnt = base64_decode_block(enc_in, enc_len, dec_buf, &rt_state);

        if (cnt != ptlen || memcmp(dec_buf, PLAINTEXT, (size_t)ptlen) != 0) {
            fprintf(stderr,
                    "[fail] strict round-trip mismatch: cnt=%d (expected %d), "
                    "memcmp %s\n",
                    cnt, ptlen,
                    memcmp(dec_buf, PLAINTEXT, (size_t)ptlen) == 0 ? "match" : "MISMATCH");
            failures++;
        } else {
            printf("[ok] strict round-trip using padding-stripped input: "
                   "cnt=%d == ptlen=%d, byte-exact\n",
                   cnt, ptlen);
        }
    }

    /* ---- Verification 4: encoded output length is a positive multiple of 4 ---- */
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

    if (failures != 0) {
        fprintf(stderr, "=== %d assertion(s) FAILED ===\n", failures);
        ret = 1;
    } else {
        printf("=== All assertions passed ===\n");
    }
    return ret;
}
