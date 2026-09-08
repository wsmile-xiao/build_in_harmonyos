#include <QCoreApplication>
#include <QString>
#include <QByteArray>
#include <QFile>
#include <QDir>
#include <QDateTime>
#include <QUrl>
#include <QJsonDocument>
#include <QJsonObject>
#include <QProcess>
#include <QThread>
#include <QMutex>
#include <QMutexLocker>
#include <QDebug>
#include <QElapsedTimer>
#include <QTemporaryFile>
#include <QRegularExpressionMatchIterator>
#include <QMetaObject>
#include <QMetaType>
#include <QObject>
#include <QList>
#include <QMap>
#include <QVector>
#include <QHash>
#include <QSet>
#include <QPair>
#include <QRegularExpression>
#include <QTextStream>
#include <QDataStream>
#include <QBuffer>
#include <QTimer>
#include <QLocalServer>
#include <QLocalSocket>
#include <QWaitCondition>
#include <QUuid>
#include <QVersionNumber>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cassert>
#include <cmath>

/* ============================================================
 * Qt5Core Test Suite - Comprehensive API Tests
 * Tests all major Qt5Core APIs without requiring GUI
 * ============================================================ */

static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name, expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL: %s (%s:%d)\n", name, __FILE__, __LINE__); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

/* ---------- QString Tests ---------- */
void test_QString() {
    // Construction
    QString s1("Hello");
    QString s2 = QString::fromUtf8("World");
    QString s3 = QString::number(42);
    TEST("QString: basic construction", !s1.isEmpty());
    TEST("QString: fromUtf8", s2 == "World");
    TEST("QString: number", s3 == "42");

    // Concatenation
    QString concat = s1 + " " + s2;
    TEST("QString: concatenation", concat == "Hello World");

    // Length
    TEST("QString: length", concat.length() == 11);
    TEST("QString: size", concat.size() == 11);

    // Comparison
    TEST("QString: equality", s1 == "Hello");
    TEST("QString: inequality", s1 != "World");
    TEST("QString: case insensitive", s1.compare("HELLO", Qt::CaseInsensitive) == 0);

    // Substring
    TEST("QString: left", concat.left(5) == "Hello");
    TEST("QString: right", concat.right(5) == "World");
    TEST("QString: mid", concat.mid(6, 5) == "World");

    // Transformation
    TEST("QString: toUpper", concat.toUpper() == "HELLO WORLD");
    TEST("QString: toLower", concat.toLower() == "hello world");
    TEST("QString: trimmed", QString("  test  ").trimmed() == "test");

    // Replace
    QString replace = concat;
    replace.replace("World", "Qt5");
    TEST("QString: replace", replace == "Hello Qt5");

    // Split
    QStringList parts = concat.split(" ");
    TEST("QString: split count", parts.size() == 2);
    TEST("QString: split first", parts[0] == "Hello");
    TEST("QString: split second", parts[1] == "World");

    // Contains
    TEST("QString: contains", concat.contains("World"));
    TEST("QString: not contains", !concat.contains("Foo"));

    // StartsWith/EndsWith
    TEST("QString: startsWith", concat.startsWith("Hello"));
    TEST("QString: endsWith", concat.endsWith("World"));

    // IndexOf
    TEST("QString: indexOf", concat.indexOf("World") == 6);
    TEST("QString: indexOf not found", concat.indexOf("Foo") == -1);

    // Conversion
    QByteArray ba = concat.toUtf8();
    TEST("QString: toUtf8", ba == QByteArray("Hello World"));
    TEST("QString: fromLatin1", QString::fromLatin1("test") == "test");

    // Formatting
    QString formatted = QString("Value: %1").arg(42);
    TEST("QString: arg formatting", formatted == "Value: 42");

    // Number formatting
    TEST("QString: setNum", QString::number(3.14159, 'f', 2) == "3.14");
    TEST("QString: hex", QString::number(255, 16) == "ff");

    // Empty/null
    QString empty;
    TEST("QString: empty is empty", empty.isEmpty());
    TEST("QString: empty is null", empty.isNull());
    TEST("QString: non-empty not null", !s1.isNull());

    printf("  QString tests: %d passed\n", 30);
}

