// Consumer test for the installed libad9361 package.
//
// Exercises the hardware-free public API: RF clock chain calculation, filter
// design parameter derivation and FIR tap generation.
#include <stdio.h>

#include "ad9361.h"

static int checks;
static int failures;

static void check(int ok, const char *what)
{
    checks++;
    if (ok) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);

    unsigned long rx[6];
    unsigned long tx[6];

    int ret = ad9361_calculate_rf_clock_chain(5208334UL, 0, rx, tx);
    check(ret == 0, "ad9361_calculate_rf_clock_chain(5208334) returns 0");
    check(rx[0] > 0 && tx[0] == rx[0], "RX/TX share a positive BBPLL rate");
    check(rx[1] >= 25000000UL && rx[1] <= 640000000UL,
          "RX ADC clock is within [25 MHz, 640 MHz]");
    check(rx[1] >= rx[2] && rx[2] >= rx[3] && rx[3] >= rx[4] && rx[4] >= rx[5],
          "RX clock chain is non-increasing");
    check(tx[1] >= tx[2] && tx[2] >= tx[3] && tx[3] >= tx[4] && tx[4] >= tx[5],
          "TX clock chain is non-increasing");
    check(ad9361_calculate_rf_clock_chain(61440001UL, 0, rx, tx) < 0,
          "sample rates above 61.44 MSPS are rejected");

    struct filter_design_parameters fdpTX;
    struct filter_design_parameters fdpRX;
    ret = ad9361_calculate_rf_clock_chain_fdp(&fdpTX, &fdpRX, 1000000UL);
    check(ret == 0, "ad9361_calculate_rf_clock_chain_fdp(1000000) returns 0");
    check(fdpRX.Rdata > 0.0 && fdpTX.Rdata > 0.0,
          "RX/TX filter design data rates are set");
    check(fdpRX.FIR >= 1.0 && fdpRX.FIR <= 4.0, "RX FIR decimation is in [1,4]");

    short taps[128];
    int num_taps = 0;
    int gain = 0;
    ret = ad9361_generate_fir_taps(&fdpRX, taps, &num_taps, &gain);
    check(ret == 0, "ad9361_generate_fir_taps(RX) returns 0");
    check(num_taps > 0 && num_taps <= 128, "RX FIR design produced a sane tap count");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures ? 1 : 0;
}
