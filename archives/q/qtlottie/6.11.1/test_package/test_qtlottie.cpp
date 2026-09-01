// Consumer smoke test for qtlottie 6.11.1 on HarmonyOS PC.
// Instantiates the real Qt.labs.lottieqt LottieAnimation through the QML
// engine, feeds it an upstream Lottie JSON fixture, and verifies that the parser
// reports Ready and exposes the parsed frame/duration metadata.

#include <QtCore/QDir>
#include <QtCore/QEventLoop>
#include <QtCore/QFile>
#include <QtCore/QMetaEnum>
#include <QtCore/QMetaObject>
#include <QtCore/QTemporaryFile>
#include <QtCore/QTimer>
#include <QtCore/QUrl>
#include <QtGui/QGuiApplication>
#include <QtQml/QQmlComponent>
#include <QtQml/QQmlEngine>

#include <cstdio>

static bool writeUpstreamLottie(QFile &file)
{
    // tests/auto/lottie/shape/ellipse/data/ellipse_static_100x80.json
    const char json[] =
        R"lottie({"v":"5.3.4","fr":60,"ip":0,"op":180,"w":320,"h":320,"nm":"StaticRoundShapeLayer","ddd":0,"assets":[],"layers":[{"ddd":0,"ind":1,"ty":4,"nm":"Shape Layer 1","sr":1,"ks":{"o":{"a":0,"k":100,"ix":11},"r":{"a":0,"k":0,"ix":10},"p":{"a":0,"k":[150,150,0],"ix":2},"a":{"a":0,"k":[0,0,0],"ix":1},"s":{"a":0,"k":[100,100,100],"ix":6}},"ao":0,"shapes":[{"d":1,"ty":"el","s":{"a":0,"k":[100,80],"ix":2},"p":{"a":0,"k":[0,0],"ix":3},"nm":"Ellipse Path 1","mn":"ADBE Vector Shape - Ellipse","hd":false}],"ip":0,"op":180,"st":0,"bm":0}],"markers":[]})lottie";
    return file.write(json, sizeof(json) - 1) == static_cast<qint64>(sizeof(json) - 1);
}

static int failures = 0;

#define CHECK(cond, name)                                                      \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("[PASS] %s\n", name);                                  \
        } else {                                                               \
            std::printf("[FAIL] %s\n", name);                                  \
            ++failures;                                                        \
        }                                                                      \
    } while (0)

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    QTemporaryFile lottieFile(QDir::tempPath() + "/qtlottie-XXXXXX.json");
    if (!lottieFile.open()) {
        std::fprintf(stderr, "Cannot create temporary Lottie JSON\n");
        return 1;
    }
    if (!writeUpstreamLottie(lottieFile)) {
        std::fprintf(stderr, "Cannot write temporary Lottie JSON\n");
        return 2;
    }

    lottieFile.flush();
    lottieFile.close();

    QQmlEngine engine;
    QQmlComponent component(&engine);
    component.setData(
        QByteArrayLiteral(
            "import Qt.labs.lottieqt 1.0\n"
            "LottieAnimation { autoPlay: false }\n"),
        QUrl());
    if (component.isError()) {
        std::fprintf(stderr, "QML component failed to load: %s\n",
                     qPrintable(component.errorString()));
        return 3;
    }

    QScopedPointer<QObject> object(component.create());
    if (!object) {
        std::fprintf(stderr, "LottieAnimation instance was not created\n");
        return 4;
    }
    QObject *animation = object.data();

    const QMetaObject *meta = animation->metaObject();
    const int statusIndex = meta->indexOfEnumerator("Status");
    int loadingValue = -1;
    int readyValue = -1;
    int errorValue = -1;
    if (statusIndex >= 0) {
        const QMetaEnum statusEnum = meta->enumerator(statusIndex);
        loadingValue = statusEnum.keyToValue("Loading");
        readyValue = statusEnum.keyToValue("Ready");
        errorValue = statusEnum.keyToValue("Error");
    }
    if (readyValue < 0) {
        std::fprintf(stderr, "LottieAnimation Status enum was not exposed\n");
        return 5;
    }

    animation->setProperty("source", QUrl::fromLocalFile(lottieFile.fileName()));

    QEventLoop loop;
    QTimer poll;
    poll.setInterval(50);
    QObject::connect(&poll, &QTimer::timeout, &loop, [&]() {
        const int status = animation->property("status").toInt();
        if (status == readyValue || status == errorValue)
            loop.quit();
    });
    QTimer::singleShot(10000, &loop, &QEventLoop::quit);
    if (animation->property("status").toInt() == loadingValue)
        poll.start();
    if (poll.isActive())
        loop.exec();
    poll.stop();

    CHECK(animation->property("status").toInt() == readyValue,
          "Lottie JSON parsed and animation reached Ready");
    CHECK(animation->property("startFrame").toInt() == 0,
          "startFrame parsed from Lottie JSON");
    CHECK(animation->property("endFrame").toInt() == 180,
          "endFrame parsed from Lottie JSON");
    CHECK(animation->property("frameRate").toInt() == 60,
          "frameRate parsed from Lottie JSON");
    double durationFrames = 0.0;
    QMetaObject::invokeMethod(animation, "getDuration",
                              Q_RETURN_ARG(double, durationFrames),
                              Q_ARG(bool, true));
    CHECK(durationFrames == 180.0,
          "duration in frames parsed from Lottie JSON");

    std::printf("qtlottie consumer test: %s\n",
                failures == 0 ? "ALL PASSED" : "FAILED");
    return failures == 0 ? 0 : 1;
}
