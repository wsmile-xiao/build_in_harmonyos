// test_package consumer test for libkcompactdisc 25.12.1
//
// This test actually calls the KCompactDisc public API (R34): it queries
// the static audio-system list, the CD-ROM device enumeration (Solid-backed)
// and the URL<->device mapping. On HarmonyOS PC there is no CD-ROM hardware
// and no optical drive is enumerated, so the device lists are expected to be
// empty; the calls must not crash, which proves the packaged
// libKCompactDisc6.so is linkable and loadable at runtime.
#include <kcompactdisc.h>

#include <QUrl>
#include <QString>
#include <QStringList>
#include <cstdio>

int main()
{
    // 1) Static API: compile-time audio system list. "phonon" is always
    //    present; "alsa" appears when HAVE_ALSA is enabled (alsa-lib).
    const QStringList audioSystems = KCompactDisc::audioSystems();
    std::printf("Audio systems: %lld\n",
                static_cast<long long>(audioSystems.size()));
    for (const QString &s : audioSystems) {
        std::printf("  audio system: %s\n", s.toUtf8().constData());
    }
    if (audioSystems.isEmpty()) {
        std::printf("FAIL: audioSystems() must at least report \"phonon\"\n");
        return 1;
    }

    // 2) Static API: CD-ROM device enumeration backed by Solid. No optical
    //    drive on the target platform -> empty list, but must not crash.
    const QStringList devices = KCompactDisc::cdromDeviceNames();
    std::printf("CD-ROM devices: %lld\n",
                static_cast<long long>(devices.size()));
    for (const QString &d : devices) {
        std::printf("  device: %s\n", d.toUtf8().constData());
    }
    const QString defaultDevice = KCompactDisc::defaultCdromDeviceName();
    std::printf("Default CD-ROM device: '%s'\n",
                defaultDevice.toUtf8().constData());

    // 3) Static API: URL -> device mapping (pure string logic; "file"
    //    scheme maps to the local device path).
    const QString device = KCompactDisc::urlToDevice(QUrl("file:///dev/sr0"));
    std::printf("urlToDevice(file:///dev/sr0) = '%s'\n",
                device.toUtf8().constData());
    if (device.isEmpty()) {
        std::printf("FAIL: urlToDevice() returned an empty string\n");
        return 1;
    }

    std::printf("test_kcompactdisc: PASS\n");
    return 0;
}