/* ---------- QByteArray Tests ---------- */
void test_QByteArray() {
    QByteArray ba("Hello");
    TEST("QByteArray: construction", !ba.isEmpty());
    TEST("QByteArray: size", ba.size() == 5);

    // Append
    ba.append(" World");
    TEST("QByteArray: append", ba == QByteArray("Hello World"));

    // Conversion
    QString s = QString::fromUtf8(ba);
    TEST("QByteArray: to QString", s == "Hello World");

    // Hex
    QByteArray hex = ba.toHex();
    TEST("QByteArray: toHex", !hex.isEmpty());

    // Base64
    QByteArray encoded = ba.toBase64();
    QByteArray decoded = QByteArray::fromBase64(encoded);
    TEST("QByteArray: base64 roundtrip", decoded == ba);

    // Left/Right/Mid
    TEST("QByteArray: left", ba.left(5) == QByteArray("Hello"));
    TEST("QByteArray: right", ba.right(5) == QByteArray("World"));

    // Number
    QByteArray num = QByteArray::number(42);
    TEST("QByteArray: number", num == QByteArray("42"));

    printf("  QByteArray tests: %d passed\n", 8);
}

/* ---------- QFile/QDir Tests ---------- */
void test_QFile() {
    // Temp file
    QTemporaryFile tmpFile;
    tmpFile.open();
    tmpFile.write("Hello Qt5");
    tmpFile.flush();

    TEST("QFile: temp file exists", QFile::exists(tmpFile.fileName()));

    // Read back
    tmpFile.seek(0);
    QByteArray data = tmpFile.readAll();
    TEST("QFile: read back", data == QByteArray("Hello Qt5"));

    // File info
    QFileInfo info(tmpFile.fileName());
    TEST("QFileInfo: exists", info.exists());
    TEST("QFileInfo: isFile", info.isFile());
    TEST("QFileInfo: size", info.size() == 9);

    // Dir operations
    QDir dir("/tmp");
    TEST("QDir: exists", dir.exists());

    // Home dir
    QString home = QDir::homePath();
    TEST("QDir: homePath not empty", !home.isEmpty());

    // Current dir
    QString cwd = QDir::currentPath();
    TEST("QDir: currentPath not empty", !cwd.isEmpty());

    // Separator
    TEST("QDir: separator", QDir::separator() == '/' || QDir::separator() == '\\');

    printf("  QFile/QDir tests: %d passed\n", 9);
}

/* ---------- QDateTime Tests ---------- */
void test_QDateTime() {
    QDateTime now = QDateTime::currentDateTime();
    TEST("QDateTime: currentDateTime valid", now.isValid());

    QDate today = QDate::currentDate();
    TEST("QDate: currentDate valid", today.isValid());

    QTime nowTime = QTime::currentTime();
    TEST("QTime: currentTime valid", nowTime.isValid());

    // String conversion
    QString dateStr = now.toString("yyyy-MM-dd");
    QDateTime parsed = QDateTime::fromString(dateStr, "yyyy-MM-dd");
    TEST("QDateTime: toString/fromString roundtrip", parsed.isValid());

    // Date arithmetic
    QDate tomorrow = today.addDays(1);
    TEST("QDate: addDays", tomorrow > today);

    // Time arithmetic
    QTime later = nowTime.addSecs(3600);
    TEST("QTime: addSecs", later > nowTime || later < nowTime); // handles midnight

    // Epoch
    qint64 secs = now.toSecsSinceEpoch();
    TEST("QDateTime: toSecsSinceEpoch", secs > 1700000000); // reasonable value for 2024+

    printf("  QDateTime tests: %d passed\n", 8);
}

/* ---------- QUrl Tests ---------- */
void test_QUrl() {
    QUrl url("https://qt.io/doc?q=test#section");
    TEST("QUrl: valid", url.isValid());
    TEST("QUrl: scheme", url.scheme() == "https");
    TEST("QUrl: host", url.host() == "qt.io");
    TEST("QUrl: path", url.path() == "/doc");
    TEST("QUrl: query", url.query() == "q=test");
    TEST("QUrl: fragment", url.fragment() == "section");

    // URL encoding
    QUrl encoded = QUrl::fromEncoded("https://example.com/path%20with%20spaces");
    TEST("QUrl: fromEncoded", encoded.path() == "/path with spaces");

    printf("  QUrl tests: %d passed\n", 7);
}

