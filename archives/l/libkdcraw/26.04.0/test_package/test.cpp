// libkdcraw 26.04.0 consumer test (R34: exercises real API).
// Verifies the installed KDcrawQt6 library and headers: KDcraw::version(),
// librawVersion(), rawFilesList(), rawFilesVersion(), supportedCamera(),
// rawFiles(), and the RawDecodingSettings / DcrawInfoContainer value types,
// plus loadEmbeddedPreview()/loadRawPreview()/rawFileIdentify() rejection
// behavior on a nonexistent path (LibRaw must be linked and functional for
// these to even run).
#include <KDCRAW/KDcraw>
#include <KDCRAW/RawDecodingSettings>
#include <KDCRAW/DcrawInfoContainer>
#include <QImage>
#include <QString>
#include <QStringList>
#include <cstdio>

using namespace KDcrawIface;

int main(int, char **) {
    // --- KDcraw static metadata API (LibRaw-backed) ---
    const QString kdcrawVersion = KDcraw::version();
    if (kdcrawVersion.isEmpty()) {
        std::fprintf(stderr, "FAIL: KDcraw::version() empty\n");
        return 1;
    }
    const QString librawVersion = KDcraw::librawVersion();
    if (librawVersion.isEmpty() || !librawVersion.startsWith(QStringLiteral("0."))) {
        std::fprintf(stderr, "FAIL: KDcraw::librawVersion() unexpected: %s\n",
                     librawVersion.toLatin1().constData());
        return 1;
    }
    // libraw 0.22.1 must be reported as 0.22 at minimum.
    const QStringList rawParts = librawVersion.split(QLatin1Char('.'));
    const int minor = rawParts.size() > 1 ? rawParts.at(1).toInt() : 0;
    if (rawParts.at(0).toInt() != 0 || minor < 22) {
        std::fprintf(stderr, "FAIL: KDcraw::librawVersion() too old: %s\n",
                     librawVersion.toLatin1().constData());
        return 1;
    }

    const QStringList rawFiles = KDcraw::rawFilesList();
    if (rawFiles.isEmpty()) {
        std::fprintf(stderr, "FAIL: KDcraw::rawFilesList() empty\n");
        return 1;
    }
    // rawFilesList() strips the "*." prefix: entries are "dng", "cr2", ...
    if (!rawFiles.contains(QLatin1String("dng"))
        || !rawFiles.contains(QLatin1String("cr2"))
        || !rawFiles.contains(QLatin1String("nef"))) {
        std::fprintf(stderr, "FAIL: KDcraw::rawFilesList() missing dng/cr2/nef\n");
        return 1;
    }
    if (KDcraw::rawFilesVersion() <= 0) {
        std::fprintf(stderr, "FAIL: KDcraw::rawFilesVersion() non-positive\n");
        return 1;
    }
    const QStringList cameras = KDcraw::supportedCamera();
    if (cameras.isEmpty()) {
        std::fprintf(stderr, "FAIL: KDcraw::supportedCamera() empty\n");
        return 1;
    }
    const char *rawFilesC = KDcraw::rawFiles();
    if (!rawFilesC || !rawFilesC[0]) {
        std::fprintf(stderr, "FAIL: KDcraw::rawFiles() empty\n");
        return 1;
    }

    // --- RawDecodingSettings value type roundtrip ---
    RawDecodingSettings settings;
    settings.sixteenBitsImage = true;
    settings.halfSizeColorImage = true;
    settings.autoBrightness = false;
    settings.customWhiteBalance = 6500;
    settings.RAWQuality = RawDecodingSettings::BILINEAR;
    if (!settings.sixteenBitsImage || !settings.halfSizeColorImage
        || settings.customWhiteBalance != 6500
        || settings.RAWQuality != RawDecodingSettings::BILINEAR) {
        std::fprintf(stderr, "FAIL: RawDecodingSettings field roundtrip failed\n");
        return 1;
    }
    RawDecodingSettings copy(settings);
    if (!(copy == settings)) {
        std::fprintf(stderr, "FAIL: RawDecodingSettings copy/compare failed\n");
        return 1;
    }

    // --- DcrawInfoContainer default state ---
    DcrawInfoContainer identify;
    if (identify.sensitivity != -1 || identify.exposureTime != -1.0) {
        std::fprintf(stderr, "FAIL: DcrawInfoContainer defaults wrong\n");
        return 1;
    }

    // --- Decode paths must cleanly reject nonexistent files ---
    // rawFileIdentify goes through LibRaw open+identify internally.
    QImage image;
    DcrawInfoContainer info;
    if (KDcraw::rawFileIdentify(info, QStringLiteral("/nonexistent/no-such.raw"))) {
        std::fprintf(stderr, "FAIL: rawFileIdentify accepted a nonexistent file\n");
        return 1;
    }
    if (KDcraw::loadRawPreview(image, QStringLiteral("/nonexistent/no-such.raw"))) {
        std::fprintf(stderr, "FAIL: loadRawPreview accepted a nonexistent file\n");
        return 1;
    }
    if (KDcraw::loadEmbeddedPreview(image, QStringLiteral("/nonexistent/no-such.raw"))) {
        std::fprintf(stderr, "FAIL: loadEmbeddedPreview accepted a nonexistent file\n");
        return 1;
    }
    if (KDcraw::loadHalfPreview(image, QStringLiteral("/nonexistent/no-such.raw"))) {
        std::fprintf(stderr, "FAIL: loadHalfPreview accepted a nonexistent file\n");
        return 1;
    }

#ifdef __OHOS__
    std::printf("OHOS-specific check: compiled with __OHOS__ on HarmonyOS PC (aarch64)\n");
    std::printf("KDcraw version %s, LibRaw %s, %zu RAW extensions, %zu cameras\n",
                kdcrawVersion.toLatin1().constData(),
                librawVersion.toLatin1().constData(),
                static_cast<size_t>(rawFiles.size()),
                static_cast<size_t>(cameras.size()));
#else
    std::printf("KDcraw version %s, LibRaw %s, %zu RAW extensions, %zu cameras\n",
                kdcrawVersion.toLatin1().constData(),
                librawVersion.toLatin1().constData(),
                static_cast<size_t>(rawFiles.size()),
                static_cast<size_t>(cameras.size()));
#endif

    std::printf("test_libkdcraw: ALL CHECKS PASSED\n");
    return 0;
}
