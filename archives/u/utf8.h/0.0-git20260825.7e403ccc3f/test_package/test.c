/* test.c — test_package for utf8.h (R34 consumer test).
 *
 * utf8.h is a header-only library, so the consumer test compiles against the
 * installed header and asserts real API behaviour on UTF-8 strings:
 *   1. utf8len: byte length of multi-byte text
 *   2. utf8codepoint: decoding successive codepoints (returns next pointer)
 *   3. utf8cat / utf8ncmp: concatenation and comparison
 *   4. utf8valid: well-formed vs truncated UTF-8
 *   5. utf8dup: heap duplication of a UTF-8 string
 *
 * The test fails to compile/link when the package artifacts are removed,
 * satisfying the CI L1e destructive negative test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <utf8.h>

static int failures = 0;

static void check(int ok, const char *what)
{
    if (ok) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

int main(void)
{
    /* "héllo" in UTF-8: 6 bytes, 5 codepoints (é is 2 bytes). */
    const utf8_int8_t *hello = "h\xc3\xa9llo";
    /* U+1F600 (grinning face) = 4 bytes. */
    const utf8_int8_t *emoji = "\xf0\x9f\x98\x80";
    utf8_int8_t buf[64] = {0};  /* utf8cat 内部 strlen(dst)，必须零初始化 */

    /* utf8len 返回码点数（非字节数）："héllo" 6 字节/5 码点 */
    check(utf8len(hello) == 5, "utf8len counts 5 codepoints in \"hÃ©llo\" (6 bytes)");
    check(utf8len(emoji) == 1, "utf8len counts 1 codepoint for U+1F600 (4 bytes)");

    {
        const utf8_int8_t *s = hello;
        utf8_int32_t cp = 0;
        int count = 0;
        while (*s != '\0') {
            s = utf8codepoint(s, &cp);
            count++;
        }
        check(count == 5, "utf8codepoint iterates 5 codepoints in \"h\xc3\xa9llo\"");
    }

    {
        const utf8_int8_t *s = emoji;
        utf8_int32_t cp = 0;
        s = utf8codepoint(s, &cp);
        check(cp == 0x1F600, "utf8codepoint decodes U+1F600");
        check(*s == '\0', "utf8codepoint advances past the 4-byte codepoint");
    }

    {
        utf8cat(buf, (const utf8_int8_t *)"abc");
        utf8cat(buf, (const utf8_int8_t *)"\xc3\xa9");
        check(strcmp((const char *)buf, "abc\xc3\xa9") == 0,
              "utf8cat concatenates byte-exactly");
        check(utf8ncmp(buf, (const utf8_int8_t *)"abc\xc3\xa9", utf8len(buf)) == 0,
              "utf8ncmp matches the concatenated result");
    }

    check(utf8valid((const utf8_int8_t *)"valid \xc3\xa9") == NULL,
          "utf8valid accepts well-formed UTF-8");
    check(utf8valid((const utf8_int8_t *)"bad \xc3") != NULL,
          "utf8valid rejects truncated UTF-8");

    {
        utf8_int8_t *dup = utf8dup(hello);
        check(dup != NULL && strcmp((const char *)dup, (const char *)hello) == 0,
              "utf8dup copies the string");
        free(dup);
    }

    if (failures != 0) {
        printf("%d test(s) failed\n", failures);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
