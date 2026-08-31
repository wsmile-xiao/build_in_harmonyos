#include <QApplication>
#include <QColor>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDomDocument>
#include <QHostAddress>
#include <QImage>
#include <QPainter>
#include <QSizePolicy>
#include <QWidget>
#include <QtGlobal>

#include <cstdio>

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication application(argc, argv);
    if (application.platformName() != "offscreen")
        return 1;

    QWidget widget;
    widget.resize(16, 16);
    widget.show();
    application.processEvents();
    if (!widget.isVisible())
        return 2;

    const QColor color("#336699");
    if (!color.isValid())
        return 3;
    if (color.red() != 0x33 || color.green() != 0x66 || color.blue() != 0x99)
        return 4;

    const QHostAddress loopback(QHostAddress::LocalHost);
    if (!loopback.isLoopback())
        return 5;

    const QSizePolicy policy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    if (policy.horizontalPolicy() != QSizePolicy::Preferred)
        return 6;
    if (policy.verticalPolicy() != QSizePolicy::Expanding)
        return 7;

    QImage image(8, 8, QImage::Format_ARGB32_Premultiplied);
    if (image.isNull())
        return 8;
    image.fill(Qt::transparent);
    QPainter painter(&image);
    painter.fillRect(image.rect(), color);
    painter.end();
    if (image.pixelColor(4, 4) != color)
        return 9;

    QDomDocument document("qtbase-test");
    QDomElement root = document.createElement("root");
    QDomElement value = document.createElement("value");
    value.appendChild(document.createTextNode("42"));
    root.appendChild(value);
    document.appendChild(root);
    if (document.documentElement().tagName() != "root")
        return 10;
    if (document.documentElement().firstChildElement("value").text() != "42")
        return 11;

    // Qt6DBus 组件验证（非阻塞契约）：QDBusMessage 的静态构造与属性检查
    // 不连接 session bus、不阻塞等待回复；OHOS 无系统 DBus daemon 也能通过。
    const QDBusMessage dbusCall = QDBusMessage::createMethodCall(
        QStringLiteral("org.freedesktop.DBus"),
        QStringLiteral("/"),
        QStringLiteral("org.freedesktop.DBus"),
        QStringLiteral("ListNames"));
    if (dbusCall.type() != QDBusMessage::MethodCallMessage)
        return 12;
    if (dbusCall.service() != QStringLiteral("org.freedesktop.DBus"))
        return 13;
    // QDBusConnection::sessionBus() 非阻塞地构造连接对象（不建立实际连接、
    // 不等待 daemon），验证 Qt6DBus 头文件与库可被消费。注意 OHOS 无系统
    // DBus session daemon，故不检查连接状态/会话名，仅验证对象可构造。
    QDBusConnection::sessionBus();

    std::printf(
        "Qt %s offscreen QPA, raster painting, XML, and Qt6DBus work\n",
        QT_VERSION_STR
    );
    return 0;
}
