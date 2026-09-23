/* Consumer test for msgpuck 2.0 on OHOS PC.
 *
 * Exercises the delivered library through its public API: encode a
 * MessagePack array (unsigned int, string, signed int, double) into a
 * caller-owned buffer, validate it with mp_check(), decode it back and
 * require every value to round-trip; then require mp_check() to reject
 * a truncated buffer.  Exit code is the verdict.
 */
#include <msgpuck.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;

static void check(int condition, const char *what) {
    printf("%s %s\n", condition ? "ok  -" : "FAIL-", what);
    if (!condition)
        ++failures;
}

int main(void) {
    char buf[256];
    char *p = buf;
    const char *text = "openharmony";

    /* ── encode an array of four values ─────────────────────────────── */
    p = mp_encode_array(p, 4);
    p = mp_encode_uint(p, 4294967295u);
    p = mp_encode_str(p, text, (uint32_t)strlen(text));
    p = mp_encode_int(p, -12345);
    p = mp_encode_double(p, 3.5);

    const char *end = p;
    const char *pos = buf;

    /* ── validate: a well-formed blob must pass mp_check ────────────── */
    /* mp_check advances the pointer it is given (documented postcondition),
     * so restart from the buffer start for the decoding pass below. */
    check(mp_check(&pos, end) == 0, "mp_check accepts a well-formed blob");
    pos = buf;

    /* ── decode and compare ─────────────────────────────────────────── */
    uint32_t array_len = mp_decode_array(&pos);
    check(array_len == 4, "decoded array header says 4 items");
    check(pos == NULL
              ? 0
              : (mp_decode_uint(&pos) == 4294967295u),
          "unsigned int round-trips");

    uint32_t str_len = 0;
    const char *str = (pos == NULL) ? NULL : mp_decode_str(&pos, &str_len);
    check(str != NULL && str_len == strlen(text)
              && memcmp(str, text, str_len) == 0,
          "string round-trips");

    check(pos == NULL || mp_decode_int(&pos) == -12345,
          "signed int round-trips");
    check(pos == NULL || mp_decode_double(&pos) == 3.5,
          "double round-trips");
    check(pos == end, "decoder consumed exactly the encoded bytes");

    /* ── a truncated blob must be rejected ──────────────────────────── */
    {
        const char *bad = buf;
        check(mp_check(&bad, end - 1) != 0,
              "mp_check rejects a truncated blob");
    }

    if (failures)
        printf("# %d check(s) failed\n", failures);
    else
        puts("# all checks passed");
    return failures ? 1 : 0;
}
