// libkdegames 26.04.0.1 OHOS-specific consumer test.
//
// Covers the platform-specific behavior of this adaptation on HarmonyOS PC
// (aarch64):
//   1. The openal audio backend wiring is active (KGAUDIO_BACKEND=openal is
//      hard-wired upstream; knowledge E285: openal-soft on OHOS keeps only
//      the built-in Null backend because there is no real audio device).
//   2. KGameSound can load a WAV through the bundled libsndfile and start
//      playback through openal-soft with the Null backend on a headless
//      OHOS device (no ALSA/PulseAudio).
//   3. KGameHighscore roundtrips through a user-writable config location
//      (HIGHSCORE_DIRECTORY defaults to empty, so scores live under HOME;
//      exercises musl/QStandardPaths writable-path behavior).
#include <KGameHighscore>
#include <KGameSound>
#include <QCoreApplication>
#include <QDataStream>
#include <QFile>
#include <QIODevice>
#include <QTemporaryDir>
#include <cstdio>
#include <cstring>

#include <libkdegames_capabilities.h>

#ifndef KGAUDIO_BACKEND_OPENAL
#error "KGAUDIO_BACKEND_OPENAL must be defined: openal backend wiring is required on OHOS"
#endif

namespace {

// Write a minimal 16-bit PCM mono 8 kHz WAV (0.25 s of a ramp waveform).
bool writeTestWav(const QString &path) {
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        return false;
    }
    const quint32 sampleRate = 8000;
    const quint32 numSamples = sampleRate / 4;
    const quint16 channels = 1;
    const quint16 bitsPerSample = 16;
    const quint32 byteRate = sampleRate * channels * bitsPerSample / 8;
    const quint16 blockAlign = channels * bitsPerSample / 8;
    const quint32 dataSize = numSamples * blockAlign;

    QDataStream out(&file);
    out.setByteOrder(QDataStream::LittleEndian);
    out.writeRawData("RIFF", 4);
    out << quint32(36 + dataSize);
    out.writeRawData("WAVE", 4);
    out.writeRawData("fmt ", 4);
    out << quint32(16) << quint16(1) << channels << sampleRate << byteRate
        << blockAlign << bitsPerSample;
    out.writeRawData("data", 4);
    out << dataSize;
    for (quint32 i = 0; i < numSamples; ++i) {
        out << qint16((i % 64 - 32) * 300);
    }
    return true;
}

} // namespace

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    int failures = 0;

    // 1. Audio backend wiring: the capability header must record the openal
    //    backend (compile-time guard above + runtime string check).
    if (std::strcmp(KGAUDIO_BACKEND, "openal") != 0) {
        std::printf("FAIL: KGAUDIO_BACKEND is \"%s\", expected \"openal\"\n",
                    KGAUDIO_BACKEND);
        ++failures;
    } else {
        std::printf("PASS: KGAUDIO_BACKEND=openal wired on OHOS\n");
    }

    // 2. openal-soft playback on a device without real audio hardware
    //    (Null backend): load a generated WAV via libsndfile and start it.
    QTemporaryDir tmpDir;
    if (!tmpDir.isValid()) {
        std::printf("FAIL: cannot create temporary directory\n");
        return 1;
    }
    const QString wav = tmpDir.filePath("ohos-smoke.wav");
    if (!writeTestWav(wav)) {
        std::printf("FAIL: cannot write test WAV\n");
        return 1;
    }
    KGameSound sound(wav);
    if (!sound.isValid()) {
        std::printf("FAIL: KGameSound could not load the test WAV\n");
        ++failures;
    } else {
        std::printf("PASS: KGameSound loaded WAV via libsndfile\n");
    }
    sound.start();
    if (sound.hasError()) {
        std::printf("FAIL: KGameSound.start() reported an error (openal Null backend)\n");
        ++failures;
    } else {
        std::printf("PASS: KGameSound.start() ok on openal Null backend\n");
    }

    // 3. Local highscore roundtrip (HOME-based storage, empty
    //    HIGHSCORE_DIRECTORY on OHOS).
    KGameHighscore highscore(true);
    highscore.writeEntry(1, "name", QStringLiteral("ohos-smoke"));
    highscore.writeEntry(1, "score", 42);
    const QString name = highscore.readEntry(1, "name");
    const int score = highscore.readEntry(1, "score", 0).toInt();
    if (name != QLatin1String("ohos-smoke") || score != 42) {
        std::printf("FAIL: highscore roundtrip mismatch (name=%s score=%d)\n",
                    qPrintable(name), score);
        ++failures;
    } else {
        std::printf("PASS: KGameHighscore local roundtrip ok\n");
    }

    if (failures != 0) {
        std::printf("FAIL: test_ohos had %d failure(s)\n", failures);
        return 1;
    }
    std::printf("PASS: test_ohos all OHOS assertions ok\n");
    return 0;
}
