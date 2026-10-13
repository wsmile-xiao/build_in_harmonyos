#include <liquidsfz.hh>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/utsname.h>
#include <vector>

namespace fs = std::filesystem;

static void write_le(std::ofstream& out, unsigned value, unsigned bytes) {
    for (unsigned i = 0; i < bytes; ++i)
        out.put(static_cast<char>(value >> (8 * i)));
}

int main() {
    struct utsname platform {};
    if (uname(&platform) != 0 || std::string(platform.sysname) != "HarmonyOS" ||
        std::string(platform.machine) != "aarch64") {
        std::cerr << "Expected HarmonyOS aarch64 runtime\n";
        return 1;
    }

    // HMDFS refuses file creation under a mkdtemp directory's default 0700.
    // Exercise the same group-access workaround used by the OHOS recipe.
    const auto parent = fs::current_path();
    if (parent.string().rfind("/storage/Users/", 0) != 0) {
        std::cerr << "Expected test working directory under HarmonyOS user storage\n";
        return 2;
    }
    const auto pattern = (parent / "liquidsfz-ohos-XXXXXX").string();
    std::vector<char> buffer(pattern.begin(), pattern.end());
    buffer.push_back('\0');
    const auto directory = mkdtemp(buffer.data());
    if (!directory) return 3;
    const fs::path root(directory);
    struct Cleanup {
        fs::path path;
        ~Cleanup() {
            std::error_code error;
            fs::remove_all(path, error);
        }
    } cleanup {root};

    try {
        fs::permissions(root, fs::perms::owner_all | fs::perms::group_read |
                              fs::perms::group_exec, fs::perm_options::replace);
        const auto fixture = root / u8"鸿蒙 SFZ 样本";
        fs::create_directory(fixture);
        const auto wav_path = fixture / u8"音频 sample.wav";
        const auto sfz_path = fixture / u8"乐器 test.sfz";
        constexpr unsigned frames = 4096;
        {
            std::ofstream wav(wav_path, std::ios::binary);
            wav.write("RIFF", 4); write_le(wav, 36 + frames * 2, 4);
            wav.write("WAVEfmt ", 8); write_le(wav, 16, 4);
            write_le(wav, 1, 2); write_le(wav, 1, 2);
            write_le(wav, 48000, 4); write_le(wav, 96000, 4);
            write_le(wav, 2, 2); write_le(wav, 16, 2);
            wav.write("data", 4); write_le(wav, frames * 2, 4);
            for (unsigned i = 0; i < frames; ++i)
                write_le(wav, (i % 64 < 32) ? 10000 : static_cast<unsigned>(-10000), 2);
            wav.close();
            if (!wav) return 4;
        }
        {
            std::ofstream sfz(sfz_path);
            sfz << u8"<region> sample=音频 sample.wav key=60\n";
            sfz.close();
            if (!sfz) return 5;
        }
        LiquidSFZ::Synth synth;
        synth.set_sample_rate(48000);
        synth.set_live_mode(false);
        // Current directory differs from the SFZ directory: samples must be
        // resolved relative to the SFZ, including UTF-8 and spaces on HMDFS.
        if (!synth.load(sfz_path.string())) return 6;
        synth.add_event_note_on(0, 0, 60, 100);
        std::array<float, 1024> left {}, right {};
        float* outputs[2] = {left.data(), right.data()};
        synth.process(outputs, left.size());
        float peak = 0;
        for (unsigned i = 0; i < left.size(); ++i) {
            if (!std::isfinite(left[i]) || !std::isfinite(right[i])) return 7;
            peak = std::max(peak, std::max(std::fabs(left[i]), std::fabs(right[i])));
        }
        if (peak < 0.001f) return 8;
        std::cout << "OHOS-specific test PASS: HarmonyOS aarch64, signed execution, "
                     "HMDFS temporary directory, UTF-8/spaced SFZ and relative sample; peak="
                  << peak << '\n';
    } catch (const std::exception& error) {
        std::cerr << "OHOS storage test failed: " << error.what() << '\n';
        return 9;
    }
    return 0;
}
