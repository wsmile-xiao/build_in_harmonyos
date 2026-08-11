#include <QGeoCoordinate>
#include <QGeoRectangle>
#include <QGeoPath>
#include <QtGlobal>

#include <cstdio>

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // QGeoCoordinate: construction, validity and distance
    const QGeoCoordinate oslo(59.9139, 10.7522);
    const QGeoCoordinate tokyo(35.6762, 139.6503);
    if (!oslo.isValid())
        return 1;
    const qreal distance = oslo.distanceTo(tokyo);
    if (distance <= 0.0)
        return 2;

    // QGeoRectangle: bounds containment
    const QGeoRectangle rect(QGeoCoordinate(60.0, 10.0),
                             QGeoCoordinate(55.0, 12.0));
    if (!rect.contains(QGeoCoordinate(58.0, 11.0)))
        return 3;
    if (rect.contains(QGeoCoordinate(50.0, 5.0)))
        return 4;

    // QGeoPath: polyline path construction
    QGeoPath path;
    path.addCoordinate(QGeoCoordinate(59.9139, 10.7522));
    path.addCoordinate(QGeoCoordinate(35.6762, 139.6503));
    if (path.size() != 2)
        return 5;
    if (!path.coordinateAt(0).isValid())
        return 6;

    std::printf(
        "Qt %s QGeoCoordinate/QGeoRectangle/QGeoPath work\n",
        QT_VERSION_STR
    );
    return 0;
}
