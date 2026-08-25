// test_package/test.cpp — R34: must call asplib API, not just print a string.
//
// This test creates a Biquad filter via the asplib CBiquadFactory, processes
// a simple sample, and verifies the output is finite. It links against
// libasplib_Biquad and libasplib_Core which together provide the filter
// implementation.
#include <cstdio>
#include <cmath>

#include "asplib/Biquad/apslib_BiquadFactory.h"
#include "asplib/Core/Constants_Typedefs/asplib_Typedefs.h"

int main(void) {
    // Create a biquad filter chain with 1 biquad at 44100 Hz sample rate
    ASPLIB_BIQUAD_HANDLE *biquads = asplib::CBiquadFactory::get_Biquads(1, 44100.0f, ASPLIB_OPT_NATIVE);
    if (!biquads) {
        fprintf(stderr, "FAIL: CBiquadFactory::get_Biquads returned NULL\n");
        return 1;
    }

    // Reset state
    ASPLIB_ERR err = asplib::CBiquadFactory::reset_Biquads(biquads);
    if (err != ASPLIB_ERR_NO_ERROR) {
        fprintf(stderr, "FAIL: reset_Biquads failed with error %d\n", (int)err);
        asplib::CBiquadFactory::destroy_Biquads(&biquads);
        return 1;
    }

    // Process a sample through the filter
    float in_val = 0.5f;
    float out_val = 0.0f;
    err = asplib::CBiquadFactory::calc_BiquadSample(biquads, in_val, &out_val);
    if (err != ASPLIB_ERR_NO_ERROR) {
        fprintf(stderr, "FAIL: calc_BiquadSample failed with error %d\n", (int)err);
        asplib::CBiquadFactory::destroy_Biquads(&biquads);
        return 1;
    }

    // Verify output is finite (NaN check)
    if (!std::isfinite(out_val)) {
        fprintf(stderr, "FAIL: output is not finite (out=%f)\n", out_val);
        asplib::CBiquadFactory::destroy_Biquads(&biquads);
        return 1;
    }

    fprintf(stdout, "asplib test: biquad created, sample processed, out=%f -- OK\n", out_val);

    // Clean up
    asplib::CBiquadFactory::destroy_Biquads(&biquads);
    return 0;
}
