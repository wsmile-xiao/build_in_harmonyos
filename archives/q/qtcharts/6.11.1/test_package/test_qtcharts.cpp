#include <QApplication>
#include <QChart>
#include <QChartView>
#include <QLineSeries>
#include <QtGlobal>
#include <cstdio>

int main(int argc, char **argv) {
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication app(argc, argv);
    if (app.platformName() != "offscreen")
        return 1;

    auto *chart = new QChart;
    QChartView view(chart);
    auto *series = new QLineSeries;
    series->append(0.0, 1.0);
    series->append(1.0, 3.0);
    chart->addSeries(series);
    chart->createDefaultAxes();
    chart->setTitle("HarmonyOS Qt Charts test");

    view.resize(320, 240);
    view.show();
    app.processEvents();
    if (!view.isVisible())
        return 2;

    if (chart->series().size() != 1 || chart->series().at(0) != series)
        return 3;
    if (series->count() != 2 || series->at(1).y() != 3.0)
        return 4;
    if (chart->axes(Qt::Horizontal, series).isEmpty() ||
        chart->axes(Qt::Vertical, series).isEmpty())
        return 5;
    if (chart->title() != "HarmonyOS Qt Charts test")
        return 6;

    std::printf(
        "Qt Charts offscreen QPA view works with Qt %s\n", QT_VERSION_STR
    );
    return 0;
}
