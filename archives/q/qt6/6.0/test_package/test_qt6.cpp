#if defined(__OHOS__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE
#endif

#include <QApplication>
#include <QColor>
#include <QCoreApplication>
#include <QDomDocument>
#include <QElapsedTimer>
#include <QFile>
#include <QHostAddress>
#include <QIODevice>
#include <QImage>
#include <QLocalServer>
#include <QLocalSocket>
#include <QMetaObject>
#include <QPainter>
#include <QPaintEvent>
#include <QProcess>
#include <QSslCipher>
#include <QSslCertificate>
#include <QSslConfiguration>
#include <QSslKey>
#include <QSslSocket>
#include <QThread>
#include <QTcpServer>
#include <QTcpSocket>
#include <QTimer>
#include <QUuid>
#include <QWidget>
#include <QtGlobal>

#include <cerrno>
#include <cstddef>
#include <cstdio>
#include <cstring>

#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <unistd.h>

namespace {

int checkCount = 0;

bool check(bool passed, const char *description)
{
    ++checkCount;
    if (!passed)
        std::fprintf(stderr, "FAIL: %s\n", description);
    return passed;
}

bool readExactly(QIODevice *device, qsizetype expectedSize, QByteArray *result)
{
    QElapsedTimer deadline;
    deadline.start();
    result->clear();
    while (result->size() < expectedSize) {
        if (device->bytesAvailable() == 0) {
            const int remaining = 5000 - int(deadline.elapsed());
            if (remaining <= 0 || !device->waitForReadyRead(remaining))
                return false;
        }
        result->append(device->read(expectedSize - result->size()));
    }
    return true;
}

int runLocalSocketClientMode(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    QLocalSocket client;
    const QString serverName = QString::fromLocal8Bit(argv[2]);
    client.connectToServer(serverName);
    if (!client.waitForConnected(5000)) {
        std::fprintf(stderr, "process client could not connect: %s\n",
                     qPrintable(client.errorString()));
        return 21;
    }

    const QByteArray payload("Qt 6 HarmonyOS cross-process payload");
    if (client.write(payload) != payload.size() || !client.waitForBytesWritten(5000)) {
        std::fprintf(stderr, "process client could not send its payload\n");
        return 22;
    }

    QByteArray response;
    if (!readExactly(&client, payload.size() + 4, &response)
        || response != QByteArray("ack:") + payload) {
        std::fprintf(stderr, "process client received an invalid response\n");
        return 23;
    }

    std::printf("HarmonyOS separate-process client exchanged %lld bytes\n",
                static_cast<long long>(payload.size()));
    return 0;
}

bool testHarmonyOSProcessLocalSocket()
{
    const QString name = QStringLiteral("qt6-process-") + QString::number(getpid())
        + QLatin1Char('-') + QUuid::createUuid().toString(QUuid::WithoutBraces);
    QLocalServer server;
    if (!check(server.listen(name), "listen for cross-process named local socket")) {
        std::fprintf(stderr, "cross-process QLocalServer::listen failed: %s\n",
                     qPrintable(server.errorString()));
        return false;
    }

    QProcess clientProcess;
    clientProcess.start(QCoreApplication::applicationFilePath(),
                        {QStringLiteral("--harmonyos-local-socket-client"),
                         server.fullServerName()});
    if (!check(clientProcess.waitForStarted(5000),
               "start separate Qt local-socket client process")) {
        std::fprintf(stderr, "QProcess start failed: %s\n",
                     qPrintable(clientProcess.errorString()));
        return false;
    }
    if (!check(clientProcess.processId() != getpid(),
               "local-socket client runs in a distinct process"))
        return false;
    if (!check(server.waitForNewConnection(5000),
               "accept a separate-process local-socket client"))
        return false;

    QLocalSocket *peer = server.nextPendingConnection();
    if (!check(peer != nullptr, "obtain separate-process accepted socket"))
        return false;

    struct ucred credentials {};
    socklen_t credentialsLength = sizeof(credentials);
    const int credentialResult = ::getsockopt(
        static_cast<int>(peer->socketDescriptor()), SOL_SOCKET, SO_PEERCRED,
        &credentials, &credentialsLength);
    if (!check(credentialResult == 0,
               "read SO_PEERCRED for separate-process client"))
        return false;
    if (!check(credentialsLength == sizeof(credentials),
               "separate-process peer credentials have the expected size"))
        return false;
    if (!check(credentials.uid == ::geteuid(),
               "separate-process peer uid matches the effective uid"))
        return false;

    const QByteArray payload("Qt 6 HarmonyOS cross-process payload");
    QByteArray received;
    if (!check(readExactly(peer, payload.size(), &received),
               "receive payload from separate-process client"))
        return false;
    if (!check(received == payload,
               "verify exact separate-process client payload"))
        return false;

    const QByteArray response = QByteArray("ack:") + received;
    if (!check(peer->write(response) == response.size(),
               "write response to separate-process client"))
        return false;
    if (!check(peer->waitForBytesWritten(5000),
               "flush response to separate-process client"))
        return false;
    if (!check(clientProcess.waitForFinished(5000),
               "wait for separate-process client completion")) {
        clientProcess.kill();
        clientProcess.waitForFinished(1000);
        return false;
    }
    if (!check(clientProcess.exitStatus() == QProcess::NormalExit
                   && clientProcess.exitCode() == 0,
               "separate-process client validates the response and exits cleanly")) {
        std::fprintf(stderr, "process client exit=%d status=%d stderr=%s\n",
                     clientProcess.exitCode(), int(clientProcess.exitStatus()),
                     clientProcess.readAllStandardError().constData());
        delete peer;
        return false;
    }

    peer->close();
    delete peer;
    server.close();
    std::printf("HarmonyOS separate-process local socket exchanged %lld bytes\n",
                static_cast<long long>(received.size()));
    return true;
}

bool testHarmonyOSNamedLocalSocket()
{
    if (!testHarmonyOSProcessLocalSocket())
        return false;

    const QString name = QStringLiteral("qt6-harmony-") + QString::number(getpid())
        + QLatin1Char('-') + QUuid::createUuid().toString(QUuid::WithoutBraces);
    const QString alias = QStringLiteral("./") + name;
    QLocalServer server;
    if (!check(server.listen(name), "listen through QLocalServer named API")) {
        std::fprintf(stderr, "QLocalServer::listen failed: %s\n",
                     qPrintable(server.errorString()));
        return false;
    }
    if (!check(server.serverName() == name,
               "server retains the caller's relative name"))
        return false;
    if (!check(server.fullServerName().startsWith(QStringLiteral("@qt6:")),
               "server exposes the HarmonyOS abstract endpoint"))
        return false;

    QLocalSocket client;
    client.connectToServer(alias);
    if (!check(client.waitForConnected(5000),
               "connect through normalized QLocalSocket name alias")) {
        std::fprintf(stderr, "QLocalSocket::connectToServer failed: %s\n",
                     qPrintable(client.errorString()));
        return false;
    }
    if (!check(client.serverName() == alias,
               "client retains the caller's normalized alias"))
        return false;
    if (!check(client.fullServerName() == server.fullServerName(),
               "client and server resolve the same abstract endpoint"))
        return false;

    if (!check(server.waitForNewConnection(5000), "accept named local connection"))
        return false;
    QLocalSocket *peer = server.nextPendingConnection();
    if (!check(peer != nullptr, "obtain accepted QLocalSocket"))
        return false;

    struct ucred credentials {};
    socklen_t credentialsLength = sizeof(credentials);
    const int credentialResult = ::getsockopt(
        static_cast<int>(peer->socketDescriptor()), SOL_SOCKET, SO_PEERCRED,
        &credentials, &credentialsLength);
    if (!check(credentialResult == 0, "read accepted socket SO_PEERCRED"))
        return false;
    if (!check(credentialsLength == sizeof(credentials),
               "SO_PEERCRED returns a complete credential record"))
        return false;
    if (!check(credentials.uid == ::geteuid(),
               "accepted peer uid matches the effective uid"))
        return false;

    QLocalSocket fullNameClient;
    fullNameClient.connectToServer(server.fullServerName());
    if (!check(fullNameClient.waitForConnected(5000),
               "connect using the server's full abstract name"))
        return false;
    if (!check(fullNameClient.serverName() == server.fullServerName(),
               "full-name client retains the supplied address"))
        return false;
    if (!check(server.waitForNewConnection(5000),
               "accept a connection using the full abstract name"))
        return false;
    QLocalSocket *fullNamePeer = server.nextPendingConnection();
    if (!check(fullNamePeer != nullptr,
               "obtain the full-name client's accepted socket"))
        return false;

    const QByteArray firstChunk("HarmonyOS Qt ");
    const QByteArray secondChunk("6.0 abstract socket payload");
    const QByteArray payload = firstChunk + secondChunk;
    if (!check(client.write(firstChunk) == firstChunk.size(), "write first payload chunk"))
        return false;
    if (!check(client.waitForBytesWritten(5000), "flush first payload chunk"))
        return false;
    if (!check(client.write(secondChunk) == secondChunk.size(), "write second payload chunk"))
        return false;
    if (!check(client.waitForBytesWritten(5000), "flush second payload chunk"))
        return false;

    QByteArray received;
    if (!check(readExactly(peer, payload.size(), &received), "read complete named socket payload"))
        return false;
    if (!check(received == payload, "verify exact named socket payload"))
        return false;

    const QByteArray response = QByteArray("ack:") + received;
    if (!check(peer->write(response) == response.size(), "write named socket response"))
        return false;
    if (!check(peer->waitForBytesWritten(5000), "flush named socket response"))
        return false;
    QByteArray reply;
    if (!check(readExactly(&client, response.size(), &reply), "read complete named socket response"))
        return false;
    if (!check(reply == response, "verify exact named socket response"))
        return false;

    client.close();
    peer->close();
    delete peer;
    fullNameClient.close();
    fullNamePeer->close();
    delete fullNamePeer;
    server.close();

    QLocalSocket reconnect;
    reconnect.connectToServer(alias);
    if (!check(!reconnect.waitForConnected(1500),
               "closed abstract endpoint rejects a bounded reconnect"))
        return false;

    std::printf("HarmonyOS QLocalServer/QLocalSocket payload '%s' (%lld bytes); closed endpoint rejected reconnect\n",
                received.constData(),
                static_cast<long long>(received.size()));
    return true;
}

bool testOpenSsl3TlsLoopback()
{
    if (!check(QSslSocket::supportsSsl(), "load the OpenSSL runtime")) {
        std::fprintf(stderr, "QSslSocket runtime: %s\n",
                     qPrintable(QSslSocket::sslLibraryVersionString()));
        return false;
    }

    const QString sslVersion = QSslSocket::sslLibraryVersionString();
    if (!check(sslVersion.startsWith(QStringLiteral("OpenSSL 3.")),
               "use the HarmonyOS OpenSSL 3 runtime")) {
        std::fprintf(stderr, "unexpected OpenSSL runtime: %s\n",
                     qPrintable(sslVersion));
        return false;
    }

    QFile certificateFile(QCoreApplication::applicationDirPath()
                          + QStringLiteral("/selfsigned-server.crt"));
    QFile privateKeyFile(QCoreApplication::applicationDirPath()
                         + QStringLiteral("/selfsigned-server.key"));
    if (!check(certificateFile.open(QIODevice::ReadOnly),
               "open TLS loopback certificate"))
        return false;
    if (!check(privateKeyFile.open(QIODevice::ReadOnly),
               "open TLS loopback private key"))
        return false;

    const QSslCertificate certificate(certificateFile.readAll(), QSsl::Pem);
    const QSslKey privateKey(privateKeyFile.readAll(), QSsl::Rsa, QSsl::Pem,
                             QSsl::PrivateKey);
    if (!check(!certificate.isNull(), "parse TLS loopback certificate"))
        return false;
    if (!check(!privateKey.isNull(), "parse TLS loopback private key"))
        return false;

    const int listener = ::socket(AF_INET, SOCK_STREAM, 0);
    if (!check(listener >= 0, "create TLS loopback listener"))
        return false;

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = 0;
    if (::bind(listener, reinterpret_cast<sockaddr *>(&address), sizeof(address)) != 0
        || ::listen(listener, 1) != 0) {
        ::close(listener);
        return check(false, "bind TLS loopback listener to an ephemeral port");
    }

    socklen_t addressLength = sizeof(address);
    if (::getsockname(listener, reinterpret_cast<sockaddr *>(&address),
                      &addressLength) != 0) {
        ::close(listener);
        return check(false, "read TLS loopback listener port");
    }

    const int clientDescriptor = ::socket(AF_INET, SOCK_STREAM, 0);
    if (clientDescriptor < 0) {
        ::close(listener);
        return check(false, "create TLS loopback client socket");
    }
    if (::connect(clientDescriptor, reinterpret_cast<sockaddr *>(&address),
                  sizeof(address)) != 0) {
        ::close(clientDescriptor);
        ::close(listener);
        return check(false, "connect TLS loopback client socket");
    }

    const int serverDescriptor = ::accept(listener, nullptr, nullptr);
    ::close(listener);
    if (!check(serverDescriptor >= 0, "accept TLS loopback client socket")) {
        ::close(clientDescriptor);
        return false;
    }

    QSslSocket client;
    QSslSocket server;
    if (!check(client.setSocketDescriptor(clientDescriptor,
                                           QAbstractSocket::ConnectedState),
               "adopt TLS loopback client descriptor")) {
        ::close(clientDescriptor);
        ::close(serverDescriptor);
        return false;
    }
    if (!check(server.setSocketDescriptor(serverDescriptor,
                                           QAbstractSocket::ConnectedState),
               "adopt TLS loopback server descriptor")) {
        ::close(serverDescriptor);
        return false;
    }

    QSslConfiguration clientConfiguration = client.sslConfiguration();
    clientConfiguration.setPeerVerifyMode(QSslSocket::VerifyNone);
    client.setSslConfiguration(clientConfiguration);
    server.setLocalCertificate(certificate);
    server.setPrivateKey(privateKey);
    server.setPeerVerifyMode(QSslSocket::VerifyNone);

    server.startServerEncryption();
    client.startClientEncryption();
    QElapsedTimer handshakeDeadline;
    handshakeDeadline.start();
    while ((!client.isEncrypted() || !server.isEncrypted())
           && handshakeDeadline.elapsed() < 10000) {
        QCoreApplication::processEvents();
        QThread::msleep(1);
    }
    if (!check(client.isEncrypted() && server.isEncrypted(),
               "complete OpenSSL 3 TLS loopback handshake")) {
        std::fprintf(stderr, "TLS client=%s server=%s\n",
                     qPrintable(client.errorString()), qPrintable(server.errorString()));
        return false;
    }
    if (!check(!client.sessionCipher().name().isEmpty()
                   && !server.sessionCipher().name().isEmpty(),
               "negotiate a TLS cipher on both peers"))
        return false;

    const QByteArray payload("HarmonyOS OpenSSL 3 TLS payload");
    if (!check(client.write(payload) == payload.size(), "write encrypted TLS payload"))
        return false;
    QElapsedTimer payloadDeadline;
    payloadDeadline.start();
    while (server.bytesAvailable() < payload.size() && payloadDeadline.elapsed() < 5000) {
        QCoreApplication::processEvents();
        QThread::msleep(1);
    }
    const QByteArray received = server.readAll();
    if (!check(received == payload, "receive exact decrypted TLS payload"))
        return false;

    const QByteArray response = QByteArray("ack:") + received;
    if (!check(server.write(response) == response.size(), "write encrypted TLS response"))
        return false;
    payloadDeadline.restart();
    while (client.bytesAvailable() < response.size() && payloadDeadline.elapsed() < 5000) {
        QCoreApplication::processEvents();
        QThread::msleep(1);
    }
    if (!check(client.readAll() == response, "receive exact decrypted TLS response"))
        return false;

    std::printf("HarmonyOS TLS loopback negotiated %s and exchanged %lld bytes\n",
                qPrintable(client.sessionCipher().name()),
                static_cast<long long>(received.size()));
    return true;
}

class RasterWidget : public QWidget
{
protected:
    void paintEvent(QPaintEvent *) override
    {
        QPainter painter(this);
        painter.fillRect(rect(), QColor(0x33, 0x66, 0x99));
    }
};

} // namespace

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", QByteArrayLiteral("offscreen"));
    if (argc == 3
        && std::strcmp(argv[1], "--harmonyos-local-socket-client") == 0)
        return runLocalSocketClientMode(argc, argv);
    QApplication application(argc, argv);

    if (!check(application.platformName() == QStringLiteral("offscreen"),
               "select the installed offscreen QPA plugin"))
        return 1;
    if (!check(std::strcmp(application.metaObject()->className(), "QApplication") == 0,
               "read QApplication meta-object"))
        return 1;

    bool timerDelivered = false;
    QTimer::singleShot(0, &application, [&timerDelivered] { timerDelivered = true; });
    application.processEvents();
    if (!check(timerDelivered, "deliver a Core event-loop timer"))
        return 1;

    const QHostAddress loopback(QHostAddress::LocalHost);
    if (!check(loopback.isLoopback(), "classify the local host as loopback"))
        return 1;

    QTcpServer tcpServer;
    if (!check(tcpServer.listen(QHostAddress::LocalHost, 0), "listen on an ephemeral TCP port"))
        return 1;
    QTcpSocket tcpClient;
    tcpClient.connectToHost(QHostAddress::LocalHost, tcpServer.serverPort());
    if (!check(tcpClient.waitForConnected(3000), "connect Qt TCP client to local server"))
        return 1;
    if (!check(tcpServer.waitForNewConnection(3000), "accept Qt TCP client"))
        return 1;
    QTcpSocket *tcpPeer = tcpServer.nextPendingConnection();
    if (!check(tcpPeer != nullptr, "obtain accepted Qt TCP socket"))
        return 1;
    const QByteArray tcpPayload("Qt Network loopback exchange");
    if (!check(tcpClient.write(tcpPayload) == tcpPayload.size(), "write Qt TCP payload"))
        return 1;
    if (!check(tcpClient.waitForBytesWritten(3000), "flush Qt TCP payload"))
        return 1;
    QByteArray tcpReceived;
    if (!check(readExactly(tcpPeer, tcpPayload.size(), &tcpReceived), "receive complete Qt TCP payload"))
        return 1;
    if (!check(tcpReceived == tcpPayload, "verify exact Qt TCP payload"))
        return 1;
    const QByteArray tcpResponse("Qt TCP response");
    if (!check(tcpPeer->write(tcpResponse) == tcpResponse.size(), "write Qt TCP response"))
        return 1;
    if (!check(tcpPeer->waitForBytesWritten(3000), "flush Qt TCP response"))
        return 1;
    QByteArray tcpReply;
    if (!check(readExactly(&tcpClient, tcpResponse.size(), &tcpReply), "receive complete Qt TCP response"))
        return 1;
    if (!check(tcpReply == tcpResponse, "verify exact Qt TCP response"))
        return 1;
    delete tcpPeer;

    const QColor color(0x33, 0x66, 0x99);
    QImage image(16, 16, QImage::Format_ARGB32_Premultiplied);
    if (!check(!image.isNull(), "allocate raster image"))
        return 1;
    image.fill(Qt::transparent);
    QPainter imagePainter(&image);
    if (!check(imagePainter.isActive(), "activate image raster painter"))
        return 1;
    imagePainter.fillRect(image.rect(), color);
    imagePainter.end();
    if (!check(image.pixelColor(8, 8) == color, "read back raster-painted pixel"))
        return 1;

    RasterWidget widget;
    widget.resize(16, 16);
    widget.show();
    application.processEvents();
    if (!check(widget.isVisible(), "show widget under offscreen QPA"))
        return 1;
    QImage rendered(widget.size(), QImage::Format_ARGB32_Premultiplied);
    rendered.fill(Qt::transparent);
    QPainter widgetPainter(&rendered);
    if (!check(widgetPainter.isActive(), "activate widget render painter"))
        return 1;
    widget.render(&widgetPainter);
    widgetPainter.end();
    if (!check(rendered.pixelColor(8, 8) == color, "render widget into raster image"))
        return 1;

    QDomDocument document;
    QString xmlError;
    int errorLine = 0;
    int errorColumn = 0;
    if (!check(document.setContent(QStringLiteral("<root><value>42</value></root>"),
                                   &xmlError, &errorLine, &errorColumn),
               "parse valid XML"))
        return 1;
    if (!check(document.documentElement().tagName() == QStringLiteral("root")
                   && document.documentElement().firstChildElement(QStringLiteral("value")).text()
                       == QStringLiteral("42"),
               "read XML document value"))
        return 1;
    QDomDocument malformed;
    if (!check(!malformed.setContent(QStringLiteral("<root>"),
                                     &xmlError, &errorLine, &errorColumn),
               "reject malformed XML"))
        return 1;

    QThread worker;
    worker.start();
    if (!check(worker.isRunning(), "start Qt worker thread"))
        return 1;
    worker.terminate();
    QThread::msleep(50);
    if (!check(worker.isRunning(), "leave thread running when cancellation is unavailable"))
        return 1;
    worker.quit();
    if (!check(worker.wait(3000), "cooperatively quit and join Qt worker thread"))
        return 1;

    if (!testHarmonyOSNamedLocalSocket())
        return 1;
    if (!testOpenSsl3TlsLoopback())
        return 1;

    std::printf("Qt %s: %d checks passed (Core, Network, raster Gui, offscreen Widgets, Xml)\n",
                QT_VERSION_STR, checkCount);
    return 0;
}
