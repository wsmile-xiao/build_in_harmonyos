/* gen_fixture.c — emit a tiny, deterministic, silent MPEG-1 Layer III stream.
 *
 * Each frame is 44.1 kHz mono 128 kbps with an all-zero side info block and
 * payload (part2_3_length == 0), which libmad requantizes to a silent PCM
 * frame. The whole file is generated arithmetically from the MPEG audio
 * frame header — no external audio data, fully auditable.
 *
 * Usage: gen_fixture <output.mp3> <num_frames>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* MPEG-1 Layer III, 44100 Hz, mono, 128 kbps, no CRC, no padding:
 *   frame length = floor(144 * 128000 / 44100) = 417 bytes
 */
#define FRAME_LEN 417

static const unsigned char header[4] = { 0xff, 0xfa, 0x90, 0xc0 };

int main(int argc, char **argv)
{
    FILE *f;
    unsigned char frame[FRAME_LEN];
    long frames, i;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <output.mp3> <num_frames>\n", argv[0]);
        return 2;
    }

    frames = atol(argv[2]);
    if (frames < 1) {
        fprintf(stderr, "num_frames must be >= 1\n");
        return 2;
    }

    f = fopen(argv[1], "wb");
    if (!f) {
        perror(argv[1]);
        return 2;
    }

    memcpy(frame, header, 4);
    memset(frame + 4, 0, sizeof(frame) - 4);

    for (i = 0; i < frames; i++) {
        if (fwrite(frame, 1, sizeof(frame), f) != sizeof(frame)) {
            fprintf(stderr, "write failed\n");
            fclose(f);
            return 2;
        }
    }

    if (fclose(f) != 0) {
        perror("fclose");
        return 2;
    }

    printf("%ld frames x %d bytes written to %s\n", frames, FRAME_LEN, argv[1]);
    return 0;
}
