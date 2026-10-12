/* Consumer smoke test for qt5-qtwebsockets 5.15.2 on OpenHarmony.
 *
 * Runs a real RFC 6455 echo round trip over the 127.0.0.1 loopback:
 * QWebSocketServer listens on an ephemeral port, a QWebSocket client
 * connects, sends a text message, and asserts the server-side echo comes
 * back with identical payload.  Also checks QWebSocketCorsAuthenticator
 * (origin/allowed getters + copy ctor) and QWebSocketProtocol::Version13
 * as non-network API coverage.
 */
#include <QCoreApplication>
#include <QHostAddress>
#include <QObject>
#include <QString>
#include <QTimer>
#include <QtWebSockets/QWebSocket>
#include <QtWebSockets/QWebSocketCorsAuthenticator>
#include <QtWebSockets/QWebSocketProtocol>
#include <QtWebSockets/QWebSocketServer>
#include <iostream>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // ── 1) QWebSocketCorsAuthenticator API coverage ──────────────────
    // (documented default: allowed() returns true — every origin accepted)
    QWebSocketCorsAuthenticator cors(QString::fromLatin1("http://example.com"));
    if (cors.origin() != QLatin1String("http://example.com")) {
        std::cerr << "FAIL: cors origin mismatch" << std::endl;
        return 1;
    }
    if (!cors.allowed()) {
        std::cerr << "FAIL: cors should default to allowed" << std::endl;
        return 1;
    }
    cors.setAllowed(false);
    if (cors.allowed()) {
        std::cerr << "FAIL: cors setAllowed(false) ignored" << std::endl;
        return 1;
    }
    QWebSocketCorsAuthenticator corsCopy(cors);
    if (corsCopy.allowed() || corsCopy.origin() != cors.origin()) {
        std::cerr << "FAIL: cors copy ctor broken" << std::endl;
        return 1;
    }

    // ── 2) QWebSocketProtocol version enum ───────────────────────────
    if (QWebSocketProtocol::VersionLatest != QWebSocketProtocol::Version13) {
        std::cerr << "FAIL: expected RFC 6455 (v13) as latest" << std::endl;
        return 1;
    }

    // ── 3) Loopback echo round trip ──────────────────────────────────
    QWebSocketServer server(
        QString::fromLatin1("smoke"), QWebSocketServer::NonSecureMode);
    if (!server.listen(QHostAddress::LocalHost, 0)) {
        std::cerr << "FAIL: server cannot listen on loopback: "
                  << server.errorString().toStdString() << std::endl;
        return 1;
    }
    if (!server.isListening() || server.serverPort() == 0) {
        std::cerr << "FAIL: server not listening" << std::endl;
        return 1;
    }
    QObject::connect(&server, &QWebSocketServer::newConnection, [&server]() {
        QWebSocket *conn = server.nextPendingConnection();
        if (!conn)
            return;
        QObject::connect(
            conn, &QWebSocket::textMessageReceived,
            [conn](const QString &msg) { conn->sendTextMessage(msg); });
        QObject::connect(conn, &QWebSocket::disconnected,
                         conn, &QWebSocket::deleteLater);
    });

    QWebSocket client;
    int result = 1;
    QObject::connect(&client,
                     &QWebSocket::connected,
                     [&client]() {
                         client.sendTextMessage(
                             QString::fromLatin1("hello-qtwebsockets-ohos"));
                     });
    QObject::connect(
        &client, &QWebSocket::textMessageReceived, [&](const QString &msg) {
            if (msg == QLatin1String("hello-qtwebsockets-ohos")) {
                std::cout << "PASS: echo round trip over 127.0.0.1: "
                          << msg.toStdString() << std::endl;
                result = 0;
            } else {
                std::cerr << "FAIL: echoed payload mismatch: "
                          << msg.toStdString() << std::endl;
            }
            client.close(QWebSocketProtocol::CloseCodeNormal);
            QCoreApplication::exit(result);
        });
    QObject::connect(
        &client,
        QOverload<QAbstractSocket::SocketError>::of(&QWebSocket::error),
        [&](QAbstractSocket::SocketError err) {
            std::cerr << "FAIL: client error " << err << ": "
                      << client.errorString().toStdString() << std::endl;
            QCoreApplication::exit(1);
        });
    QTimer::singleShot(15000, [&]() {
        std::cerr << "FAIL: echo round trip timed out" << std::endl;
        QCoreApplication::exit(1);
    });

    client.open(server.serverUrl());
    if (QCoreApplication::exec() != 0 || result != 0) {
        return 1;
    }
    std::cout << "PASS: qt5-qtwebsockets consumer smoke test completed"
              << std::endl;
    return 0;
}
