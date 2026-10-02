// Consumer probe for qzxing/3.3.0 on OpenHarmony PC.
//
// 1) Decodes an independently generated QR fixture: the 29x29 module matrix
//    below (error correction M, 2-module quiet zone, payload
//    "https://atomgit.com/OpenHarmonyPCDeveloper") was produced offline with
//    python-qrcode 8.x — it is independent of the library under test and
//    needs no binary fixture in the repository.
// 2) Encodes a payload to a QR image with the packaged encoder and decodes
//    it back (encode/decode round-trip).
// 3) Checks decoder-format API state.
#include <QZXing.h>

#include <QCoreApplication>
#include <QImage>
#include <QString>

#include <cstdio>

// 33x33 cells (29 modules + 2-cell quiet zone on each side).
static const char *const kFixtureRows[] = {
    "000000000000000000000000000000000",
    "000000000000000000000000000000000",
    "001111111001100011001100111111100",
    "001000001011101111011100100000100",
    "001011101000110001000010101110100",
    "001011101000100011101110101110100",
    "001011101011000111011100101110100",
    "001000001001110111101110100000100",
    "001111111010101010101010111111100",
    "000000000000111101110010000000000",
    "001010101000101100100110001001000",
    "001110010010000000100111100100100",
    "001011101110110100101001111011100",
    "001010100111101111110010101001000",
    "001010011011110100110111100101100",
    "000000000110110111110001100100100",
    "001011001100110010001000010101100",
    "001101000100010100011110001101000",
    "001111111010101100110111100101100",
    "000110110100011101111010100110100",
    "001001101111000000111001101001100",
    "000111000001100111010011000101000",
    "001001011100101100010111111000000",
    "000000000011000111100110001011100",
    "001111111001101110000110101101100",
    "001000001000110101011010001101100",
    "001011101010001011010011111000000",
    "001011101000100000100011001011100",
    "001011101011000110110010011100100",
    "001000001000100110111110100001000",
    "001111111011000111110110001001100",
    "000000000000000000000000000000000",
    "000000000000000000000000000000000",
};
static const int kFixtureSize = 33;
static const int kFixtureScale = 4;

static int failures = 0;
static int checks = 0;

static void check(bool ok, const char *what)
{
    ++checks;
    if (ok) {
        std::printf("PASS: %s\n", what);
    } else {
        ++failures;
        std::printf("FAIL: %s\n", what);
    }
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ---- independent fixture decode ----
    QImage fixture(kFixtureSize * kFixtureScale, kFixtureSize * kFixtureScale,
                   QImage::Format_RGB32);
    for (int y = 0; y < kFixtureSize; ++y) {
        const char *row = kFixtureRows[y];
        for (int x = 0; x < kFixtureSize; ++x) {
            const QRgb color = row[x] == '1' ? 0xFF000000u : 0xFFFFFFFFu;
            for (int dy = 0; dy < kFixtureScale; ++dy)
                for (int dx = 0; dx < kFixtureScale; ++dx)
                    fixture.setPixel(x * kFixtureScale + dx, y * kFixtureScale + dy, color);
        }
    }
    // Mirror upstream's own validator (DecodeValidator.cpp uses the
    // default constructor + setDecoder + setTryHarder(true)): QZXing's
    // strict path requires spec-perfect images, while this fixture
    // carries a 2-module quiet zone and the library's own encodeData()
    // emits a 1-module border (upstream design). tryHarder is the
    // supported consumer pattern. NOTE: the QZXing(DecoderFormat)
    // constructor skips setTryHarderBehaviour(), leaving tryHarderType
    // uninitialized (device-observed garbage value 126) so
    // setTryHarder(true) alone has no effect with it — the default
    // constructor initializes both behaviours.
    QZXing fixtureDecoder;
    fixtureDecoder.setDecoder(QZXing::DecoderFormat_QR_CODE);
    fixtureDecoder.setTryHarder(true);
    const QString fixtureText = fixtureDecoder.decodeImage(fixture);
    check(fixtureDecoder.getLastDecodeOperationSucceded(),
          "independent QR fixture decoded successfully");
    check(fixtureText == QLatin1String("https://atomgit.com/OpenHarmonyPCDeveloper"),
          "independent QR fixture payload matches");

    // ---- encoder round-trip ----
    const QString payload = QStringLiteral("OpenHarmony-PC-qzxing-3.3.0");
    const QImage encoded = QZXing::encodeData(
        payload, QZXing::EncoderFormat_QR_CODE, QSize(360, 360),
        QZXing::EncodeErrorCorrectionLevel_M, true, false);
    check(!encoded.isNull() && encoded.width() > 100 && encoded.height() > 100,
          "encoder produced a non-trivial QR image");
    QZXing roundTripDecoder;
    roundTripDecoder.setDecoder(QZXing::DecoderFormat_QR_CODE);
    roundTripDecoder.setTryHarder(true);
    const QString roundTripText = roundTripDecoder.decodeImage(encoded);
    check(roundTripDecoder.getLastDecodeOperationSucceded(),
          "round-trip QR decoded successfully");
    check(roundTripText == payload,
          "round-trip payload matches encoded data");

    // ---- encoder API overload sanity ----
    const QImage defaultEncoded = QZXing::encodeData(QStringLiteral("qzxing"));
    check(!defaultEncoded.isNull() && defaultEncoded.width() >= 21,
          "encoder default-argument overload produces an image");

    // ---- decoder API state ----
    QZXing apiProbe;
    apiProbe.setDecoder(QZXing::DecoderFormat_EAN_13);
    check(apiProbe.getEnabledFormats() == QZXing::DecoderFormat_EAN_13,
          "setDecoder/getEnabledFormats round-trip");
    check(QZXing::decoderFormatToString(QZXing::DecoderFormat_QR_CODE) == QLatin1String("QR_CODE")
              && QZXing::decoderFormatToString(QZXing::DecoderFormat_EAN_13) == QLatin1String("EAN_13"),
          "decoderFormatToString maps both formats");

    std::printf("SUMMARY: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
