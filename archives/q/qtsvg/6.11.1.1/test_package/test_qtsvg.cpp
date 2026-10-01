// Consumer test for Qt6Svg on HarmonyOS PC.
// Renders a minimal SVG with QSvgRenderer and verifies the output is a
// non-empty raster image, proving the packaged Qt6::Svg API is usable.

#include <QImage>
#include <QPainter>
#include <QSvgRenderer>
#include <cstdio>

int main()
{
    const char* svg_data =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"32\" height=\"32\">"
        "<rect width=\"32\" height=\"32\" fill=\"#4caf50\"/></svg>";
    QByteArray data(svg_data);

    QSvgRenderer renderer(data);
    if (!renderer.isValid()) {
        std::fprintf(stderr, "test_qtsvg: QSvgRenderer rejected valid SVG\n");
        return 1;
    }

    QImage image(renderer.defaultSize(), QImage::Format_ARGB32);
    image.fill(Qt::transparent);
    QPainter painter(&image);
    renderer.render(&painter);
    painter.end();

    if (image.isNull() || image.width() != 32 || image.height() != 32) {
        std::fprintf(stderr, "test_qtsvg: rendered image has unexpected size\n");
        return 1;
    }

    // The top-left pixel must be the green fill (allow minor premultiplied
    // rounding by checking green is the dominant channel).
    const QRgb pixel = image.pixel(0, 0);
    if (qGreen(pixel) <= qRed(pixel) || qGreen(pixel) <= qBlue(pixel)) {
        std::fprintf(stderr, "test_qtsvg: unexpected top-left pixel 0x%x\n",
                     pixel);
        return 1;
    }

    std::printf("test_qtsvg: QSvgRenderer render OK (%dx%d)\n",
                image.width(), image.height());
    return 0;
}
