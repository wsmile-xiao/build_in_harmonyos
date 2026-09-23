#include <Prison/Barcode>
#include <QImage>
#include <QSizeF>
#include <QString>
#include <cstdio>
#include <optional>

int main() {
    auto barcode = Prison::Barcode::create(Prison::QRCode);
    if (!barcode) {
        std::fprintf(stderr, "FAIL: QRCode barcode unavailable\n");
        return 1;
    }

    barcode->setData(QStringLiteral("akonadi-contacts"));
    QImage image = barcode->toImage(QSizeF(128, 128));
    if (image.isNull()) {
        std::fprintf(stderr, "FAIL: QRCode image is null\n");
        return 1;
    }

    std::printf("PASS: Prison QR image %dx%d\n", image.width(), image.height());
    std::printf("PASS: Prison format %d\n", static_cast<int>(barcode->format()));
    return 0;
}
