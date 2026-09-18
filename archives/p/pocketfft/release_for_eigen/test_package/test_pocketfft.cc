// test_package consumer test for pocketfft (header-only C++ FFT library)
// R34: must genuinely call the library's public API and verify observable results.
#include <complex>
#include <cmath>
#include <cstdio>
#include <vector>
#include "pocketfft_hdronly.h"

int main() {
    using namespace pocketfft;
    const size_t n = 16;
    shape_t shape{n};
    stride_t stride{sizeof(std::complex<double>)};

    std::vector<std::complex<double>> data(n), buf(n);
    // deterministic input
    for (size_t i = 0; i < n; ++i)
        data[i] = std::complex<double>(i + 1.0, 2.0 * i - 0.5);

    // forward FFT: data -> buf
    c2c(shape, stride, stride, shape_t{0}, FORWARD, data.data(), buf.data(), 1.0);
    // backward FFT: buf -> data (normalized by 1/n for round trip)
    c2c(shape, stride, stride, shape_t{0}, BACKWARD, buf.data(), data.data(), 1.0 / n);

    // verify round trip within tolerance
    double maxerr = 0.0;
    for (size_t i = 0; i < n; ++i) {
        double er = std::abs(data[i] - std::complex<double>(i + 1.0, 2.0 * i - 0.5));
        if (er > maxerr) maxerr = er;
    }
    std::printf("round-trip max error: %.3e\n", maxerr);
    if (maxerr > 1e-10) {
        std::fprintf(stderr, "FAIL: FFT round trip error too large\n");
        return 1;
    }
    std::printf("pocketfft consumer test: PASS\n");
    return 0;
}
