/* Smoke test for libkcddb on HarmonyOS PC.
 *
 * Exercises the offline-capable core of the library:
 *  - KCDDB::CDInfo construction, field get/set and CDDB toString() round trip
 *  - KCDDB::Genres / KCDDB::Categories helpers
 *  - The rewritten HTTP transport layer (KIO -> QNetworkAccessManager) against
 *    a local loopback HTTP server: covers the QEventLoop sync-wait, the
 *    zero-arg slot + qobject_cast<QNetworkReply*>(sender()) path, readAll()
 *    body handling, reply cleanup, HTTP error -> ServerError mapping and the
 *    CDDB protocol parsing after the fetch. No external network is involved
 *    (the AI review requested transport coverage without internet access).
 */
#include <kcddb/CDInfo>
#include <kcddb/Client>
#include <kcddb/Config>
#include <kcddb/categories.h>
#include <kcddb/genres.h>

#include <QCoreApplication>
#include <QDebug>
#include <QString>
#include <QStringList>
#include <QTcpServer>
#include <QTcpSocket>
#include <QVariant>

#include <cstdio>

// Minimal single-shot HTTP/1.1 server on the loopback interface. It answers
// every request with the same pre-baked body/status so the KCDDB transport
// can be exercised without any external network.
class LoopbackHttpServer : public QObject
{
    Q_OBJECT
public:
    explicit LoopbackHttpServer(const QByteArray &body, const char *statusLine,
                                QObject *parent = nullptr)
        : QObject(parent), m_body(body), m_statusLine(statusLine)
    {
        m_server = new QTcpServer(this);
        if (!m_server->listen(QHostAddress::LocalHost)) {
            qWarning() << "FAIL: loopback server cannot listen:" << m_server->errorString();
            return;
        }
        connect(m_server, &QTcpServer::newConnection,
                this, &LoopbackHttpServer::handleConnection);
    }

    bool isListening() const { return m_server->isListening(); }
    quint16 port() const { return m_server->serverPort(); }

    bool sawRequest() const { return !m_lastRequest.isEmpty(); }
    QByteArray lastRequest() const { return m_lastRequest; }

private Q_SLOTS:
    void handleConnection()
    {
        QTcpSocket *socket = m_server->nextPendingConnection();
        if (!socket)
            return;
        connect(socket, &QTcpSocket::disconnected, socket, &QTcpSocket::deleteLater);
        connect(socket, &QTcpSocket::readyRead, this, [this, socket]() {
            m_lastRequest += socket->readAll();
            // Only answer once the request line is complete.
            if (!m_lastRequest.contains("\r\n\r\n")
                && !m_lastRequest.contains('\n'))
                return;
            QByteArray response;
            response += m_statusLine;
            response += "\r\n";
            response += "Content-Type: text/plain\r\n";
            response += "Content-Length: " + QByteArray::number(m_body.size()) + "\r\n";
            response += "Connection: close\r\n";
            response += "\r\n";
            response += m_body;
            socket->write(response);
            socket->flush();
            socket->disconnectFromHost();
        });
    }

private:
    QTcpServer *m_server = nullptr;
    QByteArray m_body;
    const char *m_statusLine = nullptr;
    QByteArray m_lastRequest;
};

