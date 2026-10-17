/*
 * HarmonyOS PC consumer test for KFR 7.0.1.
 *
 * Links the exported kfr::kfr target (header-only core + kfr_io + kfr_dft
 * static archives) and exercises the public DSP API:
 *
 *   1. convolve()          - full linear convolution (kfr_dft path)
 *   2. correlate()         - cross-correlation
 *   3. realdft()/irealdft()- real FFT forward/inverse round trip
 *   4. element math        - sum/rms/abs and expression templates
 *
 * The exit code is the PASS/FAIL signal (0 = every check passed).  The FFT
 * round-trip check compares waveform shape (both signals normalised to unit
 * rms) so it is independent of any forward/inverse scaling convention and still
 * fails on a real numerical regression.
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
    std::printf("KFR consumer test (HarmonyOS PC / aarch64, kfr 7.0.1)\n");
    std::printf("-----------------------------------------------------\n");

    /* 1. convolve(): full linear convolution via the DFT path */
    univector<fbase, 5> a({1, 2, 3, 4, 5});
    univector<fbase, 5> b({0.25, 0.5, 1.0, -2.0, 1.5});
    univector<fbase> c = convolve(a, b);
    check_true("convolve() size == 9", c.size() == 9u);
    check_near("convolve() rms",
               rms(c - univector<fbase>({0.25, 1.0, 2.75, 2.5, 3.75, 3.5, 1.5, -4.0, 7.5})),
               0.0, 1e-4);

    /* 2. correlate(): cross-correlation */
    univector<fbase> r = correlate(a, b);
    check_true("correlate() size == 9", r.size() == 9u);
    check_near("correlate() rms",
               rms(r - univector<fbase>({1.5, 1.0, 1.5, 2.5, 3.75, -4.0, 7.75, 3.5, 1.25})),
               0.0, 1e-4);

    /* 3. real FFT round trip: realdft()/irealdft() live in kfr_dft */
    const size_t N = 64;
    univector<fbase> in(N);
    for (size_t i = 0; i < N; ++i) {
        in[i] = std::sin(0.31f * static_cast<float>(i)) + 0.35f;
    }
    univector<complex<fbase>> spec = realdft(in);
    check_true("realdft() bin count == N/2+1", spec.size() == N / 2 + 1);
    univector<fbase> back = irealdft(spec);
    check_true("irealdft() length == N", back.size() == N);
    // Normalisation-independent: compare unit-rms waveform shape.
    fbase scale_back = rms(back);
    fbase scale_in = rms(in);
    check_near("realdft/irealdft round-trip shape",
               rms(back / scale_back - in / scale_in), 0.0, 1e-3);

    /* 4. element math sanity on a synthesised vector */
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

    std::printf("-----------------------------------------------------\n");
    std::printf("checks=%d failures=%d\n", checks, failures);
    if (failures == 0) {
        std::printf("RESULT: PASS (%d/%d)\n", checks, checks);
        return 0;
    }
    std::printf("RESULT: FAIL (%d/%d)\n", checks - failures, checks);
    return 1;
}
