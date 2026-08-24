#include <stdio.h>
#include <stdlib.h>
#include <speex/speex.h>

int main(void) {
    /* Test speex encoder initialization */
    const SpeexMode *mode = speex_lib_get_mode(SPEEX_MODEID_NB);
    if (mode == NULL) {
        printf("ERROR: speex_lib_get_mode returned NULL\n");
        return 1;
    }
    
    /* Test bits initialization */
    SpeexBits bits;
    speex_bits_init(&bits);
    
    /* Test encoder init */
    void *state = speex_encoder_init(mode);
    if (state == NULL) {
        printf("ERROR: speex_encoder_init returned NULL\n");
        speex_bits_destroy(&bits);
        return 1;
    }
    
    /* Get frame size */
    spx_int32_t frame_size;
    speex_encoder_ctl(state, SPEEX_GET_FRAME_SIZE, &frame_size);
    
    printf("speex test OK: frame_size=%d\n", frame_size);
    
    /* Cleanup */
    speex_bits_destroy(&bits);
    speex_encoder_destroy(state);
    
    return 0;
}
