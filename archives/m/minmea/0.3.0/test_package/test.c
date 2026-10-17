/*
 * Consumer test for minmea 0.3.0 (test_package).
 *
 * Exercises the packaged header + library from an external translation unit:
 * checksum validation, sentence classification, RMC parsing and the
 * fixed-point / coordinate helpers.  14 checks must all pass.
 */

#include <stdio.h>

#include "minmea.h"

static int checks = 0;

static int check(int condition, const char *what)
{
    if (!condition) {
        fprintf(stderr, "minmea test_package: FAIL at check #%d: %s\n",
                checks + 1, what);
        return 0;
    }
    checks++;
    return 1;
}

#define CHECK(cond, what) do { if (!check((cond), (what))) return 1; } while (0)

static int near(double a, double b, double eps)
{
    double diff = a - b;
    if (diff < 0) {
        diff = -diff;
    }
    return diff < eps;
}

int main(void)
{
    const char *rmc = "$GPRMC,123205.00,A,5106.94085,N,01701.51689,E,0.016,,280214,,,A*7B";
    const char *gga = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47";
    const char *gll = "$GPGLL,5106.94086,N,01701.51680,E,123204.00,A,A*63";
    struct minmea_sentence_rmc frame;

    /* checksum validation */
    CHECK(minmea_check(rmc) == true, "valid RMC checksum accepted");
    CHECK(minmea_check("$GPRMC,,V,,,,,,,,,,N*532") == false, "wrong checksum rejected");
    CHECK(minmea_check("GPRMC,081836.75,A,3751.65,S,14507.36,E,000.0,360.0,130998,011.3,E") == false,
          "sentence must start with '$'");

    /* sentence classification */
    CHECK(minmea_sentence_id(rmc) == MINMEA_SENTENCE_RMC, "RMC classified");
    CHECK(minmea_sentence_id(gga) == MINMEA_SENTENCE_GGA, "GGA classified");
    CHECK(minmea_sentence_id(gll) == MINMEA_UNKNOWN, "unsupported sentence type is UNKNOWN");

    /* RMC parsing */
    CHECK(minmea_parse_rmc(&frame, rmc) == true, "RMC parse succeeds");
    CHECK(frame.valid == true, "RMC status A means valid");
    CHECK(frame.time.hours == 12 && frame.time.minutes == 32 && frame.time.seconds == 5,
          "RMC time is 12:32:05");
    CHECK(frame.date.day == 28 && frame.date.month == 2 && frame.date.year == 14,
          "RMC date is 28/02/14");
    CHECK(frame.latitude.value == 510694085 && frame.latitude.scale == 100000,
          "RMC latitude kept as fixed point");

    /* coordinate and float helpers */
    CHECK(near(minmea_tocoord(&frame.latitude), 51.1156808333, 1e-6),
          "latitude converted to DD.DDDDD");
    CHECK(near(minmea_tocoord(&frame.longitude), 17.0252815, 1e-6),
          "longitude converted to DD.DDDDD");
    CHECK(near(minmea_tofloat(&frame.speed), 0.016, 1e-9), "speed converted to float");

    printf("minmea test_package: %d/%d checks passed\n", checks, 14);
    return 0;
}
