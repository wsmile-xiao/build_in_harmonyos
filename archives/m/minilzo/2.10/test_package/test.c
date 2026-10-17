#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "minilzo.h"

#define IN_LEN  (128 * 1024ul)
#define OUT_LEN (IN_LEN + IN_LEN / 16 + 64 + 3)

int main(void) {
    unsigned char *input = malloc(IN_LEN);
    unsigned char *compressed = malloc(OUT_LEN);
    unsigned char *output = malloc(IN_LEN);
    lzo_align_t *work = malloc(LZO1X_1_MEM_COMPRESS);
    lzo_uint compressed_len = OUT_LEN;
    lzo_uint output_len = IN_LEN;
    int result;

    if (!input || !compressed || !output || !work)
        return 1;
    memset(input, 0x5a, IN_LEN);
    result = lzo_init();
    if (result != LZO_E_OK)
        return 2;
    result = lzo1x_1_compress(input, IN_LEN, compressed, &compressed_len, work);
    if (result != LZO_E_OK)
        return 3;
    result = lzo1x_decompress(compressed, compressed_len, output, &output_len, NULL);
    if (result != LZO_E_OK || output_len != IN_LEN || memcmp(input, output, IN_LEN) != 0)
        return 4;
    printf("MiniLZO round-trip passed: %lu -> %lu bytes\n",
           (unsigned long)IN_LEN, (unsigned long)compressed_len);
    free(input);
    free(compressed);
    free(output);
    free(work);
    return 0;
}
