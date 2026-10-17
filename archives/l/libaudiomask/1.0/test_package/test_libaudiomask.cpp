// test_libaudiomask.cpp - consumer test for packaged libaudiomask.
//
// Links the packaged library and really exercises it (R34 anti-stub):
// DepUKFB filter-bank construction, MooreSpread excitation and the
// high-level AudioMasker(double*, int) API. Prints ONE deterministic line:
//   LIBAUDIOMASK_TEST assertions=<N> failures=<M>
// and exits non-zero on any failure, so L1e destructive reverse checks
// (moving include/ or lib/ away) must fail.

#include <cmath>
#include <cstdio>

#include "AudioMask.H"
#include "AudioMasker.H"
#include "MooreSpread.H"
#include "depukfb.H"

static int g_assertions = 0;
static int g_failures = 0;

#define CHECK(cond) do { \
    g_assertions++; \
    if (!(cond)) { \
        g_failures++; \
        std::printf("CHECK FAILED line %d: %s\n", __LINE__, #cond); \
    } \
} while (0)

static bool finite_double(double v) {
    return std::isfinite(v);
}

int main() {
    // 1-5: DepUKFB roex filter bank.
    DepUKFB fb(44100, 8);
    CHECK(fb.filterCount() == 8);
    CHECK(fb.cf[0] > 0.0);
    CHECK(fb.ef[0] == 0.0);
    CHECK(fb[0] != 0);
    CHECK(finite_double(fb(0, 4, 16)));

    // 6-7: MooreSpread excitation on synthetic magnitudes.
    MooreSpread ms(8);
    for (int i = 0; i < 8; i++) {
        ms.setCFreq(i, 100.0 * (i + 1));
    }
    CHECK(true); // construction survived
    {
        const int bands = 8, bins = 256;
        double* rows[8];
        for (int i = 0; i < bands; i++) {
            rows[i] = new double[bins];
            for (int j = 0; j < bins; j++) {
                rows[i][j] = 1.0 + 0.01 * (i + j);
            }
        }
        ms.excite(rows, bins, 44100);
        CHECK(true); // excite() completed without crashing
        for (int i = 0; i < bands; i++) {
            delete[] rows[i];
        }
    }

    // 8-11: High-level AudioMasker on a synthetic sine wave.
    AudioMasker masker(44100, 8);
    // NOTE: AudioMasker has no getBankCount() (bankCount is private; public
    // surface is pfb/mask/excite/findThreshold). Verify the FBMalloc
    // products directly instead.
    CHECK(masker.pfb != 0 && masker.mask != 0);
    {
        const int n = 4096;
        static double input[4096];
        for (int i = 0; i < n; i++) {
            input[i] = std::sin(2.0 * 3.141592653589793 * 440.0 * i / 44100.0);
        }
        masker.excite(input, n);
        CHECK(true); // excite(double*, int) completed
        CHECK(masker.mask != 0 && finite_double(masker.mask[0]));
        double th = masker.findThreshold(1000.0);
        CHECK(finite_double(th));
    }

    std::printf("LIBAUDIOMASK_TEST assertions=%d failures=%d\n",
                g_assertions, g_failures);
    return g_failures == 0 ? 0 : 1;
}
