// Consumer end-to-end test for the qtpositioning/5.15.2 Conan package.
//
// Executor style: every case prints TEST PASS / TEST FAIL, a SUMMARY line is
// printed at the end, and a non-zero exit code reports any failure.
//
// Cases:
//   1. coordinate_math      - QGeoCoordinate geodesic math (real computations)
//   2. shape_algorithms     - QGeoPath / QGeoRectangle / QGeoPolygon geometry
//   3. nmea_simulation      - QNmeaPositionInfoSource replaying NMEA sentences
//   4. positionpoll_plugin  - position plugin discovery + QPluginLoader load
//   5. qml_positioning      - import QtPositioning 5.15 (PositionSource,
//                             CoordinateAnimation) through the QML engine

#include <QtPositioning/QGeoAreaMonitorSource>
#include <QtPositioning/QGeoCoordinate>
#include <QtPositioning/QGeoPath>
#include <QtPositioning/QGeoPolygon>
#include <QtPositioning/QGeoPositionInfo>
#include <QtPositioning/QGeoPositionInfoSource>
#include <QtPositioning/QGeoPositionInfoSourceFactory>
#include <QtPositioning/QGeoRectangle>
#include <QtPositioning/QNmeaPositionInfoSource>

#include <QCoreApplication>
#include <QEventLoop>
#include <QFileInfo>
#include <QIODevice>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QPluginLoader>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QTimer>

#include <cmath>
#include <cstdio>
#include <cstring>

static int g_passed = 0;
static int g_failed = 0;

struct CaseResult {
    const char *name;
    bool ok = true;
    QString reason;

    explicit CaseResult(const char *caseName) : name(caseName) {}

    void require(bool condition, const QString &why)
    {
        if (!condition && ok) {
            ok = false;
            reason = why;
        }
    }

    void finish() const
    {
        if (ok) {
            ++g_passed;
            std::printf("TEST PASS: %s\n", name);
        } else {
            ++g_failed;
            std::printf("TEST FAIL: %s - %s\n", name, qPrintable(reason));
        }
    }
};

// ---------------------------------------------------------------- case 1
static void testCoordinateMath()
{
    CaseResult r("coordinate_math");
    const QGeoCoordinate munich(48.1173, 11.5167);
    const QGeoCoordinate berlin(52.5200, 13.4050);

    r.require(munich.isValid() && berlin.isValid(), "coordinates reported invalid");
    r.require(munich.type() == QGeoCoordinate::Coordinate2D,
              "2D coordinate type is not Coordinate2D");
    r.require(munich.distanceTo(munich) == 0.0, "distance to self is not 0");

    // Munich -> Berlin is roughly 504 km; a loose band still catches a unit bug.
    const double dist = munich.distanceTo(berlin);
    const double reverse = berlin.distanceTo(munich);
    const double azimuth = munich.azimuthTo(berlin);
    r.require(dist > 400000.0 && dist < 600000.0,
              QString("Munich-Berlin distance out of range: %1 m").arg(dist));
    r.require(std::fabs(dist - reverse) < 1.0,
              QString("distance not symmetric: %1 vs %2 m").arg(dist).arg(reverse));
    r.require(azimuth >= 0.0 && azimuth < 360.0,
              QString("azimuth out of range: %1").arg(azimuth));

    // distanceTo + azimuthTo + atDistanceAndAzimuth must be mutually consistent.
    const QGeoCoordinate roundtrip = munich.atDistanceAndAzimuth(dist, azimuth);
    const double error = roundtrip.distanceTo(berlin);
    r.require(error < 100.0,
              QString("atDistanceAndAzimuth roundtrip error: %1 m").arg(error));

    // One degree of latitude at 48N is ~111.2 km on WGS84.
    const double oneDegree = munich.distanceTo(QGeoCoordinate(49.1173, 11.5167));
    r.require(oneDegree > 110000.0 && oneDegree < 112500.0,
              QString("one degree of latitude = %1 m").arg(oneDegree));

    r.finish();
}

