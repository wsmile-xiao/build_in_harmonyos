#include <stdio.h>
#include <string.h>
#include "libjodycode.h"

int main(void) {
    /* Verify version info is accessible */
    printf("libjodycode version: %s\n", jc_version);
    printf("API version: %d\n", jc_api_version);

    /* Test jc_streq — string equality check (returns 0=equal, 1=not equal) */
    int r1 = jc_streq("hello", "hello");
    int r2 = jc_streq("hello", "world");
    printf("jc_streq(\"hello\",\"hello\") = %d (expect 0)\n", r1);
    printf("jc_streq(\"hello\",\"world\") = %d (expect 1)\n", r2);

    /* Test jc_strneq — bounded string equality */
    int r3 = jc_strneq("hello world", "hello there", 5);
    printf("jc_strneq(\"hello world\",\"hello there\",5) = %d (expect 0)\n", r3);

    /* Test jc_numeric_strcmp — numeric-aware string comparison */
    int r4 = jc_numeric_strcmp("9", "10", 0);
    printf("jc_numeric_strcmp(\"9\",\"10\") = %d (expect <0)\n", r4);

    /* Verify jc_version is non-null and non-empty */
    if (jc_version == NULL || jc_version[0] == '\0') {
        fprintf(stderr, "FAIL: jc_version is empty\n");
        return 1;
    }
    if (r1 != 0 || r2 != 1 || r3 != 0 || r4 >= 0) {
        fprintf(stderr, "FAIL: API tests did not return expected values\n");
        return 1;
    }

    printf("All libjodycode tests passed!\n");
    return 0;
}