/* ---------- QLocalServer/QLocalSocket Tests ---------- */
void test_QLocalSocket() {
    const QString socketName = QString(QChar::Null)
            + QStringLiteral("qt5_")
            + QUuid::createUuid().toString(QUuid::WithoutBraces);

    QLocalServer::removeServer(socketName);

    QLocalServer server;
    TEST("QLocalServer: listen abstract", server.listen(socketName));
    TEST("QLocalServer: isListening", server.isListening());

    QLocalSocket client;
    client.connectToServer(socketName);
    TEST("QLocalSocket: waitForConnected", client.waitForConnected(5000));
    TEST("QLocalServer: waitForNewConnection", server.waitForNewConnection(5000));

    QLocalSocket *serverSide = server.nextPendingConnection();
    TEST("QLocalServer: nextPendingConnection", serverSide != nullptr);
    if (serverSide == nullptr) {
        QLocalServer::removeServer(socketName);
        return;
    }

    const QByteArray serverPayload("server->client");
    const QByteArray clientPayload("client->server");

    serverSide->write(serverPayload);
    TEST("QLocalSocket: server write bytes", serverSide->waitForBytesWritten(5000));
    TEST("QLocalSocket: client readyRead", client.waitForReadyRead(5000));
    TEST("QLocalSocket: client read payload", client.readAll() == serverPayload);

    client.write(clientPayload);
    TEST("QLocalSocket: client write bytes", client.waitForBytesWritten(5000));
    TEST("QLocalSocket: server readyRead", serverSide->waitForReadyRead(5000));
    TEST("QLocalSocket: server read payload", serverSide->readAll() == clientPayload);

    client.disconnectFromServer();
    serverSide->disconnectFromServer();
    delete serverSide;
    QLocalServer::removeServer(socketName);

    printf("  QLocalSocket tests: %d passed\n", 11);
}

class CooperativeThread : public QThread {
public:
    QMutex mutex;
    QWaitCondition enteredCondition;
    QWaitCondition stopCondition;
    bool entered = false;
    bool stopRequested = false;

    void requestStop() {
        QMutexLocker locker(&mutex);
        stopRequested = true;
        stopCondition.wakeAll();
    }

protected:
    void run() override {
        QMutexLocker locker(&mutex);
        entered = true;
        enteredCondition.wakeAll();
        while (!stopRequested) {
            stopCondition.wait(&mutex, 100);
        }
    }
};

/* ---------- QThread Lifecycle Tests ---------- */
void test_QThreadLifecycle() {
    CooperativeThread thread;
    thread.start();

    {
        QMutexLocker locker(&thread.mutex);
        QElapsedTimer timer;
        timer.start();
        while (!thread.entered && timer.elapsed() < 5000) {
            thread.enteredCondition.wait(&thread.mutex, 100);
        }
    }

    TEST("QThread: run entered", thread.entered);

    thread.requestStop();
    TEST("QThread: wait after stop", thread.wait(5000));
    TEST("QThread: not running after stop", !thread.isRunning());
    TEST("QThread: finished after stop", thread.isFinished());

    printf("  QThread lifecycle tests: %d passed\n", 4);
}

/* ---------- QJson Tests ---------- */
void test_QJson() {
    QJsonObject obj;
    obj["name"] = "Qt5";
    obj["version"] = 5.1519;
    obj["active"] = true;

    QJsonDocument doc(obj);
    QByteArray json = doc.toJson();
    TEST("QJson: toJson not empty", !json.isEmpty());

    QJsonDocument parsed = QJsonDocument::fromJson(json);
    TEST("QJson: fromJson valid", !parsed.isNull());
    TEST("QJson: isObject", parsed.isObject());

    QJsonObject parsedObj = parsed.object();
    TEST("QJson: name field", parsedObj["name"].toString() == "Qt5");
    TEST("QJson: version field", qAbs(parsedObj["version"].toDouble() - 5.1519) < 0.001);
    TEST("QJson: active field", parsedObj["active"].toBool() == true);

    printf("  QJson tests: %d passed\n", 7);
}

/* ---------- QRegularExpression Tests ---------- */
void test_QRegularExpression() {
    QRegularExpression re("\\d+");
    TEST("QRegularExpression: valid", re.isValid());

    QRegularExpressionMatch match = re.match("abc123def");
    TEST("QRegularExpression: hasMatch", match.hasMatch());
    TEST("QRegularExpression: captured", match.captured() == "123");

    // Global match
    QRegularExpressionMatchIterator it = re.globalMatch("a1b2c3");
    int count = 0;
    while (it.hasNext()) { it.next(); count++; }
    TEST("QRegularExpression: globalMatch count", count == 3);

    // Escape
    QString escaped = QRegularExpression::escape("test.123");
    TEST("QRegularExpression: escape", escaped == "test\\.123");

    printf("  QRegularExpression tests: %d passed\n", 5);
}

