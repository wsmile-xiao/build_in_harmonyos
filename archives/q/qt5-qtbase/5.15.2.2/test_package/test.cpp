#include <QApplication>
#include <QWidget>
#include <QLabel>
#include <QDomDocument>
#include <QPrinter>
#include <QHostAddress>
#include <QColor>
#include <QImage>
#include <QLibrary>
#include <QMatrix4x4>
#include <QtTest/QtTest>

int main(int argc, char *argv[]) {
    QApplication application(argc, argv);

    // QtNetwork: resolve a loopback address without requiring an AF_UNIX
    // socket bind, which the OHOS sandbox rejects.
    const QHostAddress loopback(QStringLiteral("127.0.0.1"));
    if (!loopback.isLoopback())
        return 2;

    QMatrix4x4 transform;
    transform.translate(1.0f, 2.0f, 3.0f);
    if (transform.map(QVector3D(0.0f, 0.0f, 0.0f)) != QVector3D(1.0f, 2.0f, 3.0f))
        return 3;

    // QtGui: verify the module loads and image operations work without an
    // OpenGL context (the OHOS offscreen platform plugin lacks one).
    QLibrary gui("Qt5Gui");
    if (!gui.load())
        return 4;
    gui.unload();

    QImage image(2, 2, QImage::Format_ARGB32);
    image.fill(Qt::red);
    if (image.pixelColor(0, 0) != QColor(Qt::red))
        return 5;

    // QtWidgets: construct a widget hierarchy (links Qt5::Widgets and its
    // requires chain Widgets -> Gui -> Core).
    QWidget window;
    QLabel label(&window);
    label.setText(QStringLiteral("qt5-qtbase components"));
    window.resize(200, 100);
    window.show();

    // QtXml: parse a document (links Qt5::Xml, requires Qt5Core).
    QDomDocument doc;
    if (!doc.setContent(QStringLiteral("<root><item>1</item></root>")))
        return 6;
    if (doc.documentElement().tagName() != QStringLiteral("root"))
        return 7;

    // QtPrintSupport: create a printer object (links Qt5::PrintSupport,
    // requires Widgets -> Gui -> Core).
    QPrinter printer(QPrinter::HighResolution);
    Q_UNUSED(printer);

    QTest::qWait(1);
    return 0;
}
