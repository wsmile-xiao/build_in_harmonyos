#include <stdio.h>
#include <string.h>
#include <mad.h>

/* Minimal test: verify libmad API is callable */
int main(void) {
    /* Test 1: Check mad version string is accessible */
    const char *version = mad_version;
    if (!version || strlen(version) == 0) {
        fprintf(stderr, "FAIL: mad_version is empty\n");
        return 1;
    }
    printf("libmad version: %s\n", version);

    /* Test 2: Initialize a decoder (API smoke test) */
    struct mad_decoder decoder;
    mad_decoder_init(&decoder, NULL, NULL, NULL, NULL, NULL, NULL, NULL);
    mad_decoder_finish(&decoder);
    printf("mad_decoder_init/finish: OK\n");

    /* Test 3: Initialize header parsing */
    struct mad_header header;
    mad_header_init(&header);
    mad_header_finish(&header);
    printf("mad_header_init/finish: OK\n");

    printf("test libmad 0.15.1b: PASS\n");
    return 0;
}
