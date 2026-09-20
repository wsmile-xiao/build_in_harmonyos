// Consumer test for the installed libelas package.
//
// Builds a deterministic, heavily textured stereo pair whose right image is the
// left image shifted by a known number of pixels, runs Elas::process through the
// public header, and checks that the recovered disparity matches the shift.
// This exercises the SSE2->NEON port end to end.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

#include <elas.h>

static int checks;
static int failures;

static void check(bool ok, const char *what)
{
    checks++;
    if (ok) {
        printf("ok   %s\n", what);
    } else {
        failures++;
        printf("FAIL %s\n", what);
    }
}

int main(void)
{
    const int W = 160;
    const int H = 96;
    const int SHIFT = 6;

    std::vector<uint8_t> left((size_t)W * H);
    std::vector<uint8_t> right((size_t)W * H);
    uint32_t state = 12345u;
    for (size_t i = 0; i < left.size(); ++i) {
        state = state * 1664525u + 1013904223u;
        left[i] = (uint8_t)((state >> 16) & 0xFF);
    }
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            int sx = x + SHIFT;
            if (sx >= W) {
                sx = W - 1;
            }
            right[(size_t)y * W + x] = left[(size_t)y * W + sx];
        }
    }

    Elas::parameters param;
    param.disp_min = 0;
    param.disp_max = 32;
    param.postprocess_only_left = false;

    Elas elas(param);
    std::vector<float> d1((size_t)W * H);
    std::vector<float> d2((size_t)W * H);
    const int32_t dims[3] = {W, H, W};
    elas.process(left.data(), right.data(), d1.data(), d2.data(), dims);

    int interior = 0;
    int valid = 0;
    int good = 0;
    double sum = 0.0;
    for (int y = 16; y < H - 16; ++y) {
        for (int x = SHIFT + 16; x < W - 16; ++x) {
            float d = d1[(size_t)y * W + x];
            interior++;
            if (d > 0.0f) {
                valid++;
                sum += d;
            }
            if (std::fabs(d - (float)SHIFT) <= 1.0f) {
                good++;
            }
        }
    }

    printf("interior=%d valid=%d good=%d mean_valid=%.2f\n",
           interior, valid, good, valid ? sum / valid : 0.0);

    check(interior > 0, "interior sampling region is non-empty");
    check(valid > interior / 2, "majority of interior pixels have a disparity");
    check(good > interior / 2, "majority of interior disparities match the shift (6 +/- 1)");
    check(valid > 0 && std::fabs(sum / valid - (double)SHIFT) <= 1.0,
          "mean valid disparity is within 1 px of the shift");

    bool any_left = false;
    bool any_right = false;
    for (size_t i = 0; i < d1.size(); ++i) {
        if (d1[i] > 0.0f) {
            any_left = true;
        }
        if (d2[i] > 0.0f) {
            any_right = true;
        }
    }
    check(any_left, "left disparity map is not empty");
    check(any_right, "right disparity map is not empty");

    printf("checks: %d, failures: %d\n", checks, failures);
    return failures ? 1 : 0;
}
