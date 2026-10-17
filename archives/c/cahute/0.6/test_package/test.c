#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <cahute.h>

int main(void) {
    cahute_context *ctx = NULL;
    char utf8_buf[64];
    /* "Hello" encoded in calculator legacy 8-bit (ASCII subset). */
    static const char hello_legacy[] = "Hello";
    static const char hello_utf8[] = "Hello";
    int rc;

    rc = cahute_create_context(&ctx);
    if (rc != CAHUTE_OK) {
        fprintf(stderr, "cahute_create_context failed: %s (0x%04X)\n",
                cahute_get_error_name(rc), rc);
        return 1;
    }
    if (!ctx) {
        fprintf(stderr, "cahute_create_context returned NULL context\n");
        return 1;
    }

    rc = cahute_convert_to_utf8(
        ctx, utf8_buf, sizeof(utf8_buf),
        hello_legacy, sizeof(hello_legacy) - 1,
        CAHUTE_TEXT_ENCODING_LEGACY_8
    );
    if (rc != CAHUTE_OK) {
        fprintf(stderr, "cahute_convert_to_utf8 failed: %s (0x%04X)\n",
                cahute_get_error_name(rc), rc);
        cahute_destroy_context(ctx);
        return 1;
    }

    utf8_buf[sizeof(hello_utf8) - 1] = '\0';
    if (strcmp(utf8_buf, hello_utf8) != 0) {
        fprintf(stderr, "conversion mismatch: got '%s'\n", utf8_buf);
        cahute_destroy_context(ctx);
        return 1;
    }

    cahute_destroy_context(ctx);
    printf("test cahute 0.6: context + text conversion OK\n");
    return 0;
}