// Consumer test for inspectrum 0.3.1 (L1).
//
// Links the exact dependency face inspectrum uses — Qt5 Core/Widgets/
// Concurrent, single-precision FFTW (fftw3f) and liquid-dsp — and calls
// real APIs from each:
//
//   * FFTW: plan + execute + verify an 8-point float FFT round trip.
//   * liquid-dsp: generate a kaiser low-pass filter and check the DC gain.
//   * Qt: initialize QCoreApplication and exercise QString/QStringList.
//
// Exits 0 only if every stage passes.
#include <QCoreApplication>
#include <QString>
#include <QStringList>

#include <fftw3.h>
#include <liquid/liquid.h>

#include <cmath>
#include <cstdio>
#include <utility>

static int test_fftwf()
{
    const int n = 8;
    fftwf_complex *in = fftwf_alloc_complex(n);
    fftwf_complex *out = fftwf_alloc_complex(n);
    if (!in || !out)
        return 1;
    for (int i = 0; i < n; ++i) {
        in[i][0] = (i % 2 == 0) ? 1.0f : -1.0f;
        in[i][1] = 0.0f;
    }
    fftwf_plan plan = fftwf_plan_dft_1d(n, in, out, FFTW_FORWARD, FFTW_ESTIMATE);
    if (!plan) {
        fftwf_free(in);
        fftwf_free(out);
        return 2;
    }
    fftwf_execute(plan);
    fftwf_destroy_plan(plan);

    // Alternating +/-1 sequence is e^{i*pi*n} = e^{2*pi*i*4*n/8}: all energy
    // lands in bin k=4 (magnitude 8); DC bin must be 0.
    float dc = std::fabs(out[0][0]) + std::fabs(out[0][1]);
    float bin4 = std::sqrt(out[4][0] * out[4][0] + out[4][1] * out[4][1]);
    bool ok = dc < 1e-3f && std::fabs(bin4 - 8.0f) < 1e-3f;
    fftwf_free(in);
    fftwf_free(out);
    if (!ok) {
        std::fprintf(stderr, "FFTW check failed: dc=%f bin4=%f\n", dc, bin4);
        return 3;
    }
    return 0;
}

static int test_liquid()
{
    // kaiser low-pass, cutoff 0.25, 61 taps: all coefficients finite and
    // the DC gain (coefficient sum) sane for liquid's normalization
    // (empirically ~2.0 for fc=0.25).
    const unsigned int taps = 61;
    float h[61];
    liquid_firdes_kaiser(taps, 0.25f, 60.0f, 0.0f, h);
    float sum = 0.0f;
    for (unsigned int i = 0; i < taps; ++i) {
        if (!std::isfinite(h[i]))
            return 4;
        sum += h[i];
    }
    if (sum < 0.5f || sum > 2.5f) {
        std::fprintf(stderr, "liquid check failed: coefficient sum=%f\n", sum);
        return 5;
    }
    // Execute the filter on an impulse through the real API path.
    // This liquid-dsp build defines liquid_float_complex as
    // struct {float real; float imag;} (LIQUID_DEFINE_COMPLEX fallback).
    firfilt_crcf f = firfilt_crcf_create(h, taps);
    if (!f)
        return 6;
    liquid_float_complex x;
    x.real = 1.0f;
    x.imag = 0.0f;
    firfilt_crcf_push(f, x);
    liquid_float_complex y;
    firfilt_crcf_execute(f, &y);
    firfilt_crcf_destroy(f);
    if (!std::isfinite(y.real) || !std::isfinite(y.imag)) {
        std::fprintf(stderr, "liquid filter execution produced non-finite output\n");
        return 7;
    }
    return 0;
}

static int test_qt(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("test_inspectrum"));
    const QStringList parts = QStringLiteral("inspectrum:0.3.1").split(':');
    if (parts.size() != 2 || parts[0] != QLatin1String("inspectrum")
            || parts[1] != QLatin1String("0.3.1"))
        return 6;
    return 0;
}

int main(int argc, char **argv)
{
    int rc = test_qt(argc, argv);
    if (rc)
        return rc;
    rc = test_fftwf();
    if (rc)
        return rc;
    rc = test_liquid();
    if (rc)
        return rc;
    std::printf("test_inspectrum: all stages passed (Qt5 + fftw3f + liquid)\n");
    return 0;
}
