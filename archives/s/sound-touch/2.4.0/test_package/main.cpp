#include <iostream>
#include <soundtouch/SoundTouch.h>
#include <cstring>

int main() {
    soundtouch::SoundTouch st;

    // Configure for 44100 Hz mono float samples
    st.setSampleRate(44100);
    st.setChannels(1);
    st.setTempoChange(50.0f);  // speed up 50%

    // Verify version
    std::cout << "SoundTouch version: " << st.getVersionString() << std::endl;

    // Generate 1 second of sine-ish input (44100 float samples)
    const int NUM_SAMPLES = 44100;
    float input[NUM_SAMPLES];
    for (int i = 0; i < NUM_SAMPLES; i++) {
        input[i] = static_cast<float>(i % 100) / 100.0f;
    }

    // Feed samples into the processing pipeline
    st.putSamples(input, NUM_SAMPLES);

    // Receive processed output — tempo+50% should produce fewer samples
    float output[NUM_SAMPLES];
    int received = st.receiveSamples(output, NUM_SAMPLES);

    std::cout << "Input samples: " << NUM_SAMPLES << std::endl;
    std::cout << "Output samples: " << received << std::endl;

    // Verify processing actually produced output (R40: deep adaptation check)
    if (received <= 0) {
        std::cerr << "FAIL: receiveSamples returned 0, audio pipeline not working" << std::endl;
        return 1;
    }

    // Verify output differs from input (tempo change should alter the data)
    bool has_diff = false;
    for (int i = 0; i < received && i < NUM_SAMPLES; i++) {
        if (output[i] != input[i]) {
            has_diff = true;
            break;
        }
    }
    if (!has_diff) {
        std::cerr << "FAIL: output identical to input, processing may not be active" << std::endl;
        return 1;
    }

    std::cout << "Audio processing pipeline: OK (output differs from input)" << std::endl;
    return 0;
}
