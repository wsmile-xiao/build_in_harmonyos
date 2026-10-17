#include <stdio.h>
#include <libcw.h>

int main(void) {
    /* Test that we can call libcw API functions */
    int rv = cw_generator_new(CW_AUDIO_NULL, NULL);
    if (rv != CW_SUCCESS) {
        printf("FAIL: cw_generator_new returned %d\n", rv);
        return 1;
    }
    printf("OK: libcw cw_generator_new(CW_AUDIO_NULL) returned %d\n", rv);
    cw_generator_delete();
    return 0;
}
