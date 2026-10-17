// Consumer smoke test for libcerfcpp 3.3 (C++ interface of libcerf).
// Exercises the real public API in <cerf.h> under __cplusplus
// (std::complex<double> overloads). Each check prints one "CHECK-OK:"
// line; the test_package conanfile counts those lines for the
// HMBS_TEST_PACKAGE_RESULT marker. Exit code is 0 only if all 6 checks
// pass, so exit-0-alone can never fake a pass.
#include <cmath>
#include <complex>
#include <cstdio>

#include "cerf.h"

namespace {

bool near(double a, double b, double tol) {
    if (std::isnan(a) && std::isnan(b)) {
        return true;
    }
    if (std::isinf(a) || std::isinf(b)) {
        return a == b;
    }
    double scale = 1.0;
    if (std::fabs(a) > scale) {
        scale = std::fabs(a);
    }
    if (std::fabs(b) > scale) {
        scale = std::fabs(b);
    }
    return std::fabs(a - b) <= tol * scale;
}

bool near_cmplx(std::complex<double> a, std::complex<double> b, double tol) {
    return near(a.real(), b.real(), tol) && near(a.imag(), b.imag(), tol);
}

}  // namespace

int main() {
    int failed = 0;

    // 1) w_of_z(0) == 1 (Faddeeva w at origin).
    {
        std::complex<double> got = w_of_z(std::complex<double>(0.0, 0.0));
        if (near_cmplx(got, std::complex<double>(1.0, 0.0), 1e-12)) {
            std::printf("CHECK-OK: w_of_z_origin\n");
        } else {
            std::printf("CHECK-FAIL: w_of_z_origin got (%g,%g)\n", got.real(), got.imag());
            ++failed;
        }
    }

    // 2) cerf(0) == 0 and cerfc(0) == 1.
    {
        std::complex<double> z(0.0, 0.0);
        std::complex<double> erf = cerf(z);
        std::complex<double> erfc = cerfc(z);
        if (near_cmplx(erf, std::complex<double>(0.0, 0.0), 1e-12) &&
            near_cmplx(erfc, std::complex<double>(1.0, 0.0), 1e-12)) {
            std::printf("CHECK-OK: cerf_cerfc_origin\n");
        } else {
            std::printf("CHECK-FAIL: cerf_cerfc_origin\n");
            ++failed;
        }
    }

    // 3) Real special cases: erfcx(0) == 1, erfi(0) == 0, dawson(0) == 0.
    {
        if (near(erfcx(0.0), 1.0, 1e-12) && near(erfi(0.0), 0.0, 1e-12) &&
            near(dawson(0.0), 0.0, 1e-12)) {
            std::printf("CHECK-OK: real_special_origin\n");
        } else {
            std::printf("CHECK-FAIL: real_special_origin erfcx=%g erfi=%g dawson=%g\n",
                        erfcx(0.0), erfi(0.0), dawson(0.0));
            ++failed;
        }
    }

    // 4) Complex Dawson against the upstream-tested reference value
    // (same Maple reference as upstream test/cerftest.c uses for cerf paths).
    {
        std::complex<double> got = cdawson(std::complex<double>(1.0, 0.0));
        // dawson(1) = 0.538079506912768... (real axis).
        if (near(got.real(), 0.5380795069127684, 1e-9) && near(got.imag(), 0.0, 1e-9)) {
            std::printf("CHECK-OK: cdawson_real_axis\n");
        } else {
            std::printf("CHECK-FAIL: cdawson_real_axis got (%g,%g)\n", got.real(), got.imag());
            ++failed;
        }
    }

    // 5) Voigt peak is positive and finite; width at half maximum positive.
    {
        double v = voigt(0.0, 1.0, 1.0);
        double hwhm = voigt_hwhm(1.0, 1.0);
        if (std::isfinite(v) && v > 0.0 && std::isfinite(hwhm) && hwhm > 0.0) {
            std::printf("CHECK-OK: voigt_peak width=%g hwhm=%g\n", v, hwhm);
        } else {
            std::printf("CHECK-FAIL: voigt_peak v=%g hwhm=%g\n", v, hwhm);
            ++failed;
        }
    }

    // 6) im_w_of_x(0) == 0 and real/imaginary parts agree with w_of_z.
    {
        double im = im_w_of_x(0.0);
        std::complex<double> w = w_of_z(std::complex<double>(0.5, 0.25));
        bool ok = near(im, 0.0, 1e-12) && near(re_w_of_z(0.5, 0.25), w.real(), 1e-12) &&
                  near(im_w_of_z(0.5, 0.25), w.imag(), 1e-12);
        if (ok) {
            std::printf("CHECK-OK: w_parts_consistent\n");
        } else {
            std::printf("CHECK-FAIL: w_parts_consistent\n");
            ++failed;
        }
    }

    if (failed == 0) {
        std::printf("ALL 6 CHECKS PASSED\n");
    } else {
        std::printf("%d/6 checks failed\n", failed);
    }
    return failed == 0 ? 0 : 1;
}
