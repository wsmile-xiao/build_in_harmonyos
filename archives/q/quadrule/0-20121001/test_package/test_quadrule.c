#include <math.h>
#include <stdio.h>
#include <string.h>

#include <quadrule.h>

static int close_to(double actual, double expected, double tolerance)
{
    if (fabs(actual - expected) > tolerance) {
        fprintf(stderr, "expected %.17g, got %.17g\n", expected, actual);
        return 0;
    }
    return 1;
}

static double square(double x)
{
    return x * x;
}

static int test_legendre(void)
{
    double x[4];
    double w[4];
    double weight_sum = 0.0;
    double square_sum = 0.0;
    int i;

    legendre_set(4, x, w);
    for (i = 0; i < 4; ++i) {
        weight_sum += w[i];
        square_sum += w[i] * x[i] * x[i];
    }
    return close_to(weight_sum, 2.0, 1e-13) &&
           close_to(square_sum, 2.0 / 3.0, 1e-13);
}

static int test_hermite(void)
{
    double x[5];
    double w[5];
    double weight_sum = 0.0;
    double square_sum = 0.0;
    int i;

    hermite_set(5, x, w);
    for (i = 0; i < 5; ++i) {
        weight_sum += w[i];
        square_sum += w[i] * x[i] * x[i];
    }
    return close_to(weight_sum, sqrt(acos(-1.0)), 1e-12) &&
           close_to(square_sum, sqrt(acos(-1.0)) / 2.0, 1e-12);
}

static int test_laguerre(void)
{
    double x[5];
    double w[5];
    double weight_sum = 0.0;
    double first_moment = 0.0;
    int i;

    laguerre_set(5, x, w);
    for (i = 0; i < 5; ++i) {
        weight_sum += w[i];
        first_moment += w[i] * x[i];
    }
    return close_to(weight_sum, 1.0, 1e-13) &&
           close_to(first_moment, 1.0, 1e-13);
}

static int test_clenshaw_curtis(void)
{
    double x[7];
    double w[7];
    double weight_sum = 0.0;
    int i;

    clenshaw_curtis_compute(7, x, w);
    for (i = 0; i < 7; ++i) {
        weight_sum += w[i];
    }
    return close_to(weight_sum, 2.0, 1e-13) &&
           close_to(fabs(x[0]), 1.0, 1e-13) &&
           close_to(fabs(x[6]), 1.0, 1e-13) && x[0] > x[6];
}

static int test_rule_adjust(void)
{
    double x[3];
    double w[3];
    double weight_sum = 0.0;
    int i;

    legendre_set(3, x, w);
    rule_adjust(-1.0, 1.0, 2.0, 5.0, 3, x, w);
    for (i = 0; i < 3; ++i) {
        weight_sum += w[i];
    }
    return x[0] >= 2.0 && x[2] <= 5.0 &&
           close_to(weight_sum, 3.0, 1e-13);
}

static int test_helpers(void)
{
    return i4_power(3, 4) == 81 && i4_factorial2(7) == 105 &&
           close_to(r8_gamma(0.5), sqrt(acos(-1.0)), 1e-12) &&
           r8_epsilon() > 0.0 && r8_epsilon() < 1e-12;
}

static int test_summer(void)
{
    double x[5];
    double w[5];

    legendre_set(5, x, w);
    return close_to(summer(square, 5, x, w), 2.0 / 3.0, 1e-13);
}

static int test_ohos_aarch64_abi(void)
{
    const unsigned int marker = 1U;

#ifndef QUADRULE_TEST_HARMONYOS
    fprintf(stderr, "consumer was not configured for HarmonyOS\n");
    return 0;
#endif
#ifndef __aarch64__
    fprintf(stderr, "consumer was not compiled for AArch64\n");
    return 0;
#endif
    return sizeof(void *) == 8U && *(const unsigned char *)&marker == 1U &&
           close_to(legendre_integral(4), 0.4, 1e-15);
}

int main(int argc, char **argv)
{
    int passed = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s SCENARIO\n", argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "legendre") == 0) passed = test_legendre();
    else if (strcmp(argv[1], "hermite") == 0) passed = test_hermite();
    else if (strcmp(argv[1], "laguerre") == 0) passed = test_laguerre();
    else if (strcmp(argv[1], "clenshaw_curtis") == 0) passed = test_clenshaw_curtis();
    else if (strcmp(argv[1], "rule_adjust") == 0) passed = test_rule_adjust();
    else if (strcmp(argv[1], "helpers") == 0) passed = test_helpers();
    else if (strcmp(argv[1], "summer") == 0) passed = test_summer();
    else if (strcmp(argv[1], "ohos_aarch64_abi") == 0) passed = test_ohos_aarch64_abi();
    else {
        fprintf(stderr, "unknown scenario: %s\n", argv[1]);
        return 2;
    }

    if (!passed) return 1;
    printf("PASS: %s\n", argv[1]);
    return 0;
}
