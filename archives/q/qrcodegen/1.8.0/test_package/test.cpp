// Consumer test for qrcodegen (C++ implementation, Project Nayuki v1.8.0).
// Exercises the real library API: encodeText / encodeBinary / QrSegment
// mid-level API, and verifies QR code structural properties (version, size,
// module matrix sanity). Returns non-zero on any assertion failure.
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#include "qrcodegen.hpp"

using qrcodegen::QrCode;
using qrcodegen::QrSegment;

static int failures = 0;

static void check(bool cond, const char *what) {
    if (!cond) {
        std::fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

int main() {
    // --- Test 1: encodeText of a short numeric payload (numeric mode) ---
    QrCode qr0 = QrCode::encodeText("31728", QrCode::Ecc::MEDIUM);
    check(qr0.getVersion() >= 1 && qr0.getVersion() <= 40, "version in [1,40]");
    check(qr0.getSize() == qr0.getVersion() * 4 + 17, "size == version*4+17");

    // --- Test 2: encodeText of a general text payload ---
    QrCode qr1 = QrCode::encodeText("Hello, world!", QrCode::Ecc::MEDIUM);
    check(qr1.getVersion() == 1, "version 1 for short text");
    check(qr1.getSize() == 21, "size 21 for version 1");

    // Finder pattern top-left corner check (always dark at module (4,4) center)
    check(qr1.getModule(3, 3), "finder pattern center dark");
    // Timing pattern row 6 alternates starting dark at x=8
    check(qr1.getModule(8, 6), "timing pattern dark at (8,6)");
    check(qr1.getModule(9, 6) == false, "timing pattern light at (9,6)");

    // --- Test 3: binary mode with ECI / manual segments (mid-level API) ---
    std::vector<QrSegment> segs;
    segs.push_back(QrSegment::makeNumeric("123"));
    segs.push_back(QrSegment::makeAlphanumeric("AB"));
    QrCode qr2 = QrCode::encodeSegments(segs, QrCode::Ecc::HIGH);
    check(qr2.getSize() == qr2.getVersion() * 4 + 17, "segments: size formula");

    // --- Test 4: encodeBinary with raw bytes ---
    std::vector<std::uint8_t> data = {0x00, 0x01, 0x02, 0xFE, 0xFF};
    QrCode qr3 = QrCode::encodeBinary(data, QrCode::Ecc::LOW);
    check(qr3.getVersion() >= 1, "binary: valid version");

    // --- Test 5: module matrix sanity — count dark modules (valid QR codes
    // for these payloads always contain a nonzero, bounded number of them) ---
    int dark = 0;
    for (int y = 0; y < qr1.getSize(); y++) {
        for (int x = 0; x < qr1.getSize(); x++) {
            if (qr1.getModule(x, y)) {
                dark++;
            }
        }
    }
    check(dark > 0 && dark < qr1.getSize() * qr1.getSize(), "dark module count in (0, size^2)");

    // --- Test 6: higher error correction level yields version >= lower ---
    QrCode qrLow = QrCode::encodeText("qrcodegen consumer test payload 0123456789",
                                      QrCode::Ecc::LOW);
    QrCode qrHigh = QrCode::encodeText("qrcodegen consumer test payload 0123456789",
                                       QrCode::Ecc::HIGH);
    check(qrHigh.getVersion() >= qrLow.getVersion(), "HIGH ecc version >= LOW ecc");

    if (failures == 0) {
        std::printf("qrcodegen consumer test: ALL PASSED\n");
        return 0;
    }
    std::printf("qrcodegen consumer test: %d FAILURES\n", failures);
    return 1;
}
