#include <QtPositioning/QGeoCoordinate>
#include <QtPositioning/QGeoCircle>
#include <QtPositioning/QGeoRectangle>
#include <QtPositioning/QGeoPositionInfo>
#include <QtPositioning/QNmeaPositionInfoSource>

#include <QDateTime>

#include <cstdio>

/*
 * Substantive smoke test for the Qt Positioning package on HarmonyOS PC.
 *
 * Exercises the real geo types (coordinate, circle, rectangle), position
 * info objects, and the NMEA position info source — not a stub.
 */
int main()
{
    // QGeoCoordinate: construction, validity, type and distance.
    QGeoCoordinate coord(37.0, -122.0);
    if (!coord.isValid() || coord.type() != QGeoCoordinate::Coordinate2D) {
        std::fprintf(stderr, "QGeoCoordinate construction failed\n");
        return 1;
    }

    const QGeoCoordinate other(37.0, -122.1);
    const double distance = coord.distanceTo(other);
    if (distance <= 0.0) {
        std::fprintf(stderr, "QGeoCoordinate::distanceTo gave non-positive %f\n", distance);
        return 2;
    }

    // QGeoCircle: validity and containment.
    QGeoCircle circle(coord, 1000.0);
    if (!circle.isValid() || !circle.contains(coord)) {
        std::fprintf(stderr, "QGeoCircle validity/contains failed\n");
        return 3;
    }

    // QGeoRectangle: validity and containment.
    QGeoRectangle rect(coord, 0.1, 0.1);
    if (!rect.isValid() || !rect.contains(coord)) {
        std::fprintf(stderr, "QGeoRectangle validity/contains failed\n");
        return 4;
    }

    // QGeoPositionInfo: validity and timestamp.
    QGeoPositionInfo info(coord, QDateTime::currentDateTime());
    if (!info.isValid() || !info.timestamp().isValid()) {
        std::fprintf(stderr, "QGeoPositionInfo construction failed\n");
        return 5;
    }

    // QNmeaPositionInfoSource: constructible with a simulation mode.
    QNmeaPositionInfoSource nmea(QNmeaPositionInfoSource::SimulationMode);
    if (nmea.updateInterval() < 0) {
        std::fprintf(stderr, "QNmeaPositionInfoSource::updateInterval invalid\n");
        return 6;
    }

    std::printf("QtPositioning OK: distance=%.2f m, %d inputs exercised\n",
                distance, 6);
    return 0;
}
