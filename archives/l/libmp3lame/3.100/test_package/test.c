#include <stdio.h>
#include <lame/lame.h>

int main(void) {
    lame_global_flags *gfp = lame_init();
    if (!gfp) {
        fprintf(stderr, "lame_init() failed\n");
        return 1;
    }
    /* Set basic parameters */
    lame_set_num_channels(gfp, 1);
    lame_set_in_samplerate(gfp, 44100);
    lame_set_brate(gfp, 128);
    if (lame_init_params(gfp) < 0) {
        fprintf(stderr, "lame_init_params() failed\n");
        lame_close(gfp);
        return 1;
    }
    lame_close(gfp);
    printf("libmp3lame 3.100 test: OK\n");
    return 0;
}
