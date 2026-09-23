/*
    Consumer test for libkexiv2 26.04.0 on HarmonyOS PC.

    The test writes its own JPEG fixture with Qt, then drives the public
    KExiv2 API (EXIF / IPTC / XMP read-modify-write round trips) on it, so the
    tested package does real metadata work (R34). No external fixture is
    required and the exit code is non-zero as soon as one check fails.
*/
#include <QColor>
#include <QDateTime>
#include <QImage>
#include <QString>
#include <QStringList>

#include <kexiv2.h>

#include <cstdio>

using KExiv2Iface::KExiv2;

static int g_checks = 0;
static int g_failures = 0;

static void check(bool condition, const char *what)
{
    ++g_checks;
    if (condition) {
        std::printf("ok   - %s\n", what);
    } else {
        ++g_failures;
        std::printf("FAIL - %s\n", what);
    }
}

int main(int argc, char **argv)
{
    const QString workDir = (argc > 1) ? QString::fromLocal8Bit(argv[1]) : QStringLiteral(".");
    const QString imagePath = workDir + QStringLiteral("/kexiv2-consumer.jpg");

    // (1) Fixture: a JPEG written through QtGui's JPEG handler.
    QImage image(16, 16, QImage::Format_RGB32);
    image.fill(QColor(32, 160, 96));
    check(image.save(imagePath, "JPEG", 85), "QImage::save() wrote the JPEG fixture");

    // (2) Static library identity / capability probing through Exiv2.
    const QString kexiv2Version = KExiv2::version();
    const QString exiv2Version = KExiv2::Exiv2Version();
    std::printf("     libkexiv2 version: %s\n", qPrintable(kexiv2Version));
    std::printf("     libexiv2 version:  %s\n", qPrintable(exiv2Version));
    check(!kexiv2Version.isEmpty(), "KExiv2::version() reports the libkexiv2 version");
    check(!exiv2Version.isEmpty(), "KExiv2::Exiv2Version() reports the linked exiv2 version");
    check(KExiv2::supportXmp(), "KExiv2::supportXmp() is enabled");
    check(KExiv2::supportMetadataWritting(QStringLiteral("image/jpeg")),
          "KExiv2::supportMetadataWritting(image/jpeg) is enabled");
    check(KExiv2::canWriteExif(imagePath), "KExiv2::canWriteExif() on the fixture");

    // (3) The Exiv2 tag registries are reachable through the wrapper.
    {
        KExiv2 meta;
        check(meta.getStdExifTagsList().size() > 100, "getStdExifTagsList() exposes the Exiv2 registry");
        check(meta.getMakernoteTagsList().size() > 50, "getMakernoteTagsList() exposes the makernote registry");
        check(meta.getIptcTagsList().size() > 50, "getIptcTagsList() exposes the IPTC registry");
    }

    // (4) EXIF write/read round trip.
    {
        KExiv2 meta(imagePath);
        check(meta.load(imagePath), "KExiv2::load() on the fixture");
        check(meta.setExifTagString("Exif.Image.Artist", QStringLiteral("OpenHarmony PC")),
              "setExifTagString(Exif.Image.Artist)");
        check(meta.setExifTagString("Exif.Image.ImageDescription", QStringLiteral("libkexiv2 consumer test")),
              "setExifTagString(Exif.Image.ImageDescription)");
        check(meta.applyChanges(), "applyChanges() persisted the EXIF tags");
    }
    {
        KExiv2 reloaded;
        reloaded.load(imagePath);
        check(reloaded.getExifTagString("Exif.Image.Artist") == QStringLiteral("OpenHarmony PC"),
              "Exif.Image.Artist read back after reload");
        check(reloaded.getExifTagString("Exif.Image.ImageDescription") == QStringLiteral("libkexiv2 consumer test"),
              "Exif.Image.ImageDescription read back after reload");
        check(reloaded.hasExif(), "hasExif() after the EXIF round trip");
    }

    // (5) Date/time round trip through the convenience API.
    const QDateTime written = QDateTime::fromString(QStringLiteral("2026-09-14T08:30:00"),
                                                   Qt::ISODate);
    {
        KExiv2 meta(imagePath);
        check(meta.setImageDateTime(written), "setImageDateTime()");
        check(meta.applyChanges(), "applyChanges() persisted the date/time");
    }
    {
        KExiv2 reloaded;
        reloaded.load(imagePath);
        const QDateTime read = reloaded.getImageDateTime();
        std::printf("     written=%s read=%s\n",
                    qPrintable(written.toString(QStringLiteral("yyyy-MM-dd HH:mm:ss"))),
                    qPrintable(read.toString(QStringLiteral("yyyy-MM-dd HH:mm:ss"))));
        check(read.toString(QStringLiteral("yyyy-MM-dd HH:mm:ss"))
                  == written.toString(QStringLiteral("yyyy-MM-dd HH:mm:ss")),
              "getImageDateTime() read back the written timestamp");
    }

    // (6) XMP write/read round trip (EXIV2_ENABLE_XMP is on in the package).
    {
        KExiv2 meta(imagePath);
        check(meta.setXmpTagString("Xmp.xmp.Label", QStringLiteral("openharmony-pc")),
              "setXmpTagString(Xmp.xmp.Label)");
        check(meta.applyChanges(), "applyChanges() persisted the XMP packet");
    }
    {
        KExiv2 reloaded;
        reloaded.load(imagePath);
        check(reloaded.getXmpTagString("Xmp.xmp.Label") == QStringLiteral("openharmony-pc"),
              "Xmp.xmp.Label read back after reload");
    }

    // (7) Tag removal is reflected in the reloaded metadata.
    {
        KExiv2 meta(imagePath);
        meta.removeExifTag("Exif.Image.ImageDescription");
        check(meta.applyChanges(), "applyChanges() after removeExifTag()");
    }
    {
        KExiv2 reloaded;
        reloaded.load(imagePath);
        check(reloaded.getExifTagString("Exif.Image.ImageDescription").isEmpty(),
              "removed EXIF tag is gone after reload");
    }

    std::printf("checks=%d failures=%d\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
