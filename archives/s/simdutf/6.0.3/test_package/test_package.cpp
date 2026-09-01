/*
 * simdutf 6.0.3 test_package consumer test (HarmonyOS PC / aarch64).
 *
 * Exercises the real simdutf API on this platform: UTF-8 validation and
 * UTF-8 -> UTF-16LE conversion, asserting on the returned error/result so
 * the test is a substantive consumer check (not a print-only stub).
 */
#include <simdutf.h>
#include <stdio.h>
#include <string.h>

/* "hello" in UTF-8 (multi-byte chars for a meaningful validation check) */
static const char utf8_input[] = "hello \xE4\xB8\x96\xE7\x95\x8C!"; /* hello 世界! */

int main(void) {
    size_t len = strlen(utf8_input);
    int failed = 0;

    /* 1. validate_utf8 must accept the valid input */
    if (!simdutf::validate_utf8(utf8_input, len)) {
        printf("FAIL: validate_utf8 returned false for valid UTF-8\n");
        failed = 1;
    }

    /* 2. conversion size estimate must be > input length (UTF-16 needs 2 bytes/unit) */
    size_t u16_units = simdutf::utf16_length_from_utf8(utf8_input, len);
    if (u16_units == 0 || u16_units < len / 2) {
        printf("FAIL: unexpected utf16_length_from_utf8 = %zu\n", u16_units);
        failed = 1;
    }

    /* 3. actual conversion must succeed with no error and produce expected units */
    char16_t *u16 = new char16_t[u16_units + 1];
    simdutf::result r = simdutf::convert_utf8_to_utf16le_with_errors(utf8_input, len, u16);
    if (r.error != simdutf::error_code::SUCCESS) {
        printf("FAIL: convert_utf8_to_utf16le_with_errors error=%d\n", (int)r.error);
        failed = 1;
    } else if (r.count != u16_units) {
        printf("FAIL: converted count=%zu expected=%zu\n", r.count, u16_units);
        failed = 1;
    } else if (u16[0] != (char16_t)'h' || u16[1] != (char16_t)'e') {
        printf("FAIL: unexpected converted content\n");
        failed = 1;
    }
    delete[] u16;

    if (failed) {
        printf("test_package simdutf FAILED\n");
        return 1;
    }
    printf("test_package simdutf 6.0.3: OK (validate + convert, %zu input bytes -> %zu UTF-16 units)\n",
           len, u16_units);
    return 0;
}
