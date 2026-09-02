#include <QApplication>
#include <QtCharts/QChart>
#include <QtCharts/QChartView>
#include <QtCharts/QLineSeries>
#include <QtCharts/QValueAxis>

// Qt5 Charts classes live in the QtCharts namespace (qchartglobal.h defines
// QT_CHARTS_NAMESPACE=QtCharts), so pull them in for the smoke test.
using namespace QtCharts;

int main(int argc, char *argv[]) {
    QApplication application(argc, argv);

    // Exercise the QtCharts API: build a line series, attach it to a chart,
    // create default axes and render it through a QChartView.
    QLineSeries *series = new QLineSeries();
    series->append(0.0, 6.0);
    series->append(2.0, 4.0);
    series->append(3.0, 8.0);
    series->append(7.0, 4.0);
    series->append(10.0, 5.0);
    if (series->count() != 5)
        return 1;

    QChart *chart = new QChart();
    chart->legend()->hide();
    chart->addSeries(series);
    chart->createDefaultAxes();
    chart->setTitle(QStringLiteral("qt5-qtcharts smoke test"));
    if (chart->series().isEmpty())
        return 2;

    QChartView chartView(chart);
    chartView.setRenderHint(QPainter::Antialiasing);
    chartView.resize(400, 300);
    chartView.show();

    if (chart->axes().isEmpty())
        return 3;

    return 0;
}
