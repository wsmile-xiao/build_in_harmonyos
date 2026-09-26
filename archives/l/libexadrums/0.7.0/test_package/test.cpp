// OHOS consumer smoke test for libexadrums 0.7.0.
// Validates: library version string, ALSA stub device enumeration,
// and ALSA parameters XML round-trip (exercises tinyxml2 + stub header).
//
// NOTE: a custom CHECK macro is used instead of <cassert>.  The OHOS CI
// profile builds with build_type=Release, whose default flags include
// -DNDEBUG; that makes <cassert>'s assert() preprocess away to nothing, which
// would silently turn this into a no-op test that always exits 0.  CHECK is
// always compiled in (Debug and Release), prints file/line on failure, and
// drives the process exit code.  This mirrors the convention used by other
// packages in this repo (e.g. libtnt, far2l, game-music-emu).
#include <libexadrums/Api/eXaDrums.h>
#include <libexadrums/Sound/Alsa/Alsa.h>
#include <libexadrums/Sound/Alsa/AlsaParameters.h>

#include <iostream>
#include <string>

static int g_failures = 0;

#define CHECK(cond)                                                           \
    do {                                                                      \
        if (!(cond)) {                                                        \
            std::cerr << "CHECK FAILED @" << __LINE__ << ": " #cond "\n";     \
            ++g_failures;                                                     \
        }                                                                     \
    } while (0)

int main()
{
    // 1) Library version string (static API, no device needed).
    const std::string ver = eXaDrumsApi::eXaDrums::GetVersion();
    std::cout << "libexadrums version = " << ver << std::endl;
    CHECK(ver == "0.7.0");

    // 2) ALSA stub exposes at least one playback device.  This proves the
    //    bundled libasound.a links into libexadrums and GetDevices() works.
    auto devices = Sound::Alsa::GetDevices(SND_PCM_STREAM_PLAYBACK);
    std::cout << "ALSA playback devices = " << devices.size() << std::endl;
    CHECK(!devices.empty());

    // 3) ALSA parameters XML round-trip (SaveAlsaParameters / LoadAlsaParameters
    //    go through tinyxml2; validates the dependency + stub header).
    Sound::AlsaParams p;
    p.device = "default";
    p.capture = false;
    p.format = SND_PCM_FORMAT_S16_LE;
    p.sampleRate = 44100;
    p.nChannels = 2;
    p.bufferTime = 500000;
    p.periodTime = 100000;
    p.access = SND_PCM_ACCESS_RW_INTERLEAVED;

    Sound::AlsaParameters::SaveAlsaParameters("alsaConfig.xml", p);
    Sound::AlsaParams q;
    Sound::AlsaParameters::LoadAlsaParameters("alsaConfig.xml", q);
    std::cout << "round-trip device = " << q.device
              << " sampleRate = " << q.sampleRate << std::endl;
    CHECK(q.device == "default");
    CHECK(q.sampleRate == 44100);

    if (g_failures != 0)
    {
        std::cerr << g_failures << " CHECK(s) FAILED" << std::endl;
        return 1;
    }

    std::cout << "ALL libexadrums OHOS stub tests passed" << std::endl;
    return 0;
}
