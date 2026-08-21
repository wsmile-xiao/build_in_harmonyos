#include <stdio.h>
#include <erfa.h>
#include <erfaextra.h>

int main(void) {
    /* Test eraEpb2jd: convert Bessel epoch to Julian date */
    double djm0, djm1;
    eraEpb2jd(2024.0, &djm0, &djm1);
    if (djm0 < 2400000.0 || djm1 < 0.0) {
        fprintf(stderr, "eraEpb2jd returned invalid Julian date: %f, %f\n", djm0, djm1);
        return 1;
    }

    /* Test eraDat: get TAI-UTC difference for 2024-01-01 */
    double dat;
    int status = eraDat(2024, 1, 1, 0.0, &dat);
    if (status != 0) {
        fprintf(stderr, "eraDat failed with status %d\n", status);
        return 1;
    }
    if (dat < 0.0) {
        fprintf(stderr, "eraDat returned negative TAI-UTC: %f\n", dat);
        return 1;
    }

    /* Test eraEra00: Earth rotation angle */
    double era = eraEra00(2451545.0, 0.0);
    if (era < 0.0 || era > 6.283185307179586) {
        fprintf(stderr, "eraEra00 returned out-of-range value: %f\n", era);
        return 1;
    }

    printf("erfa version: %s\n", eraVersion());
    printf("TAI-UTC: %f seconds\n", dat);
    printf("Earth rotation angle: %f rad\n", era);
    printf("All erfa tests passed!\n");
    return 0;
}
