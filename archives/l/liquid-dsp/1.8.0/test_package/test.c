#include <liquid/liquid.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    int fail = 0;

    /* liquid_nextpow2: returns ceil(log2(n)); nextpow2(100)=7 (2^7=128) */
    unsigned int n = liquid_nextpow2(100);
    if (n != 7) {
        printf("FAIL nextpow2(100)=%u (expected 7)\n", n);
        fail++;
    } else {
        printf("PASS nextpow2(100)=%u (2^7=128)\n", n);
    }

    /* version string (extern const char liquid_version[]) */
    const char *ver = liquid_version;
    if (ver == NULL || strlen(ver) == 0) {
        printf("FAIL liquid_version empty\n");
        fail++;
    } else {
        printf("PASS liquid_version=%s\n", ver);
    }

    /* window object (float precision sliding window, src/buffer) */
    windowf w = windowf_create(16);
    if (w == NULL) {
        printf("FAIL windowf_create\n");
        fail++;
    } else {
        int i;
        float *r = NULL;
        /* push 16 values to fill the window, then all taps should be 1.0f */
        for (i = 0; i < 16; i++) {
            windowf_push(w, 1.0f);
        }
        windowf_read(w, &r);
        if (r == NULL || r[0] != 1.0f) {
            printf("FAIL windowf tap[0]==%f (expected 1.0)\n", r ? r[0] : 0.0f);
            fail++;
        } else {
            printf("PASS windowf_create/push/read tap[0]=%f\n", r[0]);
        }
        windowf_destroy(w);
    }

    if (fail == 0) {
        printf("liquid-dsp 1.8.0 test_package: ALL PASS\n");
        return 0;
    }
    printf("liquid-dsp 1.8.0 test_package: %d FAILURES\n", fail);
    return 1;
}