// ---------------------------------------------------------------- case 2
static void testShapeAlgorithms()
{
    CaseResult r("shape_algorithms");
    const QGeoCoordinate a(48.1173, 11.5167);
    const QGeoCoordinate b(48.2, 11.6);
    const QGeoCoordinate c(48.3, 11.7);

    // QGeoPath length: length(0, size-1) is the open polyline length, while
    // the default length() (indexTo = -1) wraps around to the first element
    // (Qt 5.15 semantics, qgeopath.cpp QGeoPathPrivate::length).
    QGeoPath path;
    path.addCoordinate(a);
    path.addCoordinate(b);
    path.addCoordinate(c);
    const double ab = a.distanceTo(b);
    const double bc = b.distanceTo(c);
    const double ca = c.distanceTo(a);
    const double openLength = path.length(0, path.size() - 1);
    r.require(std::fabs(openLength - (ab + bc)) < 1.0,
              QString("QGeoPath::length(0, size-1) %1 vs manual %2").arg(openLength).arg(ab + bc));
    const double wrappedLength = path.length();
    r.require(std::fabs(wrappedLength - (ab + bc + ca)) < 1.0,
              QString("QGeoPath::length() wrap %1 vs manual %2").arg(wrappedLength).arg(ab + bc + ca));
    r.require(path.containsCoordinate(b), "QGeoPath does not contain its own vertex");

    // QGeoRectangle containment and intersection.
    const QGeoRectangle rect(QGeoCoordinate(48.1173, 11.5167), 0.2, 0.2);
    r.require(rect.contains(QGeoCoordinate(48.12, 11.52)),
              "QGeoRectangle does not contain an inside point");
    r.require(!rect.contains(QGeoCoordinate(49.5, 12.5)),
              "QGeoRectangle contains an outside point");
    r.require(rect.intersects(rect), "QGeoRectangle does not intersect itself");

    // QGeoPolygon: point-in-polygon is QGeoShape::contains() (delegates to
    // QGeoPolygonPrivate::polygonContains, clipper/clip2tri backed); the
    // separate containsCoordinate() matches perimeter elements only
    // (inherited QGeoPathPrivate::containsCoordinate = m_path.indexOf()).
    QGeoPolygon poly;
    poly.addCoordinate(QGeoCoordinate(47.9, 11.3));
    poly.addCoordinate(QGeoCoordinate(48.3, 11.3));
    poly.addCoordinate(QGeoCoordinate(48.3, 11.8));
    poly.addCoordinate(QGeoCoordinate(47.9, 11.8));
    r.require(poly.contains(QGeoCoordinate(48.1, 11.5)),
              "QGeoPolygon does not contain its center point");
    r.require(!poly.contains(QGeoCoordinate(50.0, 11.5)),
              "QGeoPolygon contains an outside point");
    r.require(poly.containsCoordinate(QGeoCoordinate(47.9, 11.3)),
              "QGeoPolygon::containsCoordinate missed a perimeter vertex");
    r.require(!poly.containsCoordinate(QGeoCoordinate(48.1, 11.5)),
              "QGeoPolygon::containsCoordinate matched an interior point");

    r.finish();
}

// ---------------------------------------------------------------- case 3
class NmeaFeeder : public QIODevice
{
public:
    explicit NmeaFeeder(const QByteArray &data, QObject *parent = nullptr)
        : QIODevice(parent), m_data(data) {}

    bool isSequential() const override { return true; }
    qint64 bytesAvailable() const override
    {
        return (m_data.size() - m_pos) + QIODevice::bytesAvailable();
    }

protected:
    qint64 readData(char *data, qint64 maxSize) override
    {
        const qint64 left = m_data.size() - m_pos;
        if (left <= 0)
            return 0;
        const qint64 n = qMin(maxSize, left);
        std::memcpy(data, m_data.constData() + m_pos, size_t(n));
        m_pos += n;
        return n;
    }
    qint64 writeData(const char *, qint64) override { return -1; }

private:
    QByteArray m_data;
    qint64 m_pos = 0;
};

static void testNmeaSimulation()
{
    CaseResult r("nmea_simulation");
    // Two satellite fixes one second apart (classic GGA/RMC examples with
    // valid NMEA checksums).
    const QByteArray stream =
        "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
        "$GPGGA,123520,4807.048,N,01131.010,E,1,08,0.9,545.5,M,46.9,M,,*4A\r\n"
        "$GPRMC,123520,A,4807.048,N,01131.010,E,022.4,084.4,230394,003.1,W*66\r\n";

    NmeaFeeder feeder(stream);
    QNmeaPositionInfoSource source(QNmeaPositionInfoSource::SimulationMode);
    source.setDevice(&feeder);

    QList<QGeoPositionInfo> updates;
    QObject::connect(&source, &QGeoPositionInfoSource::positionUpdated,
                     [&updates](const QGeoPositionInfo &info) { updates.append(info); });

    source.startUpdates();

    // The simulated reader emits the first fix immediately and replays the
    // second one ~1 s later (NMEA timestamps differ by one second).
    QEventLoop loop;
    QTimer poll;
    QObject::connect(&poll, &QTimer::timeout, [&updates, &loop]() {
        if (updates.size() >= 2)
            loop.quit();
    });
    poll.start(50);
    QTimer::singleShot(6000, &loop, &QEventLoop::quit);
    loop.exec();
    source.stopUpdates();

    r.require(updates.size() >= 2,
              QString("expected 2 replayed fixes, got %1").arg(updates.size()));
    if (updates.size() >= 2) {
        const QGeoPositionInfo first = updates.at(0);
        const QGeoCoordinate c0 = first.coordinate();
        r.require(std::fabs(c0.latitude() - 48.1173) < 0.001,
                  QString("first fix latitude %1").arg(c0.latitude(), 0, 'f', 6));
        r.require(std::fabs(c0.longitude() - 11.5167) < 0.001,
                  QString("first fix longitude %1").arg(c0.longitude(), 0, 'f', 6));
        r.require(std::fabs(c0.altitude() - 545.4) < 0.5,
                  QString("first fix altitude %1").arg(c0.altitude()));
        r.require(first.hasAttribute(QGeoPositionInfo::GroundSpeed)
                      && std::fabs(first.attribute(QGeoPositionInfo::GroundSpeed)
                                       - 22.4 * 1.852 / 3.6) < 0.5,
                  "first fix ground speed from RMC missing or wrong");
        r.require(first.timestamp().time().isValid(),
                  "first fix has no valid timestamp");

        const QGeoCoordinate c1 = updates.at(1).coordinate();
        r.require(c1.latitude() > c0.latitude() + 0.00005,
                  QString("second fix did not advance north: %1 vs %2")
                      .arg(c1.latitude(), 0, 'f', 6).arg(c0.latitude(), 0, 'f', 6));
    }

    r.finish();
}

