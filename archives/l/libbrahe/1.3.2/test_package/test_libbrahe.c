/*
 * libbrahe 1.3.2 installed-package consumer test.
 *
 * Built and linked against the *packaged* headers and library (not the source
 * tree) by test_package/CMakeLists.txt, so it proves that the package ships a
 * usable public API. Every expectation is an exact value from the upstream
 * contracts in src/mathtools.h plus the values the upstream console tests
 * print; the FFT window reuses upstream's own published bounds.
 */
#include <mathtools.h>
#include <prng.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks = 0;
static int failures = 0;

static void check(const char *what, int ok)
{
    ++checks;
    if (!ok)
    {
        ++failures;
        printf("FAIL: %s\n", what);
    }
}

static void check_close(const char *what, double got, double want, double eps)
{
    char label[160];
    snprintf(label, sizeof label, "%s (got %.10f want %.10f)", what, got, want);
    ++checks;
    if (!(fabs(got - want) <= eps))
    {
        ++failures;
        printf("FAIL: %s\n", label);
    }
}

int main(void)
{
    /* --- rounding: round-half-to-even, per the brahe_round_nearest contract --- */
    check_close("round_nearest(pi)", brahe_round_nearest(3.14159265358979), 3.0, 0.0);
    check_close("round_nearest(-pi)", brahe_round_nearest(-3.14159265358979), -3.0, 0.0);
    check_close("round_nearest(6.5) half-to-even", brahe_round_nearest(6.5), 6.0, 0.0);
    check_close("round_nearest(-6.5) half-to-even", brahe_round_nearest(-6.5), -6.0, 0.0);
    check_close("round_nearest(17.5) half-to-even", brahe_round_nearest(17.5), 18.0, 0.0);

    /* --- significant digits: sign preserving (upstream expectation typo case) --- */
    check_close("sigdig(pi,5)", brahe_sigdig(3.14159265358979, 5), 3.1416, 0.0);
    check_close("sigdig(-pi,8) keeps the sign", brahe_sigdig(-3.14159265358979, 8),
                -3.14159270, 1e-8);
    check_close("sigdig(c,4)", brahe_sigdig(299792.458, 4), 299800.0, 0.0);
    check_close("sigdig(x,0) returns x unchanged", brahe_sigdig(1234.5, 0), 1234.5, 0.0);

    /* --- gcf / lcm --- */
    check("gcf(644,805) == 161", brahe_gcf(644, 805) == 161);
    check("gcf(0,0) == 0", brahe_gcf(0, 0) == 0);
    check("lcm(36,125) == 4500", brahe_lcm(36, 125) == 4500);
    check("lcm(0,0) == 0", brahe_lcm(0, 0) == 0);

    /* --- hyperbolic inverses (upstream brahe_test_trig identities) --- */
    check_close("atanh(tanh(4/3))", brahe_atanh(tanh(1.3333333333333333)),
                1.3333333333333333, 1e-8);
    check_close("asinh(sinh(1))", brahe_asinh(sinh(1.0)), 1.0, 1e-8);
    check_close("acosh(cosh(1.5))", brahe_acosh(cosh(1.5)), 1.5, 1e-8);

    /* --- log tools --- */
    check_close("log2base(1024,2)", brahe_log2base(1024.0, 2.0), 10.0, 1e-9);
    check("log2base(0.5,2) is NaN (x < 1 guard)", isnan(brahe_log2base(0.5, 2.0)));
    check("sizepow2(1000) == 1024", brahe_sizepow2(1000) == 1024);
    check("sizepow2(0) == 0", brahe_sizepow2(0) == 0);

    /* --- statistics over {1,2,3,4}: sample variance uses n-1 --- */
    double data[4] = { 1.0, 2.0, 3.0, 4.0 };
    brahe_statistics stats = brahe_get_statistics(data, 4);
    check_close("statistics.min", stats.min, 1.0, 0.0);
    check_close("statistics.max", stats.max, 4.0, 0.0);
    check_close("statistics.mean", stats.mean, 2.5, 0.0);
    check_close("statistics.variance (n-1)", stats.variance, 5.0 / 3.0, 1e-12);
    check_close("statistics.sigma", stats.sigma, sqrt(5.0 / 3.0), 1e-12);

    /* --- PRNG: determinism, bounds and interval contract --- */
    brahe_prng_state_t a, b, c;
    check("prng_init(MARSENNE_TWISTER, 12345)",
          brahe_prng_init(&a, BRAHE_PRNG_MARSENNE_TWISTER, 12345) == true);
    check("prng_init(MARSENNE_TWISTER, 12345) again",
          brahe_prng_init(&b, BRAHE_PRNG_MARSENNE_TWISTER, 12345) == true);
    check("prng_init(MARSENNE_TWISTER, 987654)",
          brahe_prng_init(&c, BRAHE_PRNG_MARSENNE_TWISTER, 987654) == true);

    int same = 1;
    int differs = 0;
    for (int i = 0; i < 8; ++i)
    {
        uint32_t va = brahe_prng_next(&a);
        uint32_t vb = brahe_prng_next(&b);
        uint32_t vc = brahe_prng_next(&c);
        if (va != vb)
            same = 0;
        if (va != vc)
            differs = 1;
    }
    check("equal seeds produce identical streams", same);
    check("different seeds produce different streams", differs);

    int in_range = 1;
    for (int i = 0; i < 1000; ++i)
    {
        uint32_t v = brahe_prng_range(&a, 10, 20);
        if (v < 10 || v > 20)
            in_range = 0;
    }
    check("prng_range(10,20) stays inside the interval", in_range);

    int real1_ok = 1;
    for (int i = 0; i < 1000; ++i)
    {
        double r = brahe_prng_real1(&b);
        if (!(r >= 0.0 && r <= 1.0))
            real1_ok = 0;
    }
    check("prng_real1 stays in [0,1]", real1_ok);
    brahe_prng_free(&a);
    brahe_prng_free(&b);
    brahe_prng_free(&c);

    /* --- integer pretty-printing (both formats return heap strings) --- */
    char *comma = brahe_pretty_int(1768372193, BRAHE_PRETTY_COMMA);
    check("pretty_int(1768372193, COMMA)",
          comma != NULL && strcmp(comma, "1,768,372,193") == 0);
    free(comma);
    char *text = brahe_pretty_int(-10263, BRAHE_PRETTY_TEXT);
    check("pretty_int(-10263, TEXT)",
          text != NULL && strcmp(text, "negative ten thousand, two hundred sixty-three") == 0);
    free(text);

    /* --- sinusoid synthesis + simple FFT (upstream brahe_test_fft bounds) --- */
    brahe_wave_factor_t factors[3] = { { 100.0, 20.0 }, { 50.0, 40.0 }, { 5.0, 100.0 } };
    static const int test_size = 1024;
    double *signal = brahe_make_sinusoid(factors, 3, test_size);
    check("make_sinusoid returns a buffer", signal != NULL);
    double *fft = brahe_simple_fft(signal, test_size);
    check("simple_fft returns a buffer", fft != NULL);
    if (signal != NULL && fft != NULL)
    {
        check("fft dc bin < 1.0", fft[0] < 1.0);
        check("fft bin 5 > 20.0", fft[5] > 20.0);
        check("fft bin 10 > 36.0", fft[10] > 36.0);
        check("fft bin 102 > 75.0", fft[102] > 75.0);
        check("fft bin 8 < 4.0", fft[8] < 4.0);
        check("fft bin 42 < 0.6", fft[42] < 0.6);
        check("fft bin 511 < 0.3", fft[511] < 0.3);
    }
    free(fft);
    free(signal);

    printf("libbrahe consumer test: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
