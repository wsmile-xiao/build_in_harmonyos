#include <liquid/liquid.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    int fail = 0;

    /* deterministic scalar API call */
    float combinations = liquid_nchoosek(5, 2);
    if (combinations != 10.0f) {
        printf("FAIL nchoosek(5,2)=%f (expected 10.0)\n", combinations);
        fail++;
    } else {
        printf("PASS nchoosek(5,2)=%f\n", combinations);
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
        float first = 0.0f;
        /* push 16 values to fill the window, then all taps should be 1.0f */
        for (i = 0; i < 16; i++) {
            windowf_push(w, 1.0f);
        }
        windowf_index(w, 0, &first);
        if (first != 1.0f) {
            printf("FAIL windowf tap[0]==%f (expected 1.0)\n", first);
            fail++;
        } else {
            printf("PASS windowf_create/push/index tap[0]=%f\n", first);
        }
        windowf_destroy(w);
    }

    if (fail == 0) {
        printf("liquid-dsp 1.8.2 test_package: ALL PASS\n");
        return 0;
    }
    printf("liquid-dsp 1.8.2 test_package: %d FAILURES\n", fail);
    return 1;
}