// ---------------------------------------------------------------- case 4
static void testPositionPollPlugin()
{
    CaseResult r("positionpoll_plugin");

    // Discovery through the Qt plugin factory loader (QT_PLUGIN_PATH must
    // contain the package's plugins directory; the test harness sets it).
    const QStringList available = QGeoAreaMonitorSource::availableSources();
    std::printf("  QGeoAreaMonitorSource::availableSources() = [%s]\n",
                qPrintable(available.join(", ")));
    r.require(available.contains(QStringLiteral("positionpoll")),
              "positionpoll not announced by QGeoAreaMonitorSource::availableSources()");

    // Direct load of the packaged plugin binary.
    const QByteArray envPath = qgetenv("QT_POSITIONING_PLUGIN");
    r.require(!envPath.isEmpty(), "QT_POSITIONING_PLUGIN is not set by the test harness");
    if (!envPath.isEmpty()) {
        const QString pluginPath = QString::fromLocal8Bit(envPath);
        r.require(QFileInfo::exists(pluginPath),
                  QString("plugin file missing: %1").arg(pluginPath));
        QPluginLoader loader(pluginPath);
        QObject *instance = loader.instance();
        r.require(instance != nullptr,
                  QString("QPluginLoader::instance() failed: %1").arg(loader.errorString()));
        if (instance) {
            QGeoPositionInfoSourceFactory *factory =
                qobject_cast<QGeoPositionInfoSourceFactory *>(instance);
            r.require(factory != nullptr,
                      "loaded plugin does not implement QGeoPositionInfoSourceFactory");

            const QJsonObject meta = loader.metaData().value(QStringLiteral("MetaData")).toObject();
            QStringList keys;
            const QJsonArray keyArray = meta.value(QStringLiteral("Keys")).toArray();
            for (const QJsonValue &key : keyArray)
                keys << key.toString();
            r.require(keys.contains(QStringLiteral("positionpoll")),
                      QString("plugin metadata Keys = [%1]").arg(keys.join(", ")));
            r.require(meta.value(QStringLiteral("Monitor")).toBool(),
                      "plugin metadata does not announce monitor support");
        }
    }

    r.finish();
}

// ---------------------------------------------------------------- case 5
static void testQmlPositioning()
{
    CaseResult r("qml_positioning");
    QQmlEngine engine;
    const QByteArray importEnv = qgetenv("OHC_QML_IMPORT_PATH");
    for (const QByteArray &one : importEnv.split(':')) {
        if (!one.isEmpty())
            engine.addImportPath(QString::fromLocal8Bit(one));
    }

    QQmlComponent sourceComponent(&engine);
    sourceComponent.setData("import QtPositioning 5.15\n"
                            "PositionSource { updateInterval: 1000 }\n",
                            QUrl());
    r.require(!sourceComponent.isError(),
              QString("PositionSource compile error: %1").arg(sourceComponent.errorString()));
    QObject *sourceObject = sourceComponent.create();
    r.require(sourceObject != nullptr,
              QString("PositionSource create() returned null: %1").arg(sourceComponent.errorString()));
    if (sourceObject) {
        r.require(sourceObject->property("updateInterval").toInt() == 1000,
                  "PositionSource.updateInterval property was not applied");
        r.require(sourceObject->property("active").isValid(),
                  "PositionSource lacks the 'active' property");
        delete sourceObject;
    }

    QQmlComponent animationComponent(&engine);
    animationComponent.setData("import QtPositioning 5.15\n"
                               "CoordinateAnimation { duration: 0 }\n",
                               QUrl());
    r.require(!animationComponent.isError(),
              QString("CoordinateAnimation compile error: %1").arg(animationComponent.errorString()));
    if (!animationComponent.isError()) {
        QObject *animationObject = animationComponent.create();
        r.require(animationObject != nullptr,
                  QString("CoordinateAnimation create() returned null: %1")
                      .arg(animationComponent.errorString()));
        delete animationObject;
    }

    r.finish();
}

// ---------------------------------------------------------------- main
int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    testCoordinateMath();
    testShapeAlgorithms();
    testNmeaSimulation();
    testPositionPollPlugin();
    testQmlPositioning();

    const int total = g_passed + g_failed;
    std::printf("TEST SUMMARY: %d/%d cases passed\n", g_passed, total);
    return g_failed == 0 ? 0 : 1;
}
