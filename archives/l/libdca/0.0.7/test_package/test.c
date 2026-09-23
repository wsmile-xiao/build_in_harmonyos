#include <stdint.h>
#include <stdio.h>

#include <dca.h>

int main(void) {
    dca_state_t *state = dca_init(0);
    if (state == NULL) {
        fprintf(stderr, "dca_init failed\n");
        return 1;
    }

    uint8_t header[14] = {0};
    int flags = 0;
    int sample_rate = 0;
    int bit_rate = 0;
    int frame_length = 0;

    if (dca_syncinfo(state, header, &flags, &sample_rate, &bit_rate,
                     &frame_length) != 0) {
        fprintf(stderr, "all-zero invalid header was accepted\n");
        dca_free(state);
        return 2;
    }

    header[0] = 0x7f;
    header[1] = 0xfe;
    header[2] = 0x80;
    header[3] = 0x00;
    if (dca_syncinfo(state, header, &flags, &sample_rate, &bit_rate,
                     &frame_length) != 0) {
        fprintf(stderr, "truncated DTS-like header was accepted\n");
        dca_free(state);
        return 3;
    }

    dca_free(state);
    puts("libdca API assertions: 3 passed");
    return 0;
}
