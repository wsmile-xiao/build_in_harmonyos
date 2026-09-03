#include <ta-lib/ta_libc.h>
#include <stdio.h>
#include <math.h>

int main(void) {
    TA_RetCode ret;
    ret = TA_Initialize();
    if (ret != TA_SUCCESS) { printf("TA_Initialize failed: %d\n", (int)ret); return 1; }
    double inReal[] = {1.0, 2.0, 3.0, 4.0, 5.0};
    double outReal[5];
    int outBegIdx, outNBElement;
    ret = TA_SMA(0, 4, inReal, 3, &outBegIdx, &outNBElement, outReal);
    if (ret != TA_SUCCESS) { printf("TA_SMA failed: %d\n", (int)ret); TA_Shutdown(); return 1; }
    if (outNBElement != 3) { printf("Unexpected count: %d\n", outNBElement); TA_Shutdown(); return 1; }
    if (fabs(outReal[0]-2.0)>1e-10 || fabs(outReal[1]-3.0)>1e-10 || fabs(outReal[2]-4.0)>1e-10) {
        printf("SMA incorrect: %f,%f,%f\n", outReal[0],outReal[1],outReal[2]); TA_Shutdown(); return 1;
    }
    printf("ta-lib test passed: SMA(3)=[%.1f,%.1f,%.1f]\n", outReal[0],outReal[1],outReal[2]);
    TA_Shutdown();
    return 0;
}
