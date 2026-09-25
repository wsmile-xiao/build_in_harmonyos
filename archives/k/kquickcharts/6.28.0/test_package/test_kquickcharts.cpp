// Conan test_package consumer for kquickcharts 6.28.0.
//
// Really exercises the packaged artifact: loads the org.kde.quickcharts QML
// module, instantiates BarChart/LineChart/PieChart, feeds an ArraySource data
// source into a BarChart and reads back chart-specific properties. Fails if
// any of the QML types cannot be instantiated.
#include <QtCore/QUrl>
#include <QtGui/QGuiApplication>
#include <QtQml/QQmlComponent>
#include <QtQml/QQmlEngine>

#include <iostream>

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData(R"QML(
import QtQuick
import org.kde.quickcharts

Item {
    id: root
    ArraySource { id: values; array: [1, 2, 3, 4, 5] }
    BarChart {
        id: bar
        objectName: "barChart"
        width: 100; height: 100
        valueSources: [values]
    }
    LineChart {
        id: line
        objectName: "lineChart"
        width: 100; height: 100
        interpolate: false
        lineWidth: 3
    }
    PieChart {
        id: pie
        objectName: "pieChart"
        width: 100; height: 100
        filled: true
        thickness: 0.5
    }
}
)QML", QUrl());

    if (component.isError()) {
        const auto errors = component.errors();
        for (const auto &error : errors) {
            std::cerr << error.toString().toStdString() << std::endl;
        }
        std::cerr << "KQUICKCHARTS_TEST_FAIL: QML module org.kde.quickcharts failed to load"
                  << std::endl;
        return 1;
    }

    QObject *root = component.create();
    if (root == nullptr) {
        std::cerr << "KQUICKCHARTS_TEST_FAIL: component.create() returned null" << std::endl;
        return 1;
    }

    QObject *bar = root->findChild<QObject *>("barChart");
    QObject *line = root->findChild<QObject *>("lineChart");
    QObject *pie = root->findChild<QObject *>("pieChart");
    if (!bar || !line || !pie) {
        std::cerr << "KQUICKCHARTS_TEST_FAIL: one or more chart types did not instantiate"
                  << std::endl;
        return 1;
    }

    bool ok = false;
    const qreal lineWidth = line->property("lineWidth").toReal(&ok);
    if (!ok || lineWidth <= 0) {
        std::cerr << "KQUICKCHARTS_TEST_FAIL: LineChart.lineWidth not readable" << std::endl;
        return 1;
    }
    const qreal thickness = pie->property("thickness").toReal(&ok);
    if (!ok || thickness <= 0) {
        std::cerr << "KQUICKCHARTS_TEST_FAIL: PieChart.thickness not readable" << std::endl;
        return 1;
    }

    std::cout << "KQUICKCHARTS_TEST_OK: BarChart/LineChart/PieChart instantiated "
                 "(lineWidth=" << lineWidth << ", thickness=" << thickness << ")"
              << std::endl;
    delete root;
    return 0;
}
