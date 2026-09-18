#include <QAbstractSocket>
#include <QCoreApplication>
#include <QHostAddress>
#include <QTimer>
#include <QUrl>
#include <QtWebSockets/QWebSocket>
#include <QtWebSockets/QWebSocketServer>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QWebSocketServer server(QStringLiteral("qtwebsockets-test"),
                            QWebSocketServer::NonSecureMode);
    if (!server.listen(QHostAddress::LocalHost, 0))
        return 1;

    QWebSocket client;
    const QString payload = QStringLiteral("openharmony-websocket-loopback");
    int result = 5;

    QObject::connect(&server, &QWebSocketServer::newConnection, [&]() {
        QWebSocket *socket = server.nextPendingConnection();
        if (!socket) {
            result = 2;
            app.quit();
            return;
        }

        QObject::connect(socket, &QWebSocket::textMessageReceived, socket,
                         [socket](const QString &message) {
                             socket->sendTextMessage(
                                 QStringLiteral("echo:") + message);
                             socket->close();
                         });
        QObject::connect(socket, &QWebSocket::disconnected, socket,
                         &QObject::deleteLater);
    });

    QObject::connect(&client, &QWebSocket::connected, [&]() {
        client.sendTextMessage(payload);
    });
    QObject::connect(&client, &QWebSocket::textMessageReceived,
                     [&](const QString &message) {
                         result = (message == QStringLiteral("echo:") + payload)
                                      ? 0
                                      : 3;
                         client.close();
                         server.close();
                         app.quit();
                     });
    QObject::connect(&client,
                     qOverload<QAbstractSocket::SocketError>(
                         &QWebSocket::errorOccurred),
                     [&](QAbstractSocket::SocketError) {
                         result = 4;
                         app.quit();
                     });

    QTimer::singleShot(5000, &app, [&]() {
        result = 6;
        client.abort();
        server.close();
        app.quit();
    });

    const QUrl url(QStringLiteral("ws://127.0.0.1:%1")
                       .arg(server.serverPort()));
    client.open(url);
    app.exec();
    return result;
}
