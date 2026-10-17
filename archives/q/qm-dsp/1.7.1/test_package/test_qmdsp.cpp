// test_qmdsp.cpp — consumer test for the qm-dsp Conan package (R34).
// Four real assertions through the packaged headers (no stubs):
//   CASE 1: Pitch::getFrequencyForPitch(69) == 440Hz.
//   CASE 2: FFT DC forward: [1,1,1,1] -> re[0] == 4, imag all zero.
//   CASE 3: MathUtilities::mean([0,4,3,-1]) == 1.5.
//   CASE 4: MedianFilter standalone [1,3,5,7] -> [1,3,5,5].
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "base/Pitch.h"
#include "dsp/transforms/FFT.h"
#include "maths/MathUtilities.h"
#include "maths/MedianFilter.h"

namespace {
int s_failures = 0;

void check(bool ok, const char* label, const std::string& detail) {
    if (ok) {
        std::cout << "CASE PASS: " << label << " (" << detail << ")" << std::endl;
    } else {
        ++s_failures;
        std::cout << "CASE FAIL: " << label << " (" << detail << ")" << std::endl;
    }
}
}  // namespace

int main() {
    // CASE 1: Pitch conversion (MIDI 69 = A440).
    {
        float freq = Pitch::getFrequencyForPitch(69);
        bool ok = std::fabs(freq - 440.0f) < 1e-3f;
        check(ok, "pitch A440", "freq=" + std::to_string(freq));
    }
    // CASE 2: FFT DC-only signal, complex path.
    {
        double in[] = {1, 1, 1, 1};
        double re[] = {999, 999, 999, 999};
        double im[] = {999, 999, 999, 999};
        FFT(4).process(false, in, 0, re, im);
        bool ok = (re[0] == 4.0) && (re[1] == 0.0) && (re[2] == 0.0) &&
                  (re[3] == 0.0) && (im[0] == 0.0) && (im[1] == 0.0) &&
                  (im[2] == 0.0) && (im[3] == 0.0);
        check(ok, "fft dc forward",
              "re0=" + std::to_string(re[0]) + " im1=" + std::to_string(im[1]));
    }
    // CASE 3: MathUtilities mean.
    {
        double d0[] = {0, 4, 3, -1};
        double mean = MathUtilities::mean(d0, 4);
        bool ok = (mean == 1.5);
        check(ok, "mathutilities mean", "mean=" + std::to_string(mean));
    }
    // CASE 4: MedianFilter standalone matches upstream semantics.
    {
        std::vector<double> in;
        in.push_back(1);
        in.push_back(3);
        in.push_back(5);
        in.push_back(7);
        std::vector<double> out = MedianFilter<double>::filter(3, in);
        bool ok = out.size() == 4 && out[0] == 1 && out[1] == 3 && out[2] == 5 &&
                  out[3] == 5;
        std::string detail = "size=" + std::to_string(out.size());
        if (out.size() == 4) {
            detail += " out3=" + std::to_string(out[3]);
        }
        check(ok, "medianfilter standalone", detail);
    }

    if (s_failures == 0) {
        std::cout << "ALL 4 CASES PASSED" << std::endl;
        return 0;
    }
    std::cout << s_failures << " CASE(S) FAILED" << std::endl;
    return 1;
}
