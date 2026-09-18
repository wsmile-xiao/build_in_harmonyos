/* Consumer test for the installed plfit library.
 *
 * Deterministic (srand-fixed) discrete and continuous power-law samples are
 * generated through the packaged sampling routines and fitted back with the
 * packaged fitting routines; the recovered exponents, the KS statistic, the
 * log-likelihood and the installed version header are asserted.
 */

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <plfit.h>
#include <plfit_sampling.h>

#define NUM_SAMPLES 5000

static int checks = 0;
static int failures = 0;

static void check(int condition, const char* message) {
    checks++;
    if (condition) {
        printf("  ok   %s\n", message);
    } else {
        printf("  FAIL %s\n", message);
        failures++;
    }
}

int main(void) {
    plfit_continuous_options_t copt;
    plfit_discrete_options_t dopt;
    plfit_mt_rng_t rng;
    plfit_result_t result;
    double* data;
    double mean, variance, skewness, kurtosis;
    size_t i;

    data = (double*)malloc(sizeof(double) * NUM_SAMPLES);
    if (!data) {
        fprintf(stderr, "out of memory\n");
        return 2;
    }

    check(strcmp(PLFIT_VERSION_STRING, "0.9.6") == 0,
          "installed plfit_version.h reports 0.9.6");

    srand(42);
    plfit_mt_init(&rng);

    printf("discrete zeta sample (alpha=2.5, xmin=1, n=%d)\n", NUM_SAMPLES);
    for (i = 0; i < NUM_SAMPLES; i++)
        data[i] = plfit_rzeta(1, 2.5, &rng);
    plfit_discrete_options_init(&dopt);
    dopt.p_value_method = PLFIT_P_VALUE_SKIP;
    check(plfit_discrete(data, NUM_SAMPLES, &dopt, &result) == 0,
          "plfit_discrete returns success");
    printf("    alpha=%.5f xmin=%.0f L=%.5f D=%.5f\n",
           result.alpha, result.xmin, result.L, result.D);
    check(result.alpha > 2.30 && result.alpha < 2.70,
          "discrete alpha recovered within [2.30, 2.70]");
    check(result.xmin >= 1.0 && result.xmin <= 3.0,
          "discrete xmin recovered within [1, 3]");
    check(result.D > 0.0 && result.D < 1.0,
          "discrete KS statistic within (0, 1)");
    check(result.L < 0.0, "discrete log-likelihood is negative");

    printf("continuous Pareto sample (target alpha=2.0, xmin=1, n=%d)\n",
           NUM_SAMPLES);
    /* plfit_rpareto(xmin, a): pdf ~ x^-(a+1); plgen passes gamma-1 for a
     * target exponent gamma, so a = 1.0 targets a fitted alpha of ~2.0. */
    for (i = 0; i < NUM_SAMPLES; i++)
        data[i] = plfit_rpareto(1.0, 1.0, &rng);
    plfit_continuous_options_init(&copt);
    copt.p_value_method = PLFIT_P_VALUE_SKIP;
    check(plfit_continuous(data, NUM_SAMPLES, &copt, &result) == 0,
          "plfit_continuous returns success");
    printf("    alpha=%.5f xmin=%.5f L=%.5f D=%.5f\n",
           result.alpha, result.xmin, result.L, result.D);
    check(result.alpha > 1.80 && result.alpha < 2.20,
          "continuous alpha recovered within [1.80, 2.20]");
    check(result.D > 0.0 && result.D < 1.0,
          "continuous KS statistic within (0, 1)");

    check(plfit_moments(data, NUM_SAMPLES, &mean, &variance, &skewness,
                        &kurtosis) == 0,
          "plfit_moments returns success");
    check(variance > 0.0 && kurtosis > 0.0,
          "sample variance and kurtosis are positive");
    printf("    mean=%.5f variance=%.5f skewness=%.5f kurtosis=%.5f\n",
           mean, variance, skewness, kurtosis);

    free(data);
    if (failures) {
        printf("plfit consumer test: %d/%d checks FAILED\n", failures, checks);
        return 1;
    }
    printf("plfit consumer test: OK (%d/%d checks passed)\n", checks, checks);
    return 0;
}
