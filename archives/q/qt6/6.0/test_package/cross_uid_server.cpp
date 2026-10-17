#include <QCoreApplication>
#include <QLocalServer>
#include <QLocalSocket>
#include <QString>
#include <QTimer>
#include <QUuid>

#include <sys/types.h>
#include <unistd.h>

#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    bool secondsOk = false;
    int waitSeconds = app.arguments().value(1, QStringLiteral("120")).toInt(&secondsOk);
    if (!secondsOk || waitSeconds < 10 || waitSeconds > 300)
        waitSeconds = 120;

    const QString serverName = QStringLiteral("qt6-cross-uid-")
        + QUuid::createUuid().toString(QUuid::WithoutBraces).remove(QLatin1Char('-'));
    QLocalServer server;
    int deliveredConnections = 0;

    QObject::connect(&server, &QLocalServer::newConnection, &app, [&] {
        while (server.hasPendingConnections()) {
            QLocalSocket *socket = server.nextPendingConnection();
            if (!socket)
                continue;

            ++deliveredConnections;
            std::printf("SERVER_QT_CONNECTION_DELIVERED=1\n");
            std::fflush(stdout);
            QObject::connect(socket, &QLocalSocket::readyRead, socket, [socket, &app] {
                const QByteArray payload = socket->readAll();
                const QByteArray response = QByteArrayLiteral("Qt6 echo:") + payload;
                std::printf("SERVER_QT_PAYLOAD_BYTES=%lld\n",
                            static_cast<long long>(payload.size()));
                std::fflush(stdout);
                socket->write(response);
                socket->flush();
                socket->waitForBytesWritten(3000);
                socket->disconnectFromServer();
                QTimer::singleShot(100, &app, &QCoreApplication::quit);
            });
        }
    });

    if (!server.listen(serverName)) {
        std::fprintf(stderr, "SERVER_LISTEN_FAILED=%s\n",
                     qPrintable(server.errorString()));
        return 2;
    }

    const QByteArray fullName = server.fullServerName().toUtf8();
    std::printf("SERVER_UID=%lu\nSERVER_NAME=%s\nSERVER_FULL_NAME=%s\nSERVER_READY=1\n",
                static_cast<unsigned long>(::geteuid()), qPrintable(serverName),
                fullName.constData());
    std::fflush(stdout);

    QTimer::singleShot(waitSeconds * 1000, &app, &QCoreApplication::quit);
    app.exec();

    server.close();
    QLocalServer::removeServer(serverName);
    std::printf("SERVER_QT_DELIVERED_COUNT=%d\n", deliveredConnections);
    if (deliveredConnections == 0) {
        std::puts("SERVER_RESULT=NO_QT_CONNECTION_DELIVERED");
        return 0;
    }
    std::puts("SERVER_RESULT=QT_CONNECTION_DELIVERED");
    return 3;
}
