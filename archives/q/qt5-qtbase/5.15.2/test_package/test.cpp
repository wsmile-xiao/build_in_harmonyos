#include <QGuiApplication>
#include <QHostAddress>
#include <QColor>
#include <QImage>
#include <QLibrary>
#include <QMatrix4x4>
#include <QtTest/QtTest>

int main(int argc, char *argv[]) {
    QGuiApplication application(argc, argv);

    // Use a QtNetwork API that does not require an AF_UNIX socket bind, which
    // is restricted by the OHOS sandbox.
    const QHostAddress loopback(QStringLiteral("127.0.0.1"));
    if (!loopback.isLoopback())
        return 2;

    QMatrix4x4 transform;
    transform.translate(1.0f, 2.0f, 3.0f);
    if (transform.map(QVector3D(0.0f, 0.0f, 0.0f)) != QVector3D(1.0f, 2.0f, 3.0f))
        return 3;

    // Verify QtGui can be loaded without requiring an OpenGL context, which
    // the OHOS offscreen platform plugin does not provide.
    QLibrary gui("Qt5Gui");
    if (!gui.load())
        return 4;
    gui.unload();

    QImage image(2, 2, QImage::Format_ARGB32);
    image.fill(Qt::red);
    if (image.pixelColor(0, 0) != QColor(Qt::red))
        return 5;

    QTest::qWait(1);
    return 0;
}
