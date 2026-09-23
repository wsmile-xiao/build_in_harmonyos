// test_package consumer test for phonon4qt6 4.12.0
//
// This test actually calls the Phonon public API (R34): it queries the
// runtime version string via Phonon::phononVersion() and enumerates
// backend capabilities (mime types + audio output devices). This proves
// the packaged libphonon4qt6.so is linkable and loadable at runtime.
#include <phonon/phononnamespace.h>
#include <phonon/backendcapabilities.h>
#include <QString>
#include <QStringList>
#include <cstdio>

int main()
{
    // 1) Static API: library version string (resolved from libphonon4qt6.so)
    const char *ver = Phonon::phononVersion();
    std::printf("Phonon version: %s\n", ver != nullptr ? ver : "()");
    if (ver == nullptr || ver[0] == '\0') {
        std::printf("FAIL: phononVersion() returned empty string\n");
        return 1;
    }

    // 2) Runtime API: backend capability enumeration. Without a backend
    //    plugin installed these return empty lists, but the calls must not
    //    crash — proving the shared library loads and dispatches correctly.
    const QStringList mimeTypes = Phonon::BackendCapabilities::availableMimeTypes();
    std::printf("Backend mime types: %lld\n", static_cast<long long>(mimeTypes.size()));
    for (const QString &m : mimeTypes) {
        std::printf("  mime: %s\n", m.toUtf8().constData());
    }

    const auto audioOutputs =
        Phonon::BackendCapabilities::availableAudioOutputDevices();
    std::printf("Audio output devices: %lld\n",
                static_cast<long long>(audioOutputs.size()));

    std::printf("test_phonon4qt6: PASS\n");
    return 0;
}