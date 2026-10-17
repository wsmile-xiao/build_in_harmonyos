#include <ZXing/BarcodeFormat.h>
#include <ZXing/BitMatrix.h>
#include <ZXing/MultiFormatWriter.h>
#include <ZXing/ReadBarcode.h>
#include <ZXing/Version.h>

#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool condition, const char* message)
{
    if (condition) {
        std::cout << "[ok] " << message << '\n';
    } else {
        std::cerr << "[FAIL] " << message << '\n';
        ++failures;
    }
}

} // namespace

int main()
{
    constexpr int width = 160;
    constexpr int height = 160;
    const std::string payload = "zxing-cpp/2.3.0";

    ZXing::MultiFormatWriter writer(ZXing::BarcodeFormat::QRCode);
    const auto matrix = writer.encode(payload, width, height);
    check(matrix.width() == width && matrix.height() == height,
          "MultiFormatWriter returns the requested QR dimensions");

    int black_pixels = 0;
    std::vector<std::uint8_t> image(static_cast<std::size_t>(width * height));
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            const bool black = matrix.get(x, y);
            black_pixels += black ? 1 : 0;
            image[static_cast<std::size_t>(y * width + x)] = black ? 0 : 255;
        }
    }
    check(black_pixels > 0 && black_pixels < width * height,
          "QR output contains both dark and light pixels");

    const ZXing::ImageView view(
        image.data(), width, height, ZXing::ImageFormat::Lum);
    const auto result = ZXing::ReadBarcode(
        view,
        ZXing::ReaderOptions()
            .setFormats(ZXing::BarcodeFormat::QRCode)
            .setTryRotate(false)
            .setTryInvert(false)
            .setTryDownscale(false));
    check(result.isValid(), "ReadBarcode decodes the generated QR image");
    check(result.text() == payload, "decoded text matches the encoded payload");
    check(result.format() == ZXing::BarcodeFormat::QRCode,
          "decoded format is QRCode");
    check(std::string(ZXING_VERSION_STR) == "2.3.0",
          "installed public version is 2.3.0");

    if (failures != 0) {
        std::cerr << "zxing-cpp consumer test: " << failures
                  << " assertion(s) failed\n";
        return 1;
    }
    std::cout << "zxing-cpp consumer test: all assertions passed\n";
    return 0;
}
