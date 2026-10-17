#include <QtCore/QUrl>
#include <QtGui/QGuiApplication>
#include <QtGraphs/QBarSeries>
#include <QtGraphs/QBarSet>
#include <QtGraphs/QLineSeries>
#include <QtGraphs/QScatterSeries>
#include <QtGraphs/QValueAxis>
#include <QtGraphs/QtGraphs>
#include <QtGraphs/qtgraphsversion.h>
#include <QtQml/QQmlComponent>
#include <QtQml/QQmlEngine>

#include <cstdlib>
#include <cstring>
#include <iostream>

namespace {

bool run_render_probe(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData(R"QML(
import QtQuick
import QtGraphs

GraphsView {
    width: 320
    height: 240
    BarSeries {
        BarSet {
            label: "A"
            values: [1, 2, 3]
        }
    }
}
)QML", QUrl());

    if (component.isError()) {
        const auto errors = component.errors();
        for (const auto &error : errors) {
            std::cerr << error.toString().toStdString() << std::endl;
        }
        return false;
    }

    QObject *root = component.create();
    if (!root) {
        std::cerr << "Qt Graphs QML component creation failed" << std::endl;
        return false;
    }

    delete root;
    return true;
}

} // namespace

int main(int argc, char **argv) {
    QBarSeries bar_series;
    QBarSet bar_set(QStringLiteral("A"));
    bar_set.append(QList<qreal>{1.0f, 2.0f, 3.0f});
    if (!bar_series.append(&bar_set) || bar_series.barSets().size() != 1 ||
        bar_set.count() != 3) {
        return EXIT_FAILURE;
    }

    QLineSeries line_series;
    line_series.append(0.0f, 1.0f);
    line_series.append(1.0f, 2.0f);
    line_series.append(2.0f, 3.0f);
    if (line_series.count() != 3 || line_series.at(1).y() != 2.0f) {
        return EXIT_FAILURE;
    }

    QScatterSeries scatter_series;
    scatter_series.append(0.0f, 1.0f);
    scatter_series.append(1.0f, 2.0f);
    if (scatter_series.count() != 2) {
        return EXIT_FAILURE;
    }

    if (std::strlen(QTGRAPHS_VERSION_STR) == 0) {
        return EXIT_FAILURE;
    }

    if (std::getenv("QTGRAPHS_RUN_RENDER_TEST") == nullptr) {
        std::cout << "Qt Graphs render validation skipped: set QTGRAPHS_RUN_RENDER_TEST=1 in an OpenHarmony display session" << std::endl;
        return EXIT_SUCCESS;
    }

    return run_render_probe(argc, argv) ? EXIT_SUCCESS : EXIT_FAILURE;
}
