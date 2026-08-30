#include <cstdio>
#include <cmath>
#include <cstdint>

#include <Biquads/apslib_BiquadFactory.h>
#include <Biquads/Biquad_Native/asplib_Biquad_Native.h>

using namespace asplib;

// Substantive smoke test: creates real Biquad filters through the public
// asplib API (CBiquadFactory + CBiquad_Native), processes actual samples and
// verifies that the DSP output is finite and non-zero. Also exercises
// resetState(), which was an infinite loop in the upstream commit and is
// fixed by the recipe's patch.
int main()
{
    int failures = 0;

    // ── 1. Factory path: 2 chained native biquads ───────────────────────
    ASPLIB_BIQUAD_HANDLE *biquads =
        CBiquadFactory::get_Biquads(2, 44100.0f, ASPLIB_OPT_NATIVE);
    if (!biquads) { std::printf("FAIL: get_Biquads returned NULL\n"); return 1; }
    if (CBiquadFactory::get_maxBiquads(biquads) != 2) {
        std::printf("FAIL: get_maxBiquads != 2\n"); return 1;
    }

    ASPLIB_BIQUAD_COEFFICIENTS coef0 = {0.1f, 0.2f, 0.1f, -0.6f, 0.3f};
    ASPLIB_BIQUAD_COEFFICIENTS coef1 = {0.5f, 0.0f, 0.0f, 0.0f, 0.0f};
    if (CBiquadFactory::set_BiquadCoefficients(biquads, &coef0, (uint32_t)0) != ASPLIB_ERR_NO_ERROR ||
        CBiquadFactory::set_BiquadCoefficients(biquads, &coef1, (uint32_t)1) != ASPLIB_ERR_NO_ERROR) {
        std::printf("FAIL: set_BiquadCoefficients\n"); return 1;
    }

    float in[8] = {1.0f, 0.0f, 0.0f, 0.0f, 0.5f, -0.25f, 0.0f, 0.125f};
    float out[8] = {0.0f};
    if (CBiquadFactory::calc_BiquadSamples(biquads, in, out, 8) != ASPLIB_ERR_NO_ERROR) {
        std::printf("FAIL: calc_BiquadSamples\n"); return 1;
    }
    for (int i = 0; i < 8; ++i) {
        if (!std::isfinite(out[i])) { std::printf("FAIL: non-finite out[%d]\n", i); ++failures; }
    }
    // expected out[0] = 0.5 * 0.1 = 0.05 (chain of biquad0 then biquad1)
    if (std::fabs(out[0] - 0.05f) > 1e-4f) {
        std::printf("FAIL: out[0]=%f (expected ~0.05)\n", out[0]); ++failures;
    }
    bool nonzero = false;
    for (int i = 0; i < 8; ++i) {
        if (std::fabs(out[i]) > 1e-6f) { nonzero = true; break; }
    }
    if (!nonzero) { std::printf("FAIL: all outputs zero\n"); ++failures; }

    // ── 2. Direct CBiquad_Native path + resetState (patched) ────────────
    CBiquad_Native bq(1, 44100.0f);
    if (bq.updateCoefficients(&coef0, 0.0f) != ASPLIB_ERR_NO_ERROR) {
        std::printf("FAIL: direct updateCoefficients\n"); ++failures;
    }
    float s = bq.calcSample(1.0f);
    if (std::fabs(s - 0.1f) > 1e-4f) {
        std::printf("FAIL: direct calcSample=%f (expected ~0.1)\n", s); ++failures;
    }
    bq.resetState();          // must return (upstream infinite loop fixed)
    float s2 = bq.calcSample(1.0f);
    if (std::fabs(s2 - 0.1f) > 1e-4f) {
        std::printf("FAIL: calcSample after reset=%f (expected ~0.1)\n", s2); ++failures;
    }

    CBiquadFactory::destroy_Biquads(&biquads);

    if (failures == 0) {
        std::printf("test_asplib: OK (factory chain + direct + resetState)\n");
        return 0;
    }
    std::printf("test_asplib: %d failure(s)\n", failures);
    return 1;
}
