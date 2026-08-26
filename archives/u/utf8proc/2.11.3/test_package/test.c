#include <stdio.h>
#include <string.h>
#include "utf8proc.h"

int main(void) {
    /* Verify version string is accessible */
    const char *ver = utf8proc_version();
    printf("utf8proc version: %s\n", ver);
    if (!ver || strlen(ver) == 0) {
        fprintf(stderr, "FAIL: version string is empty\n");
        return 1;
    }

    /* Decode a UTF-8 character (U+00E9 = é, encoded as 0xC3 0xA9) */
    utf8proc_int32_t codepoint = 0;
    utf8proc_ssize_t len = utf8proc_iterate((const utf8proc_uint8_t *)"\xC3\xA9", -1, &codepoint);
    if (len != 2 || codepoint != 0x00E9) {
        fprintf(stderr, "FAIL: expected codepoint 0xE9, got 0x%X (len=%ld)\n", codepoint, (long)len);
        return 1;
    }
    printf("Decoded U+00E9 correctly (len=%ld)\n", (long)len);

    /* Test character width */
    utf8proc_int32_t w = utf8proc_charwidth(0x0041); /* 'A' should be width 1 */
    if (w != 1) {
        fprintf(stderr, "FAIL: expected width 1 for 'A', got %d\n", w);
        return 1;
    }
    printf("Character width of 'A' = %d\n", w);

    printf("All tests passed!\n");
    return 0;
}
