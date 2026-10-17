// ksvg 6.26.0 consumer test (R34: exercises real API).
// Loads a real SVG through KSvg::Svg, verifies the size/element API surface
// of the QImage software rendering path, and exercises KSvg::FrameSvg
// margins. Runs headless (QT_QPA_PLATFORM=offscreen).
#include <KSvg/Svg>
#include <KSvg/FrameSvg>
#include <QGuiApplication>
#include <QImage>
#include <QTemporaryDir>
#include <QFile>
#include <cstdio>

static const char *kSvgData = R"SVG(<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="120" height="60">
  <rect id="center" x="20" y="20" width="80" height="20" fill="#1a92ee"/>
  <rect id="topleft" x="0" y="0" width="20" height="20" fill="#123456"/>
</svg>
)SVG";

int main(int argc, char **argv) {
    // KSvg::Svg uses QImage rendering; QGuiApplication is enough (no
    // widgets). offscreen platform is selected via the environment.
    QGuiApplication app(argc, argv);

    // Write a small SVG theme file to a temp location.
    QTemporaryDir tmp;
    QString svgPath = tmp.path() + "/test.svg";
    {
        QFile f(svgPath);
        if (!f.open(QIODevice::WriteOnly)) {
            std::printf("FAIL: cannot write temp svg\n");
            return 1;
        }
        f.write(kSvgData);
    }

    // --- KSvg::Svg API surface ---
    KSvg::Svg *svg = new KSvg::Svg();
    if (!svg) {
        std::printf("FAIL: alloc failed\n");
        return 1;
    }
    svg->setImagePath(svgPath);
    if (!svg->isValid()) {
        std::printf("FAIL: svg not valid after setImagePath\n");
        return 1;
    }

    // contains()/hasElement() on real rendered SVG
    if (!svg->hasElement(QStringLiteral("center"))) {
        std::printf("FAIL: hasElement(center) should be true\n");
        return 1;
    }
    if (svg->hasElement(QStringLiteral("banana"))) {
        std::printf("FAIL: hasElement(banana) should be false\n");
        return 1;
    }

    // size API: default natural size, then resize
    if (svg->size() != QSizeF(120, 60)) {
        std::printf("FAIL: natural size mismatch: %fx%f\n",
                    svg->size().width(), svg->size().height());
        return 1;
    }
    svg->resize(240, 120);
    if (svg->size() != QSizeF(240, 120)) {
        std::printf("FAIL: resize mismatch\n");
        return 1;
    }

    // image() exercises the QImage software rendering path (QPainter +
    // QSvgRenderer), which is the core deliverable of this library.
    QImage img = svg->image(QSize(60, 30));
    if (img.isNull() || img.width() != 60 || img.height() != 30) {
        std::printf("FAIL: rendered image null or wrong size\n");
        return 1;
    }

    // elementRect / elementSize on a real element
    QRectF rect = svg->elementRect(QStringLiteral("topleft"));
    if (rect.isNull() || rect.width() <= 0) {
        std::printf("FAIL: elementRect(topleft) empty\n");
        return 1;
    }

    // status/color-set API
    svg->setStatus(KSvg::Svg::Selected);
    if (svg->status() != KSvg::Svg::Selected) {
        std::printf("FAIL: status round-trip\n");
        return 1;
    }
    svg->setColorSet(KSvg::Svg::Window);
    if (svg->colorSet() != KSvg::Svg::Window) {
        std::printf("FAIL: colorSet round-trip\n");
        return 1;
    }

    // color override API
    svg->setColor(KSvg::Svg::Text, QColor("#123456"));
    if (svg->color(KSvg::Svg::Text) != QColor("#123456")) {
        std::printf("FAIL: color override round-trip\n");
        return 1;
    }
    svg->clearColorOverrides();

    delete svg;

    // --- KSvg::FrameSvg API surface ---
    KSvg::FrameSvg *frame = new KSvg::FrameSvg();
    frame->setImagePath(svgPath);
    frame->setElementPrefix(QStringLiteral("topleft"));
    if (!frame->isValid()) {
        std::printf("FAIL: FrameSvg not valid\n");
        return 1;
    }
    frame->resizeFrame(QSize(100, 100));
    if (frame->frameSize() != QSize(100, 100)) {
        std::printf("FAIL: FrameSvg resize round-trip\n");
        return 1;
    }
    // margins API (may legitimately be 0 for a plain svg without hints)
    frame->margins();
    frame->marginSize(KSvg::FrameSvg::TopMargin);
    frame->marginSize(KSvg::FrameSvg::LeftMargin);
    frame->fixedMargins();
    delete frame;

    std::printf("PASS: KSvg Svg/FrameSvg API surface verified OK\n");
    return 0;
}
