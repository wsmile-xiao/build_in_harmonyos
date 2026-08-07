#include <AudioFile/AudioFile.h>

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace {

bool nearly_equal(double lhs, double rhs, double tolerance = 0.02) {
    return std::fabs(lhs - rhs) <= tolerance;
}

bool validate_round_trip(AudioFileFormat format) {
    AudioFile<double> writer;
    writer.setSampleRate(44100);
    writer.setBitDepth(16);
    writer.setAudioBufferSize(2, 512);

    for (int i = 0; i < writer.getNumSamplesPerChannel(); ++i) {
        const double sample = std::sin(2.0 * 3.14159265358979323846 * i / 64.0) * 0.5;
        writer.samples[0][static_cast<size_t>(i)] = sample;
        writer.samples[1][static_cast<size_t>(i)] = -sample;
    }

    std::vector<uint8_t> encoded;
    if (!writer.saveToMemory(encoded, format) || encoded.empty()) {
        std::puts("FAIL: saveToMemory failed");
        return false;
    }

    AudioFile<double> reader;
    reader.shouldLogErrorsToConsole(false);
    if (!reader.loadFromMemory(encoded)) {
        std::puts("FAIL: loadFromMemory failed");
        return false;
    }
    if (reader.getSampleRate() != 44100 || reader.getBitDepth() != 16 ||
        reader.getNumChannels() != 2 || reader.getNumSamplesPerChannel() != 512) {
        std::puts("FAIL: decoded metadata mismatch");
        return false;
    }
    if (!nearly_equal(reader.samples[0][32], writer.samples[0][32]) ||
        !nearly_equal(reader.samples[1][96], writer.samples[1][96])) {
        std::puts("FAIL: decoded samples mismatch");
        return false;
    }
    return true;
}

bool validate_file_round_trip() {
    const std::string path = "adamstark_audiofile_consumer.wav";

    AudioFile<float> writer;
    writer.setSampleRate(22050);
    writer.setBitDepth(24);
    writer.setAudioBufferSize(1, 128);
    for (int i = 0; i < writer.getNumSamplesPerChannel(); ++i) {
        writer.samples[0][static_cast<size_t>(i)] = static_cast<float>(i) / 128.0f;
    }

    if (!writer.save(path, AudioFileFormat::Wave)) {
        std::puts("FAIL: save file failed");
        return false;
    }

    AudioFile<float> reader;
    reader.shouldLogErrorsToConsole(false);
    if (!reader.load(path)) {
        std::remove(path.c_str());
        std::puts("FAIL: load file failed");
        return false;
    }
    std::remove(path.c_str());

    if (reader.getSampleRate() != 22050 || reader.getBitDepth() != 24 ||
        reader.getNumChannels() != 1 || reader.getNumSamplesPerChannel() != 128) {
        std::puts("FAIL: file metadata mismatch");
        return false;
    }
    if (!nearly_equal(reader.samples[0][64], writer.samples[0][64], 0.001)) {
        std::puts("FAIL: file sample mismatch");
        return false;
    }
    return true;
}

}  // namespace

int main() {
    if (!validate_round_trip(AudioFileFormat::Wave)) {
        return 1;
    }
    if (!validate_round_trip(AudioFileFormat::Aiff)) {
        return 1;
    }
    if (!validate_file_round_trip()) {
        return 1;
    }

    std::puts("PASS: adamstark-audiofile consumer round-trip checks passed");
    return 0;
}
