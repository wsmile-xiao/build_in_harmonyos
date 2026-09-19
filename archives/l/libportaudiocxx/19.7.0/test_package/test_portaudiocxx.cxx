// Consumer test for libportaudiocxx (PortAudioCpp) 19.7.0.
//
// Exercises the public C++ binding API without requiring audio hardware:
//   - System lifecycle (initialize / terminate)
//   - version query (must match PortAudio 19.7.0)
//   - host API and device enumeration consistency
//   - host API iterator traversal
//   - sample-size helper
//   - C++ exception path for out-of-range device index
// On HarmonyOS additionally asserts the platform-specific no-backend
// behavior (host API / device counts are 0, null device is available).
#include <portaudiocpp/PortAudioCpp.hxx>

#include <cstdio>

int main() {
    int checks = 0;

    // 1. Version must be visible before initialization.
    // PA_VERSION_INT encodes 19.7.0 as (19 << 16) | (7 << 8) | 0 = 1246976.
    if (portaudio::System::version() != 1246976) {
        std::fprintf(stderr, "unexpected PortAudio version %d\n",
                     portaudio::System::version());
        return 1;
    }
    const char *version_text = portaudio::System::versionText();
    if (version_text == nullptr || version_text[0] == '\0') {
        std::fprintf(stderr, "empty PortAudio version text\n");
        return 1;
    }
    ++checks;

    // 2. System lifecycle: initialize, then enumerate.
    portaudio::System::initialize();
    portaudio::System &sys = portaudio::System::instance();

    int host_api_count = sys.hostApiCount();
    int device_count = sys.deviceCount();
    if (host_api_count < 0 || device_count < 0) {
        std::fprintf(stderr, "PortAudio API consistency check failed\n");
        portaudio::System::terminate();
        return 1;
    }
    ++checks;

    // 3. Host API iterator traversal must match the reported count.
    int iterated = 0;
    for (portaudio::System::HostApiIterator it = sys.hostApisBegin();
         it != sys.hostApisEnd(); ++it) {
        ++iterated;
    }
    if (iterated != host_api_count) {
        std::fprintf(stderr, "host API iterator count mismatch\n");
        portaudio::System::terminate();
        return 1;
    }
    ++checks;

    // 4. Sample-size helper.
    if (sys.sizeOfSample(paFloat32) != 4) {
        std::fprintf(stderr, "sizeOfSample(paFloat32) failed\n");
        portaudio::System::terminate();
        return 1;
    }
    ++checks;

    // 5. Out-of-range device index must throw a C++ exception, not crash.
    bool threw = false;
    try {
        sys.deviceByIndex(device_count);
    } catch (const portaudio::PaException &) {
        threw = true;
    }
    if (!threw) {
        std::fprintf(stderr, "deviceByIndex(out-of-range) did not throw\n");
        portaudio::System::terminate();
        return 1;
    }
    ++checks;

#if defined(__OHOS__)
    // ===== HarmonyOS platform-specific assertions =====
    // The OHOS portaudio package disables every audio backend
    // (ALSA/JACK/OSS/ASIHPI/CoreAudio), so the host API and device counts
    // must be 0 while lifecycle, enumeration and exception paths still work.
    if (host_api_count != 0 || device_count != 0) {
        std::fprintf(stderr,
                     "OHOS: host_apis=%d devices=%d (expected 0)\n",
                     host_api_count, device_count);
        portaudio::System::terminate();
        return 1;
    }
    // The null-device abstraction must be usable with no devices at all.
    if (portaudio::System::nullDevice().index() != -1) {
        std::fprintf(stderr, "OHOS: null device index mismatch\n");
        portaudio::System::terminate();
        return 1;
    }
    ++checks;
#endif

    // 6. Terminate.
    portaudio::System::terminate();
    ++checks;

    std::printf("PASS PortAudioCpp %s host_apis=%d devices=%d checks=%d\n",
                version_text, host_api_count, device_count, checks);
    return 0;
}
