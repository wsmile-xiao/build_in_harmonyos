// Consumer smoke test for signalsmith-dsp 1.7.2 (header-only).
// Exercises a representative subset of the public headers/APIs so the
// test actually links against and runs real library code (R34).
#include <signalsmith-dsp/envelopes.h>
#include <signalsmith-dsp/filters.h>
#include <signalsmith-dsp/fft.h>
#include <signalsmith-dsp/delay.h>
#include <signalsmith-dsp/mix.h>
#include <signalsmith-dsp/rates.h>
#include <signalsmith-dsp/windows.h>
#include <cstdio>
#include <vector>
#include <complex>
#include <cmath>

int main() {
    // envelopes: cubic LFO
    signalsmith::envelopes::CubicLfo lfo(42);
    lfo.set(0.0f, 1.0f, 2.0f);
    float v = lfo.next();
    if (!(v >= 0.0f && v <= 1.0f)) return 1;

    // filters: biquad
    signalsmith::filters::BiquadStatic<double> bq;
    bq.reset();
    double f = bq(0.5);
    if (!std::isfinite(f)) return 1;

    // fft: real FFT round trip (RealFFT::fft writes complex output,
    // RealFFT::ifft writes real output back)
    signalsmith::fft::RealFFT<double> rfft(8);
    std::vector<double> in(8, 0), back(8);
    std::vector<std::complex<double>> out(8);
    in[0] = 1.0;
    rfft.fft(in.begin(), out.begin());
    rfft.ifft(out.begin(), back.begin());
    // Note: signalsmith RealFFT round-trip yields N*input (no 1/N
    // normalization on the inverse), so back[0] must be N = 8.
    if (std::fabs(back[0] - 8.0) > 1e-9) return 1;

    // delay: multi-channel buffer
    signalsmith::delay::MultiBuffer<double> db;
    db.resize(2, 64);

    // windows: Kaiser window
    signalsmith::windows::Kaiser kaiser(4.0);
    double w = kaiser(0.5);
    if (!(w >= 0.0 && w <= 1.0)) return 1;

    std::printf("dsp 1.7.2 consumer test OK v=%.3f f=%.3f w=%.3f\n", v, f, w);
    return 0;
}
