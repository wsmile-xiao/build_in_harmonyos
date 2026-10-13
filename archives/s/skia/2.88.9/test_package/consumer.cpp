#include <cstdint>
#include <cstdio>
#include <cstring>

#include "include/codec/SkCodec.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkColor.h"
#include "include/core/SkData.h"
#include "include/core/SkImageInfo.h"
#include "include/core/SkPaint.h"
#include "include/core/SkPath.h"
#include "include/core/SkPixmap.h"
#include "include/core/SkRect.h"
#include "include/core/SkStream.h"
#include "include/core/SkSurface.h"
#include "include/encode/SkPngEncoder.h"

// 最小消费者程序：只走 skia 的公共 API，验证 CPU 光栅化 + 编解码面在 OHOS 上可用。
// 覆盖：光栅 surface 创建 / 立即模式绘制（矩形、抗锯齿、路径描边）/ 像素回读 /
//       libpng 编码（SkPngEncoder）/ 解码（SkCodec，走 libpng decode 路径）。
static int g_pass = 0;
static int g_fail = 0;

static void check(bool ok, const char* name) {
    if (ok) {
        ++g_pass;
        std::printf("PASS: %s\n", name);
    } else {
        ++g_fail;
        std::printf("FAIL: %s\n", name);
    }
}

int main() {
    const int W = 32, H = 32;

    auto surface = SkSurface::MakeRasterN32Premul(W, H);
    check(surface != nullptr, "SkSurface::MakeRasterN32Premul(32,32)");
    if (!surface) {
        std::printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
        return 2;
    }

    SkCanvas* canvas = surface->getCanvas();
    check(canvas != nullptr, "surface->getCanvas()");

    canvas->clear(SK_ColorWHITE);

    SkPaint fill;
    fill.setColor(SK_ColorRED);
    fill.setAntiAlias(true);
    canvas->drawRect(SkRect::MakeXYWH(4, 4, 24, 24), fill);

    SkPaint stroke;
    stroke.setColor(SK_ColorBLUE);
    stroke.setStyle(SkPaint::kStroke_Style);
    stroke.setStrokeWidth(2);
    stroke.setAntiAlias(true);
    SkPath path;
    path.moveTo(2, 30);
    path.lineTo(16, 2);
    path.lineTo(30, 30);
    canvas->drawPath(path, stroke);
    check(true, "CPU raster: drawRect + drawPath(stroke, AA)");

    SkImageInfo info = SkImageInfo::MakeN32Premul(W, H);
    uint32_t pixels[W * H];
    std::memset(pixels, 0, sizeof(pixels));
    check(surface->readPixels(info, pixels, W * sizeof(uint32_t), 0, 0),
          "surface->readPixels()");

    const uint32_t c = pixels[16 * W + 16];
    const unsigned a = (c >> 24) & 0xFFu;
    const unsigned r = c & 0xFFu;
    const unsigned g = (c >> 8) & 0xFFu;
    const unsigned b = (c >> 16) & 0xFFu;
    std::printf("INFO: center pixel = a=%u r=%u g=%u b=%u\n", a, r, g, b);
    check(a == 255 && r == 255 && g == 0 && b == 0, "center pixel is opaque red");

    // --- libpng encode path ---
    SkDynamicMemoryWStream stream;
    SkPixmap pmap;
    const bool peeked = surface->peekPixels(&pmap);
    check(peeked, "surface->peekPixels()");

    const bool encoded =
            peeked && SkPngEncoder::Encode(&stream, pmap, SkPngEncoder::Options{});
    check(encoded, "SkPngEncoder::Encode (libpng encode path)");

    sk_sp<SkData> data = stream.detachAsData();
    const bool magic = data && data->size() > 8 && data->bytes()[0] == 0x89 &&
                       data->bytes()[1] == 'P' && data->bytes()[2] == 'N' &&
                       data->bytes()[3] == 'G';
    std::printf("INFO: encoded png bytes = %zu\n", data ? data->size() : 0);
    check(magic, "PNG signature (89 50 4E 47)");

    // --- libpng decode path ---
    sk_sp<SkData> png = data;
    auto codec = png ? SkCodec::MakeFromData(png) : nullptr;
    check(codec != nullptr, "SkCodec::MakeFromData(png)");
    if (codec) {
        check(codec->getInfo().width() == W && codec->getInfo().height() == H,
              "decoded image size == 32x32");
    }

    std::printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
