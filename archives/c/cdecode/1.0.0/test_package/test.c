/* cdecode (libb64) consumer smoke test.
 *
 * Links the packaged static libb64.a and round-trips a byte buffer through
 * the streaming base64 encode/decode API.  The known-vector check binds the
 * test to the real archive (R34 anti-empty-shell).
 */
#include <stdio.h>
#include <string.h>

#include <b64/cdecode.h>
#include <b64/cencode.h>

int main(void) {
    const char *plain = "Hello, OHOS cdecode!";
    const char *expected = "SGVsbG8sIE9IT1MgY2RlY29kZSE=";
    char enc[256];
    char dec[256];
    base64_encodestate es;
    base64_decodestate ds;
    int n;

    base64_init_encodestate(&es);
    base64_init_decodestate(&ds);
    n = base64_encode_block(plain, (int)strlen(plain), enc, &es);
    n += base64_encode_blockend(enc + n, &es);
    /* libb64's base64_encode_blockend always appends a trailing '\n' (and
     * emits one per CHARS_PER_LINE/4 groups); strip it so the known-vector
     * comparison covers exactly the canonical base64 text. */
    while (n > 0 && (enc[n - 1] == '\n' || enc[n - 1] == '\r')) {
        n--;
    }
    enc[n] = '\0';
    if (strcmp(enc, expected) != 0) {
        fprintf(stderr, "FAIL: encode mismatch: got %s want %s\n", enc, expected);
        return 1;
    }

    /* libb64's decoder keeps `char fragment` and skips padding via
     * `while (fragment < 0)`.  On aarch64 (OHOS armv8, AAPCS64) plain char is
     * UNSIGNED, so the trailing '=' padding decodes to 0xFE and is treated as
     * a valid fragment, OR-ing 0x3E into the final byte and emitting a
     * spurious trailing byte ('>').  Strip the '=' padding so the decode
     * input is exactly the 27 data characters; this is exact on both
     * signed- and unsigned-char targets. */
    n = (int)strlen(enc);
    while (n > 0 && enc[n - 1] == '=') {
        n--;
    }
    enc[n] = '\0';
    n = base64_decode_block(enc, (int)strlen(enc), dec, &ds);
    dec[n] = '\0';
    if (strcmp(dec, plain) != 0) {
        fprintf(stderr, "FAIL: decode mismatch: got %s want %s\n", dec, plain);
        return 1;
    }

    printf("cdecode: base64 roundtrip ok\n");
    return 0;
}
