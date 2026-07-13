#include <stdio.h>
#include <stdlib.h>
#include <leptonica/allheaders.h>

int main(void) {
    /* Verify leptonica is linked and version is accessible */
    const char *version = getLeptonicaVersion();
    printf("leptonica version: %s\n", version ? version : "unknown");
    /* Create a small 1x1 8-bit image to exercise the API */
    PIX *pix = pixCreate(1, 1, 8);
    if (pix) {
        pixDestroy(&pix);
        printf("test leptonica 1.87.0: OK\n");
        return 0;
    }
    fprintf(stderr, "test leptonica 1.87.0: FAIL (pixCreate returned NULL)\n");
    return 1;
}
