/* Consumer test: use libad9361-iio exactly like a downstream library user.
 * Drives the device-independent public API (no AD9361 hardware required) and
 * asserts the documented clock-chain behaviour. */
#include "ad9361.h"

#include <stdio.h>

static int fail(const char *msg) {
    printf("FAIL: %s\n", msg);
    return 1;
}

int main(void) {
    unsigned long rx[6], tx[6];
    const unsigned long bb = 25000000UL; /* 25 MHz baseband */

    if (ad9361_calculate_rf_clock_chain(bb, 0, rx, tx) != 0)
        return fail("ad9361_calculate_rf_clock_chain(25MHz) returned non-zero");

    /* ADC/DAC rates (index 0) must not fall below the baseband rate. */
    if (rx[0] < bb || tx[0] < bb)
        return fail("chain-head rate below baseband rate");

    /* The clock chain must be monotonically non-increasing towards the
     * baseband side (ADC -> HB3 -> HB2 -> HB1 -> FIR -> BB). */
    for (int i = 0; i < 5; i++) {
        if (rx[i] < rx[i + 1] || tx[i] < tx[i + 1])
            return fail("clock chain not monotonic");
    }

    for (int i = 0; i < 6; i++) {
        printf("rx[%d]=%lu tx[%d]=%lu\n", i, rx[i], i, tx[i]);
    }
    printf("consumer test passed\n");
    return 0;
}
