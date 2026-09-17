#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "utf8proc.h"

/* Consumer-side API test for utf8proc 2.11.3.2 (upstream 2.11.3) on HarmonyOS PC. */
static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        checks++;                                                          \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL [line %d]: %s\n", __LINE__, #cond);      \
            failures++;                                                    \
        }                                                                  \
    } while (0)

int main(void) {
    /* 1. version API */
    const char *ver = utf8proc_version();
    CHECK(ver != NULL);
    CHECK(strncmp(ver, "2.11", 4) == 0);
    CHECK(UTF8PROC_VERSION_MAJOR == 2);
    CHECK(UTF8PROC_VERSION_MINOR == 11);

    /* 2. NFC normalization: "e" + U+0301 -> U+00E9. */
    const utf8proc_uint8_t *decomposed =
        (const utf8proc_uint8_t *)"e\xCC\x81";
    utf8proc_uint8_t *norm = utf8proc_NFC(decomposed);
    CHECK(norm != NULL);
    if (norm) {
        CHECK(strlen((const char *)norm) == 2);
        CHECK(norm[0] == 0xC3 && norm[1] == 0xA9);
        free(norm);
    }

    /* 3. utf8proc_iterate: decode 'A' (U+0041). */
    utf8proc_int32_t cp = 0;
    utf8proc_ssize_t n = utf8proc_iterate(
        (const utf8proc_uint8_t *)"A", 1, &cp);
    CHECK(n == 1);
    CHECK(cp == 0x41);

    /* 4. Combining acute does not create a new grapheme. */
    utf8proc_int32_t state = 0;
    utf8proc_bool brk = utf8proc_grapheme_break_stateful(0x61, 0x0301, &state);
    CHECK(brk == 0);

    /* 5. Property lookup: 'A' is an uppercase letter. */
    CHECK(utf8proc_get_property(0x41)->category == UTF8PROC_CATEGORY_LU);

    if (failures > 0) {
        fprintf(stderr, "test_utf8proc: %d/%d checks FAILED\n", failures, checks);
        return 1;
    }
    printf("test_utf8proc: %s - all %d checks passed\n", ver, checks);
    return 0;
}
