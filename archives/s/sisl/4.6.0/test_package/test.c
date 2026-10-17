#include <stdio.h>
#include "sisl.h"

int main(void)
{
    double knots[4] = {0.0, 0.0, 1.0, 1.0};
    double coefficients[4] = {0.0, 0.0, 1.0, 1.0};
    double point[2] = {0.0, 0.0};
    int left = 0;
    int status = 0;
    SISLCurve *curve = newCurve(2, 2, knots, coefficients, 1, 2, 1);

    if (curve == NULL) {
        fprintf(stderr, "newCurve returned NULL\n");
        return 1;
    }

    s1221(curve, 0, 0.5, &left, point, &status);
    freeCurve(curve);

    if (status < 0) {
        fprintf(stderr, "s1221 failed with status %d\n", status);
        return 2;
    }
    if (point[0] < 0.499999 || point[0] > 0.500001 ||
        point[1] < 0.499999 || point[1] > 0.500001) {
        fprintf(stderr, "unexpected curve point: (%g, %g)\n", point[0], point[1]);
        return 3;
    }

    puts("SISL linear curve evaluation passed");
    return 0;
}
