#include <QGuiApplication>
#include <QSvgRenderer>
#include <QImage>
#include <QPainter>
#include <QByteArray>

int main(int argc, char *argv[]) {
    QGuiApplication application(argc, argv);

    // Minimal SVG document: a red rectangle 100x100
    const char svgData[] =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\">"
        "<rect width=\"100\" height=\"100\" fill=\"red\"/>"
        "</svg>";

    QByteArray ba(svgData);
    QSvgRenderer renderer;
    if (!renderer.load(ba))
        return 2;

    // Render the SVG to a QImage and verify it is non-empty
    QImage image(100, 100, QImage::Format_ARGB32);
    image.fill(Qt::transparent);
    QPainter painter(&image);
    renderer.render(&painter);
    painter.end();

    if (image.isNull())
        return 3;

    // Check that the rendered output contains non-transparent pixels
    bool hasContent = false;
    for (int y = 0; y < image.height() && !hasContent; ++y) {
        for (int x = 0; x < image.width(); ++x) {
            if (qAlpha(image.pixel(x, y)) != 0) {
                hasContent = true;
                break;
            }
        }
    }
    if (!hasContent)
        return 4;

    return 0;
}
