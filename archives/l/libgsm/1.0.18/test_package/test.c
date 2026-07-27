#include <stdio.h>
#include <stdlib.h>
#include <gsm.h>

int main(void) {
    /* Create GSM encoder/decoder handle */
    gsm handle = gsm_create();
    if (handle == NULL) {
        fprintf(stderr, "gsm_create() failed\n");
        return 1;
    }

    /* Encode a frame: 160 signed 16-bit samples → 33 GSM bytes */
    gsm_signal input[160] = {0};
    gsm_byte output[33];

    gsm_encode(handle, input, output);

    /* Decode back: 33 GSM bytes → 160 signed 16-bit samples */
    gsm_signal decoded[160];
    int rc = gsm_decode(handle, output, decoded);
    if (rc < 0) {
        fprintf(stderr, "gsm_decode() failed\n");
        gsm_destroy(handle);
        return 1;
    }

    gsm_destroy(handle);

    printf("libgsm encode/decode test: OK\n");
    return 0;
}
