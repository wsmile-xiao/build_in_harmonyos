#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "zopfli/zopfli.h"

int main(void) {
    ZopfliOptions options;
    ZopfliInitOptions(&options);
    options.numiterations = 1;

    const unsigned char* in_data = (const unsigned char*)"Hello, zopfli! This is a test.";
    size_t in_size = strlen((const char*)in_data);

    unsigned char* out = NULL;
    size_t out_size = 0;

    ZopfliCompress(&options, ZOPFLI_FORMAT_GZIP, in_data, in_size, &out, &out_size);

    if (out_size > 0 && out != NULL) {
        printf("Compression successful: input=%zu bytes, output=%zu bytes\n", in_size, out_size);
        free(out);
        return 0;
    } else {
        printf("Compression failed\n");
        free(out);
        return 1;
    }
}
