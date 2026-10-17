/* lame test_package：真实 MP3 编码，非仅版本查询（R34 / R40 多媒体类要求） */
#include <lame/lame.h>

#include <stdio.h>

#define NSAMP  1152          /* 一个 MPEG1 Layer3 granule pair */

int main(void) {
    lame_global_flags *gf = lame_init();
    if (gf == NULL) {
        fprintf(stderr, "lame_init failed\n");
        return 1;
    }

    lame_set_in_samplerate(gf, 44100);
    lame_set_num_channels(gf, 2);
    lame_set_brate(gf, 128);
    lame_set_quality(gf, 5);
    if (lame_init_params(gf) < 0) {
        fprintf(stderr, "lame_init_params failed\n");
        lame_close(gf);
        return 1;
    }

    static short left[NSAMP], right[NSAMP];
    for (int i = 0; i < NSAMP; i++) {
        left[i]  = (short)(((i * 53) % 4096) - 2048);
        right[i] = (short)(2048 - ((i * 31) % 4096));
    }

    unsigned char mp3[16384];
    int n = lame_encode_buffer(gf, left, right, NSAMP, mp3, (int)sizeof(mp3));
    if (n < 0) {
        fprintf(stderr, "lame_encode_buffer failed: %d\n", n);
        lame_close(gf);
        return 1;
    }

    int flushed = lame_encode_flush(gf, mp3, (int)sizeof(mp3));
    lame_close(gf);
    if (flushed < 0 || (n + flushed) <= 0) {
        fprintf(stderr, "lame produced no output: encode=%d flush=%d\n", n, flushed);
        return 1;
    }

    printf("lame: version=%s  encode=%d bytes  flush=%d bytes  OK\n",
           get_lame_version(), n, flushed);
    return 0;
}
