#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "varintencode.h"
#include "varintdecode.h"

/* Consumer smoke test: encode a set of integers with the public vbyte_encode
 * API, then decode with the public masked_vbyte_decode API and verify the
 * round trip. Uses only the installed public headers and the linked library. */
int main(void) {
    const uint32_t datain[] = {0, 1, 127, 128, 16383, 16384, 999999, 387420489,
                               42, 7, 65535, 1u << 24};
    const size_t N = sizeof(datain) / sizeof(datain[0]);
    uint8_t *compressed = malloc(2 * N * sizeof(uint32_t));
    uint32_t *recov = malloc(N * sizeof(uint32_t));
    if (!compressed || !recov) {
        printf("maskedvbyte consumer test: OOM\n");
        return -1;
    }

    size_t compsize = vbyte_encode(datain, N, compressed);
    size_t usedbytes = masked_vbyte_decode(compressed, recov, N);
    if (compsize != usedbytes) {
        printf("maskedvbyte consumer test FAIL: compsize=%zu used=%zu\n",
               compsize, usedbytes);
        return -1;
    }
    for (size_t k = 0; k < N; ++k) {
        if (recov[k] != datain[k]) {
            printf("maskedvbyte consumer test FAIL at %zu: %u != %u\n", k,
                   recov[k], datain[k]);
            return -1;
        }
    }

    /* Delta path: sorted input with small gaps. */
    uint32_t delta_in[8];
    uint32_t delta_rec[8];
    for (int i = 0; i < 8; ++i)
        delta_in[i] = (uint32_t)(i * 3);
    size_t dsize = vbyte_encode_delta(delta_in, 8, compressed, 0);
    size_t ddec = masked_vbyte_decode_delta(compressed, delta_rec, 8, 0);
    if (dsize != ddec || memcmp(delta_in, delta_rec, sizeof(delta_in)) != 0) {
        printf("maskedvbyte consumer test FAIL: delta round trip\n");
        return -1;
    }

    free(compressed);
    free(recov);
    printf("maskedvbyte 0.1.0 consumer test: PASS (%zu values round-tripped)\n",
           N);
    return 0;
}