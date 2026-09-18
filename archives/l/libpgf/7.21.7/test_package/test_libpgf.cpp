// Consumer test for libpgf/7.21.7 on OHOS.
//
// Builds a deterministic 64x48 RGB gradient, losslessly encodes it into an
// in-memory PGF stream via CPGFImage/CPGFMemoryStream, then decodes it back
// and asserts header and pixel round-trip equality (quality=0 is lossless).
#include "PGFimage.h"

#include <cstdio>
#include <cstring>
#include <vector>

static const UINT32 kWidth = 64;
static const UINT32 kHeight = 48;
static const int kPitch = static_cast<int>(kWidth) * 4;  // bytes per row, 32bpp buffer

static int g_checks = 0;
static int g_failed = 0;

static void Check(bool cond, const char* name) {
    g_checks++;
    if (cond) {
        std::printf("PASS: %s\n", name);
    } else {
        g_failed++;
        std::printf("FAIL: %s\n", name);
    }
}

static UINT32 MakePixel(UINT32 x, UINT32 y) {
    // PGF expects BGR channel order in RGB color mode; the 32bpp buffer holds
    // byte 0 = B, byte 1 = G, byte 2 = R, byte 3 = unused.
    const UINT32 b = (x * 4) & 0xFF;
    const UINT32 g = (y * 5) & 0xFF;
    const UINT32 r = ((x + y) * 2) & 0xFF;
    return b | (g << 8) | (r << 16);
}

int main() {
    PGFHeader header;
    header.width = kWidth;
    header.height = kHeight;
    header.nLevels = 4;
    header.quality = 0;  // lossless
    header.bpp = 24;
    header.channels = 3;
    header.mode = ImageModeRGBColor;
    header.usedBitsPerChannel = 8;

    std::vector<UINT32> src(kWidth * kHeight);
    for (UINT32 y = 0; y < kHeight; ++y) {
        for (UINT32 x = 0; x < kWidth; ++x) {
            src[y * kWidth + x] = MakePixel(x, y);
        }
    }

    try {
        CPGFImage encoder;
        encoder.SetHeader(header);
        encoder.ImportBitmap(kPitch, reinterpret_cast<UINT8*>(src.data()), 32);

        CPGFMemoryStream stream(kWidth * kHeight * 4 + 65536);
        encoder.Write(&stream);
        const UINT64 encoded = stream.GetEOS();
        Check(encoded > 0, "encoded PGF stream is not empty");
        Check(encoded < static_cast<UINT64>(kWidth) * kHeight * 4,
              "encoded stream smaller than raw 24bpp raster");

        stream.SetPos(FSFromStart, 0);
        CPGFImage decoder;
        decoder.Open(&stream);
        decoder.Read();

        const PGFHeader* hdr = decoder.GetHeader();
        Check(hdr != nullptr && hdr->width == kWidth && hdr->height == kHeight,
              "decoded header keeps width/height");
        Check(hdr != nullptr && hdr->channels == 3 && hdr->bpp == 24 &&
                  hdr->mode == ImageModeRGBColor,
              "decoded header keeps channels/bpp/mode");

        std::vector<UINT32> dst(kWidth * kHeight, 0);
        decoder.GetBitmap(kPitch, reinterpret_cast<UINT8*>(dst.data()), 32);
        Check(std::memcmp(src.data(), dst.data(), sizeof(UINT32) * kWidth * kHeight) == 0,
              "lossless round trip restores every pixel");
    } catch (const std::exception& e) {
        std::printf("EXCEPTION: %s\n", e.what());
        return 2;
    } catch (...) {
        std::printf("EXCEPTION: unknown\n");
        return 2;
    }

    std::printf("%d checks, %d failures\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
