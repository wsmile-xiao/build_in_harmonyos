// Consumer smoke test for blitzwave/0.8.0 on OHOS.
// Exercises the public API like a real downstream user:
//  1. 1-D CDF(2,2) non-standard decomposition + reconstruction of a smooth
//     signal must round-trip (max |orig - recon| < 1e-10).
//  2. Wavelet descriptor identity checks (WL_HAAR == WL_CDF_1_1,
//     WL_HAAR != WL_CDF_2_2), mirroring upstream Wavelet-test.
//  3. 2-D decomposition over selected dimensions + coefficient re-separation
//     round-trip (mirrors the upstream WaveletDecomp-test coefficient
//     sorting test path).
#include <cmath>
#include <cstdio>
#include <cstdlib>

#include <blitz/array.h>
#include <blitzwave/Wavelet.h>
#include <blitzwave/WaveletDecomp.h>

using namespace blitz;
using namespace bwave;

int main() {
    // 1) 1-D perfect reconstruction
    Array<double, 1> x(256);
    for (int i = 0; i < x.size(); ++i) {
        x(i) = std::sin(0.1 * i) + 0.25 * std::cos(0.37 * i);
    }
    Array<double, 1> orig(x.copy());
    WaveletDecomp<1> dec(WL_CDF_2_2, NONSTD_DECOMP, 0);
    TinyVector<int, 1> depth = dec.apply(x);
    TinyVector<int, 1> rdepth = dec.applyInv(x);
    double maxdiff = max(abs(orig - x));
    std::printf("1-D CDF(2,2) roundtrip: depth=(%d) rdepth=(%d) maxdiff=%.3e\n",
                depth(0), rdepth(0), maxdiff);
    if (!(depth(0) > 0) || depth(0) != -rdepth(0)) {
        std::fprintf(stderr, "FAIL: decomposition depth mismatch\n");
        return 1;
    }
    if (maxdiff >= 1e-10) {
        std::fprintf(stderr, "FAIL: 1-D reconstruction error too large\n");
        return 1;
    }

    // 2) Wavelet descriptor identities (upstream Wavelet-test asserts)
    if (!(WL_HAAR == WL_CDF_1_1)) {
        std::fprintf(stderr, "FAIL: WL_HAAR != WL_CDF_1_1\n");
        return 1;
    }
    if (WL_HAAR == WL_CDF_2_2) {
        std::fprintf(stderr, "FAIL: WL_HAAR == WL_CDF_2_2\n");
        return 1;
    }

    // 3) 2-D selected-dimensions decomposition + coefficient re-separation
    Array<double, 2> img(64, 64);
    for (int i = 0; i < img.rows(); ++i)
        for (int j = 0; j < img.cols(); ++j)
            img(i, j) = 128.0 + 40.0 * std::sin(i * 0.2) * std::cos(j * 0.13);
    Array<double, 2> orig2(img.copy());
    WaveletDecomp<2> dec2(WL_CDF_2_2, NONSTD_DECOMP, 0);
    dec2.dimSelection(TinyVector<bool, 2>(true, true));
    dec2.apply(img);
    WaveletDecomp<2> dec2sep(dec2, SEPARATED_COEFFS);
    Array<TinyVector<int, 2>, 1> idx(dec2sep.indices(img));
    Array<double, 2> sep(img.shape());
    for (int i = 0; i < idx.size(); ++i)
        dec2sep.coeffs(sep, idx(i)) = dec2.coeffs(img, idx(i));
    img = 0.0;
    for (int i = 0; i < idx.size(); ++i)
        dec2.coeffs(img, idx(i)) = dec2sep.coeffs(sep, idx(i));
    dec2.applyInv(img);
    double maxdiff2 = max(abs(orig2 - img));
    std::printf("2-D separated-coeffs roundtrip: idx=%d maxdiff=%.3e\n",
                static_cast<int>(idx.size()), maxdiff2);
    if (maxdiff2 >= 1e-8) {
        std::fprintf(stderr, "FAIL: 2-D reconstruction error too large\n");
        return 1;
    }

    std::printf("PASS: blitzwave consumer test\n");
    return 0;
}
