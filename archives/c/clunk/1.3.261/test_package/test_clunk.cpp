/* Consumer test for the packaged clunk library.
 *
 * Case 1 (fft_roundtrip): run the header FFT implementation forward and back
 * and assert the roundtrip residual is tiny (genuine numeric assertion on
 * shipped headers).
 * Case 2 (buffer_api): exercise clunk::Buffer, whose methods live in the
 * compiled libclunk (forces real linkage; removing lib/ breaks this build).
 */
#include <clunk/buffer.h>
#include <clunk/fft_context.h>

#include <cmath>
#include <complex>
#include <cstdio>

typedef clunk::fft_context<5, float> fft_type;

static int test_fft_roundtrip() {
    fft_type fft;
    for (int i = 0; i < fft_type::N; ++i) {
        fft.data[i] = std::complex<float>((float)((i / 4) & 1), 0.0f);
    }
    fft.fft();
    double energy = 0.0;
    for (int i = 0; i < fft_type::N; ++i) {
        energy += std::abs(fft.data[i]);
    }
    if (!(energy > 0.0)) {
        std::printf("FAIL fft_roundtrip: spectrum has no energy\n");
        return 1;
    }
    fft.ifft();
    double worst = 0.0;
    for (int i = 0; i < fft_type::N; ++i) {
        std::complex<float> expect((float)((i / 4) & 1), 0.0f);
        double err = std::abs(fft.data[i] - expect);
        if (err > worst) {
            worst = err;
        }
    }
    std::printf("fft_roundtrip: N=%d energy=%.3f worst_residual=%.6f\n",
                fft_type::N, energy, worst);
    if (!(worst < 1e-3)) {
        std::printf("FAIL fft_roundtrip: residual too large\n");
        return 1;
    }
    std::printf("PASS fft_roundtrip\n");
    return 0;
}

static int test_buffer_api() {
    clunk::Buffer buf(1024);
    if (buf.get_size() != 1024) {
        std::printf("FAIL buffer_api: size is %u\n", (unsigned)buf.get_size());
        return 1;
    }
    buf.fill(0xAB);
    const unsigned char *p = (const unsigned char *)buf.get_ptr();
    for (size_t i = 0; i < buf.get_size(); ++i) {
        if (p[i] != 0xAB) {
            std::printf("FAIL buffer_api: byte %u is 0x%02x\n",
                        (unsigned)i, p[i]);
            return 1;
        }
    }
    clunk::Buffer copy = buf;
    if (copy.get_size() != buf.get_size()) {
        std::printf("FAIL buffer_api: copy size mismatch\n");
        return 1;
    }
    std::string dump = copy.dump();
    std::printf("buffer_api: size=%u dump_chars=%u\n",
                (unsigned)copy.get_size(), (unsigned)dump.size());
    if (dump.empty()) {
        std::printf("FAIL buffer_api: empty dump\n");
        return 1;
    }
    std::printf("PASS buffer_api\n");
    return 0;
}

int main() {
    int failures = 0;
    failures += test_fft_roundtrip();
    failures += test_buffer_api();
    if (failures == 0) {
        std::printf("ALL 2 CONSUMER CASES PASSED\n");
    }
    return failures;
}
