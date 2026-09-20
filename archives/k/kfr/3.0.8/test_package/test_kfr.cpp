/*
 * HarmonyOS PC consumer test for KFR 3.0.8.
 *
 * Links the exported kfr::kfr target, which pulls in the header-only core
 * (kfr) plus the two compiled static archives (kfr_io and kfr_dft), and
 * exercises the public DSP API:
 *
 *   1. convolve()          - header-only core, exact expected result
 *   2. correlate()         - header-only core, exact expected result
 *   3. convolve_filter     - FFT based path, i.e. the kfr_dft archive
 *   4. realdft/irealdft()  - real FFT round trip, also kfr_dft
 *   5. element math        - sin/sum/rms sanity on a synthesised vector
 *
 * The exit code is the PASS/FAIL signal (0 = every check passed).
 * The expected values in (1) and (2) are the ones upstream asserts in
 * tests/dft_test.cpp, so a regression in either layer is caught.
 */
#include <cmath>
#include <cstdio>

#include <kfr/base.hpp>
#include <kfr/dft.hpp>

using namespace kfr;

static int checks = 0;
static int failures = 0;

static void check_true(const char* what, bool cond)
{
    ++checks;
    if (cond) {
        std::printf("ok   %-38s true\n", what);
    } else {
        std::printf("FAIL %-38s false\n", what);
        ++failures;
    }
}

static void check_near(const char* what, double got, double want, double eps)
{
    ++checks;
    if (std::fabs(got - want) <= eps) {
        std::printf("ok   %-38s %.9f (want %.9f +- %g)\n", what, got, want, eps);
    } else {
        std::printf("FAIL %-38s %.9f (want %.9f +- %g)\n", what, got, want, eps);
        ++failures;
    }
}

int main()
{
    std::printf("KFR consumer test (HarmonyOS PC / aarch64)\n");
    std::printf("-----------------------------------------\n");

    /* 1. convolve(): header-only core */
    univector<fbase, 5> a({1, 2, 3, 4, 5});
    univector<fbase, 5> b({0.25, 0.5, 1.0, -2.0, 1.5});
    univector<fbase> c = convolve(a, b);
    check_true("convolve() size == 9", c.size() == 9u);
    check_near("convolve() rms",
               rms(c - univector<fbase>({0.25, 1.0, 2.75, 2.5, 3.75, 3.5, 1.5, -4.0, 7.5})),
               0.0, 1e-4);

    /* 2. correlate(): header-only core */
    univector<fbase> r = correlate(a, b);
    check_true("correlate() size == 9", r.size() == 9u);
    check_near("correlate() rms",
               rms(r - univector<fbase>({1.5, 1.0, 1.5, 2.5, 3.75, -4.0, 7.75, 3.5, 1.25})),
               0.0, 1e-4);

    /* 3. convolve_filter: FFT based overlap-add, requires kfr_dft */
    univector<fbase, 5> fdest;
    convolve_filter<fbase> filter(a);
    filter.apply(fdest, b);
    check_true("convolve_filter() output size == 5", fdest.size() == 5u);
    check_near("convolve_filter() rms",
               rms(fdest - univector<fbase>({0.25, 1.0, 2.75, 2.5, 3.75})),
               0.0, 1e-4);

    /* 4. real FFT round trip: realdft/irealdft are implemented in kfr_dft */
    const size_t N = 64;
    univector<fbase> in(N);
    for (size_t i = 0; i < N; ++i) {
        in[i] = std::sin(0.31f * static_cast<float>(i)) + 0.35f;
    }
    univector<complex<fbase>> spec = realdft(in);
    check_true("realdft() bin count == N/2+1", spec.size() == N / 2 + 1);
    univector<fbase> back = irealdft(spec) / N;
    check_near("realdft/irealdft round trip rms", rms(back - in), 0.0, 1e-4);

    /* 5. element math sanity on a synthesised vector */
    univector<fbase> ones(16);
    for (size_t i = 0; i < ones.size(); ++i) {
        ones[i] = 1.0f;
    }
    check_near("sum() of 16 ones", sum(ones), 16.0, 1e-6);
    check_near("rms() of 16 ones", rms(ones), 1.0, 1e-6);
    univector<fbase> scaled = ones * 2.0f + 1.0f;
    check_near("expression (v*2+1)[0]", static_cast<double>(scaled[0]), 3.0, 1e-6);
    check_true("expression (v*2+1) size", scaled.size() == 16u);
    check_near("abs() of -3.5", abs(-3.5f), 3.5, 1e-6);

    std::printf("-----------------------------------------\n");
    std::printf("checks=%d failures=%d\n", checks, failures);
    if (failures == 0) {
        std::printf("RESULT: PASS (%d/%d)\n", checks, checks);
        return 0;
    }
    std::printf("RESULT: FAIL (%d/%d)\n", checks - failures, checks);
    return 1;
}
