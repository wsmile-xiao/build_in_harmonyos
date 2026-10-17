// test_mffm_fftw.cpp — consumer test for mffm-fftw 1.7.
//
// Drives the real mffm-fftw API end-to-end:
//   * complexFFTData / complexFFT — fills an 8-sample buffer, runs the
//     forward transform and checks the DC/peak power behaviour, then runs
//     the inverse transform (Parseval round trip).
//   * realFFTData / realFFT — same round trip on a real buffer.
// Only the installed public headers (<mffm/*.H>) and linked libs
// (libfft, lib2Dfft) are used. R34: genuinely depends on the package.

#include <mffm/complexFFT.H>
#include <mffm/realFFT.H>

#include <cmath>
#include <cstdio>
#include <cstdlib>

static int failures = 0;

#define CHECK(cond, msg)                                   \
  do {                                                     \
    if (!(cond)) {                                         \
      std::printf("FAIL: %s\n", msg);                      \
      ++failures;                                          \
    }                                                      \
  } while (0)

int main() {
  // ---- complexFFT round trip (N = 8) ----
  {
    const int n = 8;
    complexFFTData data(n);
    complexFFT fft(&data);

    // impulse at DC: only bin 0 is non-zero.
    for (int i = 0; i < n; ++i) {
      c_re(data.in[i]) = (i == 0) ? 1.0 : 0.0;
      c_im(data.in[i]) = 0.0;
    }
    fft.fwdTransform();
    // A pure DC impulse yields a flat spectrum: every bin has magnitude 1
    // (un-normalised FFTW forward). Sum of squared magnitudes == N.
    double energy = 0.0;
    for (int i = 0; i < n; ++i) {
      energy += c_re(data.out[i]) * c_re(data.out[i]) +
                c_im(data.out[i]) * c_im(data.out[i]);
    }
    CHECK(std::fabs(energy - (double)n) < 1e-6,
          "complexFFT fwd energy of DC impulse == N");

    int maxbin = data.compPowerSpec();
    CHECK(maxbin == 0, "complexFFT power spectrum peaks at DC bin");

    // round trip: inverse transform recovers the (un-normalised) input.
    fft.invTransform();
    CHECK(std::fabs(c_re(data.in[0]) / (double)n - 1.0) < 1e-6,
          "complexFFT inverse recovers DC amplitude");
  }

  // ---- realFFT round trip (N = 16) ----
  {
    const int n = 16;
    realFFTData data(n);
    realFFT fft(&data);
    for (int i = 0; i < n; ++i)
      data.in[i] = (i % 2 == 0) ? 1.0 : -1.0;   // alternating square wave
    fft.fwdTransform();
    data.compPowerSpec();
    // power_spectrum is allocated with size/2+1 entries; the Nyquist bin
    // lives at index n/2. realFFTData::getHalfSize() only returns n/2 for
    // even n (upstream quirk), so iterate the full array here.
    const int ps_len = n / 2 + 1;
    double total = 0.0;
    for (int i = 0; i < ps_len; ++i)
      total += data.power_spectrum[i];
    CHECK(total > 0.0, "realFFT power spectrum is positive");
    // Inverse transform (un-normalised) restores the original waveform.
    fft.invTransform();
    bool roundtrip_ok = true;
    for (int i = 0; i < n; ++i) {
      double expect = (i % 2 == 0) ? 1.0 : -1.0;
      if (std::fabs(data.in[i] / (double)n - expect) > 1e-6)
        roundtrip_ok = false;
    }
    CHECK(roundtrip_ok, "realFFT inverse recovers original waveform");
  }

  if (failures == 0)
    std::printf("test_mffm-fftw: ALL PASSED\n");
  return failures == 0 ? 0 : 1;
}
