#include <ta-lib/ta_libc.h>
#include <stdio.h>
#include <math.h>

int main(void) {
    TA_RetCode ret;

    ret = TA_Initialize();
    if (ret != TA_SUCCESS) {
        printf("TA_Initialize failed: %d\n", (int)ret);
        return 1;
    }

    /* SMA(3) over {1..5} == {2.0, 3.0, 4.0} */
    double inReal[] = {1.0, 2.0, 3.0, 4.0, 5.0};
    double outReal[5];
    int outBegIdx, outNBElement;
    ret = TA_SMA(0, 4, inReal, 3, &outBegIdx, &outNBElement, outReal);
    if (ret != TA_SUCCESS) {
        printf("TA_SMA failed: %d\n", (int)ret);
        TA_Shutdown();
        return 1;
    }
    if (outNBElement != 3) {
        printf("Unexpected count: %d\n", outNBElement);
        TA_Shutdown();
        return 1;
    }
    if (fabs(outReal[0] - 2.0) > 1e-10 ||
        fabs(outReal[1] - 3.0) > 1e-10 ||
        fabs(outReal[2] - 4.0) > 1e-10) {
        printf("SMA incorrect: %f,%f,%f\n",
               outReal[0], outReal[1], outReal[2]);
        TA_Shutdown();
        return 1;
    }

    /* EMA(3) over a NON-linear series {1,2,4,8,16},
     * k = 2/(3+1) = 0.5, seed = SMA(1,2,4) = 7/3.
     * The seed IS the first output (lookbackTotal = period-1 = 2, so
     * the seed loop only accumulates bars [0..2] and never walks):
     *   out[0] = 7/3                        (the seed itself)
     *   out[1] = (8 - 7/3) * 0.5 + 7/3     = 31/6
     *   out[2] = (16 - 31/6) * 0.5 + 31/6  = 127/12
     * Values verified against the built library on device.
     * (values verified against the built library on device) */
    double inEma[] = {1.0, 2.0, 4.0, 8.0, 16.0};
    double outEma[5];
    ret = TA_EMA(0, 4, inEma, 3, &outBegIdx, &outNBElement, outEma);
    if (ret != TA_SUCCESS) {
        printf("TA_EMA failed: %d\n", (int)ret);
        TA_Shutdown();
        return 1;
    }
    if (outNBElement != 3 ||
        fabs(outEma[0] - 7.0 / 3.0) > 1e-10 ||
        fabs(outEma[1] - 31.0 / 6.0) > 1e-10 ||
        fabs(outEma[2] - 127.0 / 12.0) > 1e-10) {
        printf("EMA incorrect: n=%d %f,%f,%f\n", outNBElement,
               outEma[0], outEma[1], outEma[2]);
        TA_Shutdown();
        return 1;
    }

    /* RSI needs >= 2 periods; use a trending series so RSI == 100
     * for a strictly rising input. */
    double rising[15];
    for (int i = 0; i < 15; i++) rising[i] = (double)(i + 1);
    double outRsi[15];
    ret = TA_RSI(0, 14, rising, 14, &outBegIdx, &outNBElement, outRsi);
    if (ret != TA_SUCCESS) {
        printf("TA_RSI failed: %d\n", (int)ret);
        TA_Shutdown();
        return 1;
    }
    if (outNBElement != 1 || fabs(outRsi[0] - 100.0) > 1e-9) {
        printf("RSI incorrect: n=%d val=%f\n", outNBElement, outRsi[0]);
        TA_Shutdown();
        return 1;
    }

    printf("ta-lib test passed: SMA(3)=[%.1f,%.1f,%.1f] EMA(3)=[%.2f,%.3f] RSI(14)=%.1f\n",
           outReal[0], outReal[1], outReal[2],
           outEma[0], outEma[1], outRsi[0]);
    TA_Shutdown();
    return 0;
}
