#include <cstdio>
#include <memory>
#include <string>

#include "lunasvg/lunasvg.h"

// Consumer test: parse a minimal SVG document, render it to a Bitmap and
// verify a non-trivial pixel result (red rect center must be red).
int main() {
    const std::string svg =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\">"
        "<rect width=\"10\" height=\"10\" fill=\"#ff0000\"/>"
        "</svg>";

    auto doc = lunasvg::Document::loadFromData(svg);
    if (!doc) {
        std::fprintf(stderr, "FAIL: loadFromData returned null\n");
        return 1;
    }

    auto bitmap = doc->renderToBitmap(10, 10);
    if (bitmap.isNull()) {
        std::fprintf(stderr, "FAIL: renderToBitmap returned null bitmap\n");
        return 1;
    }
    if (bitmap.width() != 10 || bitmap.height() != 10) {
        std::fprintf(stderr, "FAIL: bitmap size %dx%d, expected 10x10\n",
                     bitmap.width(), bitmap.height());
        return 1;
    }

    // Center pixel (5,5) must be opaque red (#ff0000). plutovg stores pixels
    // premultiplied in BGRA byte order on little-endian targets, so byte[0]=B,
    // byte[1]=G, byte[2]=R, byte[3]=A.
    unsigned char* data = bitmap.data();
    const int center = 5 * 4 + 5 * bitmap.stride();
    const unsigned char b = data[center + 0];
    const unsigned char g = data[center + 1];
    const unsigned char r = data[center + 2];
    const unsigned char a = data[center + 3];
    if (!(r == 0xff && g == 0x00 && b == 0x00 && a == 0xff)) {
        std::fprintf(stderr, "FAIL: center pixel rgba=(%u,%u,%u,%u), expected (255,0,0,255)\n",
                     r, g, b, a);
        return 1;
    }

    std::printf("test lunasvg 3.5.0: OK (center pixel rgba=%u,%u,%u,%u)\n",
                r, g, b, a);
    return 0;
}
