// kimageformats5 5.116.0 consumer test (R34: exercises real functionality).
// Loads the kimg_hdr plugin through Qt's plugin infrastructure and decodes a
// minimal valid Radiance HDR image, verifying the plugin chain end-to-end.
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QImage>
#include <QImageReader>
#include <QTemporaryDir>
#include <QTextStream>
#include <cstdio>
#include <cstring>

static QTextStream out(stdout);

static bool writeSampleHdr(const QString &path)
{
    // Minimal valid Radiance RGBE file: 1x1 pixel, flat (non-RLE) scanline.
    // Header "#?RADIANCE / FORMAT=32-bit_rle_rgbe", resolution "-Y 1 +X 1",
    // then one RGBE scanline of 4 bytes (R=G=B mantissa 0x80 => 1.0).
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly)) {
        return false;
    }
    const char header[] = "#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 1 +X 1\n";
    if (f.write(header, static_cast<qint64>(std::strlen(header)))
        != static_cast<qint64>(std::strlen(header))) {
        return false;
    }
    const unsigned char scanline[4] = {0x80, 0x80, 0x80, 0x80};
    if (f.write(reinterpret_cast<const char *>(scanline), sizeof(scanline))
        != static_cast<qint64>(sizeof(scanline))) {
        return false;
    }
    f.close();
    return true;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    // The package root is baked in through KIMAGEFORMATS5_ROOT at configure
    // time; Qt5 appends the "imageformats" subdirectory to library paths, so
    // the environment points at the package's "plugins" directory.
    QString pluginDir = QString::fromLatin1(
        qgetenv("KIMAGEFORMATS5_PLUGIN_DIR"));
    if (pluginDir.isEmpty()) {
        pluginDir = QCoreApplication::applicationDirPath()
            + QStringLiteral("/../plugins");
    }
    if (!QDir(pluginDir).exists()) {
        out << "FAIL: plugin dir missing: " << pluginDir << "\n";
        return 1;
    }
    QCoreApplication::removeLibraryPath(pluginDir);
    QCoreApplication::addLibraryPath(pluginDir);

    // The kimg_hdr plugin must be visible through the reader.
    const QList<QByteArray> formats = QImageReader::supportedImageFormats();
    if (!formats.contains("hdr")) {
        out << "FAIL: 'hdr' format not supported after loading plugins\n";
        return 1;
    }
    out << "PASS: hdr format advertised by kimageformats5 plugins\n";

    QTemporaryDir tmp;
    const QString hdrFile = tmp.path() + QStringLiteral("/sample.hdr");
    if (!writeSampleHdr(hdrFile)) {
        out << "FAIL: could not write sample hdr file\n";
        return 1;
    }

    QImageReader reader(hdrFile);
    reader.setAutoTransform(true);
    QImage image = reader.read();
    // The decode must genuinely succeed: a broken plugin (wrong Qt linkage,
    // pruned handler, broken HDR parsing) has to fail this test, not pass it.
    if (image.isNull()) {
        out << "FAIL: hdr decode failed: " << reader.errorString() << "\n";
        return 1;
    }
    if (image.width() != 1 || image.height() != 1) {
        out << "FAIL: unexpected decoded size " << image.width() << "x"
            << image.height() << " (expected 1x1)\n";
        return 1;
    }
    out << "PASS: hdr image decoded " << image.width() << "x" << image.height() << "\n";
    return 0;
}
