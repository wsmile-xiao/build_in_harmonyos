/* Consumer test for vo-amrwbenc: encode AMR-WB frames through the public
 * E_IF_* API (enc_if.h) and assert the RFC 3267 payload size. */
#include <stdio.h>
#include <string.h>
#include <vo-amrwbenc/enc_if.h>

int main(void) {
    /* 20 ms frame at 16 kHz mono 16-bit PCM = 320 samples. */
    short pcm[320];
    unsigned char out[500];
    int i, n1, n2;

    for (i = 0; i < 320; i++) {
        pcm[i] = (short)((i % 80) * 100 - 3950);
    }

    void *state = E_IF_init();
    if (!state) {
        printf("FAIL: E_IF_init returned NULL\n");
        return 1;
    }

    /* mode 8 = 23.85 kbps, dtx off: RFC 3267 frame is 1 ToC byte + 60 data
     * bytes = 61 bytes. Encode two frames and require the exact size. */
    n1 = E_IF_encode(state, 8, pcm, out, 0);
    if (n1 != 61) {
        printf("FAIL: frame 1: expected 61 bytes, got %d\n", n1);
        E_IF_exit(state);
        return 1;
    }

    n2 = E_IF_encode(state, 8, pcm, out, 0);
    if (n2 != 61) {
        printf("FAIL: frame 2: expected 61 bytes, got %d\n", n2);
        E_IF_exit(state);
        return 1;
    }

    E_IF_exit(state);

    if (out[0] == 0 && out[1] == 0 && out[2] == 0) {
        printf("FAIL: encoded payload is all zero\n");
        return 1;
    }

    printf("vo-amrwbenc consumer test passed (two 61-byte AMR-WB frames)\n");
    return 0;
}
