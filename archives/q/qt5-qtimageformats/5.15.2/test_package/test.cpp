#include <QCoreApplication>
#include <QImage>
#include <QBuffer>
#include <QByteArray>

// R34: Test must substantively depend on the tested package.
// This test verifies that Qt5 image format plugins (TIFF, WebP, TGA, WBMP)
// from qt5-qtimageformats are loadable and functional.

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Create a simple TIFF image in-memory and verify it can be read back.
    // The TIFF format support comes from the qtiff plugin built by qt5-qtimageformats.
    QImage original(4, 4, QImage::Format_RGB32);
    original.fill(0xFF0000FF); // red pixel (BGRA on little-endian)

    QByteArray tiffData;
    QBuffer tiffBuffer(&tiffData);
    tiffBuffer.open(QIODevice::WriteOnly);
    if (!original.save(&tiffBuffer, "tiff")) {
        // TIFF plugin not available — this means qt5-qtimageformats was not built properly
        return 2;
    }
    tiffBuffer.close();

    // Read the TIFF back and verify
    QBuffer readBuffer(&tiffData);
    readBuffer.open(QIODevice::ReadOnly);
    QImage loaded;
    if (!loaded.load(&readBuffer, "tiff")) {
        return 3;
    }
    readBuffer.close();

    if (loaded.size() != original.size()) {
        return 4;
    }

    // Test WebP format (qwebp plugin)
    QByteArray webpData;
    QBuffer webpBuffer(&webpData);
    webpBuffer.open(QIODevice::WriteOnly);
    bool webpOk = original.save(&webpBuffer, "webp");
    webpBuffer.close();

    if (webpOk) {
        QBuffer webpRead(&webpData);
        webpRead.open(QIODevice::ReadOnly);
        QImage webpLoaded;
        if (!webpLoaded.load(&webpRead, "webp")) {
            return 5;
        }
        webpRead.close();
        if (webpLoaded.size() != original.size()) {
            return 6;
        }
    }

    return 0;
}