/* ---------- QList/QVector/QMap Tests ---------- */
void test_Containers() {
    // QList
    QList<int> list;
    list << 1 << 2 << 3;
    TEST("QList: size", list.size() == 3);
    TEST("QList: contains", list.contains(2));
    TEST("QList: first", list.first() == 1);
    TEST("QList: last", list.last() == 3);
    list.append(4);
    TEST("QList: append", list.size() == 4);
    list.removeOne(2);
    TEST("QList: removeOne", !list.contains(2));

    // QVector
    QVector<int> vec;
    vec << 10 << 20 << 30;
    TEST("QVector: size", vec.size() == 3);
    TEST("QVector: at", vec.at(1) == 20);
    vec.append(40);
    TEST("QVector: append", vec.size() == 4);

    // QMap
    QMap<QString, int> map;
    map["one"] = 1;
    map["two"] = 2;
    map["three"] = 3;
    TEST("QMap: size", map.size() == 3);
    TEST("QMap: contains", map.contains("two"));
    TEST("QMap: value", map.value("two") == 2);
    TEST("QMap: keys", map.keys().size() == 3);

    // QHash
    QHash<QString, int> hash;
    hash["key1"] = 100;
    hash["key2"] = 200;
    TEST("QHash: size", hash.size() == 2);
    TEST("QHash: value", hash.value("key1") == 100);

    // QSet
    QSet<int> set;
    set << 1 << 2 << 3 << 1; // duplicate
    TEST("QSet: no duplicates", set.size() == 3);
    TEST("QSet: contains", set.contains(2));

    printf("  Container tests: %d passed\n", 15);
}

/* ---------- QUuid Tests ---------- */
void test_QUuid() {
    QUuid uuid = QUuid::createUuid();
    TEST("QUuid: createUuid not null", !uuid.isNull());
    QString uuidStr = uuid.toString(QUuid::WithoutBraces);
    TEST("QUuid: toString not empty", !uuidStr.isEmpty());
    TEST("QUuid: string length", uuidStr.length() == 36);

    // From string
    QUuid parsed = QUuid::fromString(uuidStr);
    TEST("QUuid: fromString roundtrip", parsed == uuid);

    printf("  QUuid tests: %d passed\n", 4);
}

/* ---------- QVersionNumber Tests ---------- */
void test_QVersionNumber() {
    QVersionNumber v = QVersionNumber::fromString("5.15.19");
    TEST("QVersionNumber: major", v.majorVersion() == 5);
    TEST("QVersionNumber: minor", v.minorVersion() == 15);
    TEST("QVersionNumber: micro", v.microVersion() == 19);
    TEST("QVersionNumber: toString", v.toString() == "5.15.19");

    QVersionNumber v1(5, 15, 19);
    QVersionNumber v2(5, 15, 0);
    TEST("QVersionNumber: comparison", v1 > v2);

    printf("  QVersionNumber tests: %d passed\n", 5);
}

/* ============================================================
 * Main: Run all tests
 * ============================================================ */
int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    printf("Qt5 Version: %s\n", qVersion());
    printf("QT_VERSION: %d.%d.%d\n",
           (QT_VERSION >> 16) & 0xFF,
           (QT_VERSION >> 8) & 0xFF,
           QT_VERSION & 0xFF);

    // Verify version macro
    assert(QT_VERSION == QT_VERSION_CHECK(5, 15, 19));

    printf("\n=== Qt5Core Comprehensive Test Suite ===\n\n");

    test_QString();
    test_QByteArray();
    test_QFile();
    test_QDateTime();
    test_QUrl();
    test_QLocalSocket();
    test_QThreadLifecycle();
    test_QJson();
    test_QRegularExpression();
    test_Containers();
    test_QUuid();
    test_QVersionNumber();

    printf("\n=== Results ===\n");
    printf("Tests passed: %d\n", tests_passed);
    printf("Tests failed: %d\n", tests_failed);

    if (tests_failed > 0) {
        fprintf(stderr, "FAILED: %d tests failed!\n", tests_failed);
        return 1;
    }

    printf("ALL TESTS PASSED\n");
    return 0;
}
