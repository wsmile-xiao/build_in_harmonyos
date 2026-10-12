/* Consumer-side verification for kdiagram 3.0.1 (KChart6 + KGantt6).
 *
 * Part 1: the installed KChart6Config.cmake / KGantt6Config.cmake are
 *         found through find_package(CONFIG) — the exact mechanism
 *         eventviews (KDE PIM) uses to link KChart.
 * Part 2: instantiate a KChart::Chart + BarDiagram over a
 *         QStandardItemModel and a KGantt::View + ConstraintModel —
 *         exercising the exported KChart6::KChart6 / KGantt6::KGantt6
 *         targets (offscreen, no event loop).
 * Part 3: render the chart into a QImage and assert non-empty output.
 */
#include <QApplication>
#include <QImage>
#include <QStandardItemModel>
#include <QPainter>
#include <QVariant>

#include <KChartChart>
#include <KChartBarDiagram>
#include <KChartCartesianCoordinatePlane>

#include <KGanttView>
#include <KGanttConstraintmodel>

#include <cstdio>

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // ---- Part 2a: KChart chart over a standard item model ----------
    QStandardItemModel model(3, 3);
    for (int row = 0; row < 3; ++row)
        for (int col = 0; col < 3; ++col)
            model.setItem(row, col, new QStandardItem(QString::number((row + 1) * (col + 1))));

    KChart::Chart chart;
    KChart::BarDiagram *bars = new KChart::BarDiagram;
    bars->setModel(&model);
    chart.coordinatePlane()->replaceDiagram(bars);
    chart.resize(400, 300);

    // ---- Part 3: offscreen render must produce content --------------
    QImage image(400, 300, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::white);
    QPainter painter(&image);
    chart.paint(&painter, image.rect());
    painter.end();

    int nonWhite = 0;
    for (int y = 0; y < image.height(); ++y)
        for (int x = 0; x < image.width(); ++x)
            if (image.pixel(x, y) != QColor(Qt::white).rgb())
                ++nonWhite;
    if (nonWhite <= 0) {
        std::printf("FAIL: chart rendered no content\n");
        return 1;
    }

    // ---- Part 2b: KGantt view + constraint model --------------------
    KGantt::View ganttView;
    QStandardItemModel ganttModel(2, 2);
    ganttView.setModel(&ganttModel);
    KGantt::ConstraintModel constraints;
    ganttView.setConstraintModel(&constraints);
    if (ganttView.constraintModel() != &constraints) {
        std::printf("FAIL: constraint model not retained\n");
        return 1;
    }

    std::printf("PASS: KChart6+KGantt6 consumer test "
                "(find_package configs, chart render %d px, KGantt model APIs)\n",
                nonWhite);
    return 0;
}
