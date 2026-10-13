#include <liquidsfz.hh>

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>

static void le16(std::ofstream& out, unsigned value) {
    out.put(static_cast<char>(value));
    out.put(static_cast<char>(value >> 8));
}

static void le32(std::ofstream& out, unsigned value) {
    le16(out, value);
    le16(out, value >> 16);
}

int main() {
    constexpr unsigned frames = 4096;
    {
        std::ofstream wav("test.wav", std::ios::binary);
        wav.write("RIFF", 4); le32(wav, 36 + frames * 2);
        wav.write("WAVEfmt ", 8); le32(wav, 16);
        le16(wav, 1); le16(wav, 1); le32(wav, 48000);
        le32(wav, 96000); le16(wav, 2); le16(wav, 16);
        wav.write("data", 4); le32(wav, frames * 2);
        for (unsigned i = 0; i < frames; ++i)
            le16(wav, (i % 64 < 32) ? 10000 : static_cast<unsigned>(-10000));
        if (!wav) return 1;
    }
    { std::ofstream sfz("test.sfz"); sfz << "<region> sample=test.wav key=60\n"; }

    LiquidSFZ::Synth synth;
    synth.set_sample_rate(48000);
    synth.set_live_mode(false);
    if (!synth.load("test.sfz")) return 2;
    synth.add_event_note_on(0, 0, 60, 100);
    std::array<float, 1024> left{}, right{};
    float* outputs[2] = {left.data(), right.data()};
    synth.process(outputs, left.size());
    const auto peak = *std::max_element(left.begin(), left.end());
    if (peak < 0.001f) return 3;
    std::cout << "liquidsfz SFZ playback: peak=" << peak << '\n';
    return 0;
}
