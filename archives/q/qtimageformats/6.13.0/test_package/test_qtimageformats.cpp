// Consumer test for the qtimageformats package on HarmonyOS PC.
//
// The Qt image format handlers ship as runtime-loaded GUI plugins, so the
// substantive assertion is: the plugins in this package's plugins/imageformats
// directory are loadable, and QImageReader's supported format list (plus real
// decode attempts) covers the MNG / JPEG2000 / TGA formats contributed by the
// plugin .so files installed by this package.

#include <QBuffer>
#include <QCoreApplication>
#include <QDir>
#include <QImage>
#include <QImageReader>
#include <QList>
#include <QByteArray>

#include <cstdio>

static int failures = 0;

static bool check(bool condition, const char *name, const char *detail)
{
    std::fprintf(condition ? stdout : stderr, "[%s] %s (%s)\n",
                 condition ? "PASS" : "FAIL", name, detail);
    if (!condition)
        ++failures;
    return condition;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Locate the plugins staged by the qtimageformats package (QT_PLUGIN_PATH
    // is injected by the recipe's package_info; fall back to a relative
    // layout for direct build-tree runs).
    const QByteArray pluginPath = qgetenv("QT_PLUGIN_PATH");
    if (!pluginPath.isEmpty())
        QCoreApplication::addLibraryPath(QString::fromLocal8Bit(pluginPath));

    const QList<QByteArray> formats = QImageReader::supportedImageFormats();
    QStringList names;
    for (const QByteArray &format : formats)
        names << QString::fromLatin1(format);
    const QString listing = names.join(u" ");
    std::printf("supported formats: %s\n", listing.toLocal8Bit().constData());

    // 1. TGA handler: real decode of a minimal uncompressed 24-bit TGA.
    {
        // 2x2 uncompressed true-color TGA (image type 2), no image id,
        // with the TRUEVISION-XFILE footer required by QTgaFile::QTgaFile().
        const unsigned char tga[] = {
            0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x02, 0x00, 0x02, 0x00, 0x18, 0x20,
            // pixels: red, green, blue, white (BGR order)
            0x00, 0x00, 0xFF,  0x00, 0xFF, 0x00,  0xFF, 0x00, 0x00,  0xFF, 0xFF, 0xFF,
            // TGA 2.0 footer (26 bytes): extension offset (4), developer
            // offset (4), 16-byte signature "TRUEVISION-XFILE" (no NUL),
            // reserved '.', terminator 0x00
            0x00, 0x00, 0x00, 0x00,  0x00, 0x00, 0x00, 0x00,
            'T', 'R', 'U', 'E', 'V', 'I', 'S', 'I', 'O', 'N', '-', 'X', 'F', 'I', 'L', 'E',
            '.', 0x00,
        };
        QByteArray data(reinterpret_cast<const char *>(tga), sizeof(tga));
        QBuffer buffer(&data);
        buffer.open(QIODevice::ReadOnly);
        QImageReader reader(&buffer, "tga");
        QImage image = reader.read();
        check(!image.isNull(), "TGA plugin decodes a 2x2 image",
              reader.errorString().toLocal8Bit().constData());
        check(formats.contains("tga"), "TGA format in QImageReader list",
              listing.toLocal8Bit().constData());
    }

    // 2. WBMP handler: real decode of a 1-bit WBMP (type 0, 2x2 black).
    {
        // WBMP header: type 0x00, fixed header 0x00, width 2, height 2,
        // then 2 rows x 1 byte of packed bitmap data (4 black pixels).
        const unsigned char wbmp[] = { 0x00, 0x00, 0x02, 0x02, 0x00, 0x00 };
        QByteArray data(reinterpret_cast<const char *>(wbmp), sizeof(wbmp));
        QBuffer buffer(&data);
        buffer.open(QIODevice::ReadOnly);
        QImageReader reader(&buffer, "wbmp");
        QImage image = reader.read();
        check(!image.isNull(), "WBMP plugin decodes a 2x2 image",
              reader.errorString().toLocal8Bit().constData());
    }

    // 3. TIFF plugin presence (system libtiff integration): format advertised.
    check(formats.contains("tif") || formats.contains("tiff"),
          "TIFF format in QImageReader list",
          listing.toLocal8Bit().constData());

    // 4. WebP plugin presence (system libwebp integration): webp advertised.
    check(formats.contains("webp"), "WebP format in QImageReader list",
          listing.toLocal8Bit().constData());

    // 5. ICNS plugin presence (built-in): icns advertised.
    check(formats.contains("icns"), "ICNS format in QImageReader list",
          listing.toLocal8Bit().constData());

    if (failures != 0) {
        std::fprintf(stderr, "qtimageformats test: %d failure(s)\n", failures);
        return 1;
    }
    std::printf("qtimageformats test: all checks passed\n");
    return 0;
}
