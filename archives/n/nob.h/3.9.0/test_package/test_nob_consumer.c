#include <stdio.h>
#include <string.h>

/* Consumer test for nob.h 3.9.0 (header-only C build-recipe library).
 * Uses only the installed public header nob.h (NOB_IMPLEMENTATION),
 * exercises real public APIs with observable results:
 *  - nob_sv_from_cstr / nob_sv_equals   (string-view helpers)
 *  - nob_da_append                      (dynamic array append)
 *  - nob_temp_sprintf                   (temporary string formatting)
 */
#define NOB_IMPLEMENTATION
#include <nob.h>

typedef struct {
    int *items;
    size_t count;
    size_t capacity;
} Numbers;

int main(void) {
    int failures = 0;

    /* 1) String view API: parse and compare */
    Nob_String_View sv = nob_sv_from_cstr("  hello world  ");
    Nob_String_View trimmed = nob_sv_trim(sv);
    if (!nob_sv_eq(trimmed, nob_sv_from_cstr("hello world"))) {
        printf("FAIL: sv_trim expected 'hello world', got '%.*s'\n",
               (int) trimmed.count, trimmed.data);
        failures++;
    } else {
        printf("PASS: sv_trim -> '%.*s'\n", (int) trimmed.count, trimmed.data);
    }

    /* 2) Dynamic array API: append and read back */
    Numbers xs = {0};
    for (int i = 0; i < 5; ++i) {
        nob_da_append(&xs, i * 10);
    }
    if (xs.count != 5 || xs.items[0] != 0 || xs.items[4] != 40) {
        printf("FAIL: da_append expected [0,10,20,30,40], got count=%zu first=%d last=%d\n",
               xs.count, xs.items[0], xs.items[4]);
        failures++;
    } else {
        printf("PASS: da_append -> [0,10,20,30,40] (count=%zu)\n", xs.count);
    }

    /* 3) Temporary string API: format with embedded number */
    const char *msg = nob_temp_sprintf("nob.h v3.9.0 consumer ok (%d)", failures);
    if (strncmp(msg, "nob.h v3.9.0 consumer ok (", 25) != 0) {
        printf("FAIL: temp_sprintf unexpected output: %s\n", msg);
        failures++;
    } else {
        printf("PASS: %s\n", msg);
    }

    printf("consumer result: %s\n", failures == 0 ? "ALL PASS" : "FAILED");
    return failures;
}
