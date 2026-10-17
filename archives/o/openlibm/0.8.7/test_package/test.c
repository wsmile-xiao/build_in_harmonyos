#include <stdio.h>
#include <openlibm.h>

int main(void) {
    double x = 3.14159265358979323846;
    double s = sin(x);
    double c = cos(x);
    double e = exp(1.0);
    double l = log(e);

    if (s > 1e-10 || s < -1e-10) {
        printf("FAIL: sin(pi) = %.15f, expected ~0\n", s);
        return 1;
    }
    if (c < -1.0000001 || c > -0.9999999) {
        printf("FAIL: cos(pi) = %.15f, expected ~-1\n", c);
        return 1;
    }
    if (l < 0.9999999 || l > 1.0000001) {
        printf("FAIL: log(e) = %.15f, expected ~1\n", l);
        return 1;
    }

    printf("openlibm 0.8.7 test: sin(pi)=%.6f cos(pi)=%.6f log(e)=%.6f OK\n", s, c, l);
    return 0;
}
