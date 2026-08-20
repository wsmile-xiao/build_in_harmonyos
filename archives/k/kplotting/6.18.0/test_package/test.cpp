// kplotting 6.18.0 consumer test (R34: exercises real Widgets API).
#include <KPlotObject>
#include <KPlotPoint>
#include <KPlotWidget>

#include <QApplication>
#include <QColor>
#include <QRectF>
#include <QString>

#include <cstdio>

static int fail(const char *message)
{
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    KPlotWidget widget;
    widget.setLimits(0.0, 10.0, -5.0, 5.0);
    widget.setBackgroundColor(Qt::black);
    widget.setForegroundColor(Qt::white);

    auto *object = new KPlotObject(Qt::red, KPlotObject::Lines, 2.0);
    object->addPoint(1.0, 2.0, QStringLiteral("first"));
    object->addPoint(2.0, 3.0, QStringLiteral("second"));
    widget.addPlotObject(object);

    if (widget.plotObjects().size() != 1) {
        return fail("plot object was not added to widget");
    }
    if (widget.dataRect() != QRectF(0.0, -5.0, 10.0, 10.0)) {
        return fail("plot limits did not round-trip");
    }
    if (object->points().size() != 2) {
        return fail("plot points were not retained");
    }
    if (object->points().front()->label() != QStringLiteral("first")) {
        return fail("plot point label did not round-trip");
    }
    if (!object->plotTypes().testFlag(KPlotObject::Lines)) {
        return fail("plot type flag did not round-trip");
    }

    std::printf("PASS: KPlotting widget smoke OK\n");
    return 0;
}
