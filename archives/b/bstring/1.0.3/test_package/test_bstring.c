/*
 * test_bstring.c — Simple bstring API test.
 *
 * Verifies that:
 *   1. bfromcstr() creates a bstring from a C string
 *   2. bdata() returns the raw C string data
 *   3. blength() returns the correct length
 *   4. bstrcpy() copies a bstring
 *   5. bdestroy() frees memory without error
 */
#include "bstrlib.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;

    /* Test 1: Create bstring from C string */
    bstring bs = bfromcstr("Hello bstring on HarmonyOS!");
    if (bs == NULL) {
        fprintf(stderr, "FAIL: bfromcstr() returned NULL\n");
        return 1;
    }
    printf("PASS: bfromcstr() created bstring\n");

    /* Test 2: Check data content */
    const char *data = (const char *)bdata(bs);
    if (data == NULL || strcmp(data, "Hello bstring on HarmonyOS!") != 0) {
        fprintf(stderr, "FAIL: bdata() = \"%s\", expected \"Hello bstring on HarmonyOS!\"\n", data ? data : "(null)");
        failures++;
    } else {
        printf("PASS: bdata() = \"%s\"\n", data);
    }

    /* Test 3: Check length */
    int len = blength(bs);
    if (len != 27) {
        fprintf(stderr, "FAIL: blength() = %d, expected 27\n", len);
        failures++;
    } else {
        printf("PASS: blength() = %d\n", len);
    }

    /* Test 4: Copy bstring */
    bstring bs2 = bstrcpy(bs);
    if (bs2 == NULL || bstrcmp(bs, bs2) != 0) {
        fprintf(stderr, "FAIL: bstrcpy() copy mismatch\n");
        failures++;
    } else {
        printf("PASS: bstrcpy() copied correctly\n");
    }

    /* Test 5: Destroy both bstrings */
    int ret1 = bdestroy(bs);
    int ret2 = bdestroy(bs2);
    if (ret1 != 0 || ret2 != 0) {
        fprintf(stderr, "FAIL: bdestroy() returned error (bs=%d, bs2=%d)\n", ret1, ret2);
        failures++;
    } else {
        printf("PASS: bdestroy() freed memory\n");
    }

    if (failures > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", failures);
        return 1;
    }

    printf("\nAll bstring tests passed.\n");
    return 0;
}
