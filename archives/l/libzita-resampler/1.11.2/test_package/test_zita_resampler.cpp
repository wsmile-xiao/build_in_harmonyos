#include <cmath>
#include <cstdlib>
#include <iostream>
#include <algorithm>
#include <vector>

#include <zita-resampler/resampler.h>

int main() {
    Resampler resampler;
    if (resampler.setup(48000, 44100, 1, 16) != 0 || resampler.nchan() != 1) {
        return 1;
    }
    std::vector<float> input(65536);
    for (size_t i = 0; i < input.size(); ++i)
        input[i] = 0.25f * std::sin(2.0f * 3.14159265358979323846f * 440.0f * i / 48000.0f);
    std::vector<float> output(65536, 0.0f);
    resampler.inp_data = input.data();
    resampler.out_data = output.data();
    resampler.inp_count = static_cast<unsigned int>(input.size());
    resampler.out_count = static_cast<unsigned int>(output.size());
    const unsigned int before = resampler.out_count;
    const int result = resampler.process();
    const bool has_signal = std::any_of(output.begin(), output.end(), [](float sample) {
        return std::fabs(sample) > 1.0e-6f;
    });
    if (result != 0 || resampler.out_count >= before || !has_signal) {
        std::cerr << "resampler produced no output\n";
        return 1;
    }
    std::cout << "zita-resampler functional assertion passed (produced="
              << (before - resampler.out_count) << " samples)\n";
    return 0;
}