static KCDDB::TrackOffsetList sampleOffsets()
{
    KCDDB::TrackOffsetList list;
    list << 150 << 61408 << 177675;  // same offsets as upstream utf8test
    return list;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // ---- CDInfo field storage / retrieval ----
    KCDDB::CDInfo info;
    info.set(KCDDB::Artist, QString::fromUtf8("Test Artist"));
    info.set(KCDDB::Title, QString::fromUtf8("Test Title"));
    info.set(KCDDB::Category, QString::fromUtf8("rock"));
    info.set(KCDDB::Genre, QString::fromUtf8("Rock"));
    info.set(KCDDB::Year, 2026);
    info.set(QLatin1String("discid"), QString::fromUtf8("13093f02"));

    if (info.get(KCDDB::Artist).toString() != QString::fromUtf8("Test Artist")) {
        qWarning() << "FAIL: artist roundtrip";
        return 1;
    }
    if (info.get(KCDDB::Title).toString() != QString::fromUtf8("Test Title")) {
        qWarning() << "FAIL: title roundtrip";
        return 1;
    }
    if (info.get(KCDDB::Year).toInt() != 2026) {
        qWarning() << "FAIL: year roundtrip";
        return 1;
    }

    // ---- CDInfo CDDB protocol serialization (toString) ----
    const QString rendered = info.toString();
    if (!rendered.contains(QString::fromUtf8("Test Title"))
        || !rendered.contains(QString::fromUtf8("Test Artist"))) {
        qWarning() << "FAIL: toString output missing fields:" << rendered;
        return 1;
    }

    // ---- CDInfo::load round trip from a CDDB-format string list ----
    KCDDB::CDInfo parsed;
    const QStringList xmcd = info.toString(true).split(QLatin1Char('\n'));
    if (!parsed.load(xmcd)) {
        qWarning() << "FAIL: CDInfo::load could not parse xmcd data";
        return 1;
    }
    if (parsed.get(KCDDB::Title).toString() != QString::fromUtf8("Test Title")) {
        qWarning() << "FAIL: loaded title mismatch:"
                   << parsed.get(KCDDB::Title).toString();
        return 1;
    }

    // ---- Genres / Categories helpers ----
    KCDDB::Categories categories;
    const QStringList categoryList = categories.cddbList();
    if (categoryList.isEmpty()) {
        qWarning() << "FAIL: cddb category list is empty";
        return 1;
    }
    if (!categoryList.contains(QString::fromUtf8("rock"))) {
        qWarning() << "FAIL: rock not in cddb category list" << categoryList;
        return 1;
    }
    if (categories.cddb2i18n(QString::fromUtf8("rock")).isEmpty()) {
        qWarning() << "FAIL: cddb2i18n(rock) empty";
        return 1;
    }

    KCDDB::Genres genres;
    const QStringList genreList = genres.cddbList();
    if (genreList.isEmpty()) {
        qWarning() << "FAIL: cddb genre list is empty";
        return 1;
    }
    if (genres.cddb2i18n(genreList.first()).isEmpty()) {
        qWarning() << "FAIL: cddb2i18n(first genre) empty";
        return 1;
    }

    // ===================================================================
    // Rewritten HTTP transport (KIO -> QNetworkAccessManager) coverage:
    // a loopback HTTP server answers the CDDB query, so the sync lookup
    // exercises fetchURL()'s QEventLoop wait, the zero-arg slotResult with
    // qobject_cast<QNetworkReply*>(sender()), readAll() body transfer,
    // deleteLater cleanup and the HTTP status -> Result mapping — all
    // without any external network.
    // ===================================================================

    // ---- transport: Success path (CDDB "200 found exact match") ----
    {
        // CDDB query response: "200<genre><discid>" -> Success + one match.
        LoopbackHttpServer okServer(
            QByteArrayLiteral("200 rock 13093f02\n"),
            "HTTP/1.1 200 OK");

        if (!okServer.isListening()) {
            qWarning() << "FAIL: loopback server did not start";
            return 1;
        }

        KCDDB::Client client;
        client.config().setCacheLookupEnabled(false);
        client.config().setFreedbLookupEnabled(true);
        client.config().setMusicBrainzLookupEnabled(false);
        client.config().setHostname(QString::fromLatin1("127.0.0.1"));
        client.config().setPort(okServer.port());
        client.config().setFreedbLookupTransport(1); // 1 = HTTP (EnumFreedbLookupTransport::HTTP)
        const KCDDB::Result r = client.lookup(sampleOffsets());

        if (r != KCDDB::Success) {
            qWarning() << "FAIL: loopback HTTP lookup expected Success, got"
                       << static_cast<int>(r);
            return 1;
        }
        if (!okServer.sawRequest()) {
            qWarning() << "FAIL: loopback server never received a request";
            return 1;
        }
        // The request must be a real CDDB CGI query with cmd/hello/proto.
        const QByteArray req = okServer.lastRequest();
        if (!req.contains("cmd=cddb%20query")
            || !req.contains("hello=")
            || !req.contains("proto=6")) {
            qWarning() << "FAIL: request is not a CDDB CGI query:" << req;
            return 1;
        }
    }

    // ---- transport: NoRecordFound path (CDDB "202 no match") ----
    {
        LoopbackHttpServer emptyServer(
            QByteArrayLiteral("202 No match for disc ID\n"),
            "HTTP/1.1 200 OK");

        if (!emptyServer.isListening()) {
            qWarning() << "FAIL: loopback server (202) did not start";
            return 1;
        }

        KCDDB::Client client;
        client.config().setCacheLookupEnabled(false);
        client.config().setFreedbLookupEnabled(true);
        client.config().setMusicBrainzLookupEnabled(false);
        client.config().setHostname(QString::fromLatin1("127.0.0.1"));
        client.config().setPort(emptyServer.port());
        client.config().setFreedbLookupTransport(1); // 1 = HTTP (EnumFreedbLookupTransport::HTTP)
        const KCDDB::Result r = client.lookup(sampleOffsets());

        if (r != KCDDB::NoRecordFound) {
            qWarning() << "FAIL: loopback 202 lookup expected NoRecordFound, got"
                       << static_cast<int>(r);
            return 1;
        }
    }

    // ---- transport: HTTP error -> ServerError mapping ----
    {
        LoopbackHttpServer errServer(
            QByteArrayLiteral("500 Internal Server Error"),
            "HTTP/1.1 500 Internal Server Error");

        if (!errServer.isListening()) {
            qWarning() << "FAIL: loopback server (500) did not start";
            return 1;
        }

        KCDDB::Client client;
        client.config().setCacheLookupEnabled(false);
        client.config().setFreedbLookupEnabled(true);
        client.config().setMusicBrainzLookupEnabled(false);
        client.config().setHostname(QString::fromLatin1("127.0.0.1"));
        client.config().setPort(errServer.port());
        client.config().setFreedbLookupTransport(1); // 1 = HTTP (EnumFreedbLookupTransport::HTTP)
        const KCDDB::Result r = client.lookup(sampleOffsets());

        if (r != KCDDB::ServerError) {
            qWarning() << "FAIL: loopback 500 lookup expected ServerError, got"
                       << static_cast<int>(r);
            return 1;
        }
    }

    // ---- transport: submit path (HTTP POST with custom headers) ----
    // Client::submit (blocking) -> SyncHTTPSubmit -> QNetworkAccessManager::post
    // with Category/Discid/User-Email/Submit-Mode/Charset raw headers. The
    // loopback server captures the POST so the header set and body are both
    // verified (AI review: "submit header loss" regression coverage).
    {
        LoopbackHttpServer submitServer(
            QByteArrayLiteral("320 OK, CDDB database has been updated\n"),
            "HTTP/1.1 200 OK");

        if (!submitServer.isListening()) {
            qWarning() << "FAIL: loopback server (submit) did not start";
            return 1;
        }

        KCDDB::CDInfo submitInfo;
        submitInfo.set(KCDDB::Artist, QString::fromUtf8("Submit Artist"));
        submitInfo.set(KCDDB::Title, QString::fromUtf8("Submit Title"));
        submitInfo.set(KCDDB::Category, QString::fromUtf8("rock"));
        submitInfo.set(QLatin1String("discid"), QString::fromUtf8("13093f02"));
        // track(0) auto-extends the track list (xmcd body needs tracks)
        submitInfo.track(0).set(KCDDB::Title, QString::fromUtf8("Track One"));

        KCDDB::Client client;
        client.config().setCacheLookupEnabled(false);
        client.config().setFreedbLookupEnabled(false);
        client.config().setMusicBrainzLookupEnabled(false);
        client.config().setEmailAddress(QString::fromLatin1("tester@example.org"));
        client.config().setHttpSubmitServer(QString::fromLatin1("127.0.0.1"));
        client.config().setHttpSubmitPort(submitServer.port());
        const KCDDB::Result r = client.submit(submitInfo, sampleOffsets());

        const QByteArray req = submitServer.lastRequest();
        if (!req.startsWith("POST /~cddb/submit.cgi")) {
            qWarning() << "FAIL: submit request is not a POST to submit.cgi:" << req.left(120);
            return 1;
        }
        if (!req.contains("Category: rock")
            || !req.contains("Discid: 13093f02")
            || !req.contains("User-Email: tester@example.org")
            || !req.contains("Submit-Mode: submit")
            || !req.contains("Charset: UTF-8")) {
            qWarning() << "FAIL: submit custom headers missing. Request:" << req;
            return 1;
        }
        if (!req.contains("Content-Type: text/plain")) {
            qWarning() << "FAIL: submit Content-Type header missing";
            return 1;
        }
        if (r != KCDDB::Success) {
            // 320 == Success per Submit::parseWrite; anything else is a
            // transport or parsing regression.
            qWarning() << "FAIL: submit expected Success, got"
                       << static_cast<int>(r);
            return 1;
        }
    }

    std::printf("libkcddb smoke test passed\n");
    return 0;
}

#include "test_package.moc"
