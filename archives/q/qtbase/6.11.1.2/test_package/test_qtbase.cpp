#include <QApplication>
#include <QColor>
#include <QDBusMessage>
#include <QDBusConnection>
#include <QDomDocument>
#include <QElapsedTimer>
#include <QFontDatabase>
#include <QFontMetrics>
#include <QGuiApplication>
#include <QHostAddress>
#include <QImage>
#include <QPainter>
#include <QProcess>
#include <QSharedMemory>
#include <QScopeGuard>
#include <QSizePolicy>
#include <QSslSocket>
#include <QThread>
#include <QTemporaryFile>
#include <QTemporaryDir>
#include <QSaveFile>
#include <QFile>
#include <QWidget>
#include <QWindow>
#include <QtGlobal>
#include <QUuid>
#include <QtWaylandClient/private/qwaylandintegration_p.h>

#include <cstdio>
#include <cstring>
#include <QDateTime>
#include <QTimeZone>
#include <QStandardPaths>
#ifdef Q_OS_UNIX
#include <pthread.h>
#include <signal.h>
#include <sys/mman.h>
#include <unistd.h>
#endif

static int assertions = 0;

static bool check(bool condition, const char *name, const char *expected)
{
    ++assertions;
    std::fprintf(condition ? stdout : stderr, "[%s] %s; expected=%s; actual=%s\n",
                 condition ? "PASS" : "FAIL", name, expected,
                 condition ? "matched" : "not matched");
    return condition;
}

#ifdef Q_OS_UNIX
static volatile sig_atomic_t interrupted = 0;
static bool interruptedStdioEof()
{
    int pipefd[2];
    if (::pipe(pipefd) != 0)
        return false;
    FILE *stream = ::fdopen(pipefd[0], "rb");
    if (!stream) {
        ::close(pipefd[0]);
        ::close(pipefd[1]);
        return false;
    }
    struct sigaction action = {}, previous = {};
    action.sa_handler = [](int) { interrupted = 1; };
    sigemptyset(&action.sa_mask);
    if (::sigaction(SIGUSR1, &action, &previous) != 0) {
        ::fclose(stream);
        ::close(pipefd[1]);
        return false;
    }
    const pthread_t reader = pthread_self();
    QThread *writer = QThread::create([reader, fd = pipefd[1]] {
        QThread::msleep(200);
        pthread_kill(reader, SIGUSR1);
        QThread::msleep(200);
        ::close(fd);
    });
    writer->start();
    QFile input;
    char byte;
    const bool opened = input.open(stream, QIODevice::ReadOnly);
    const qint64 count = opened ? input.read(&byte, 1) : -1;
    input.close();
    writer->wait();
    delete writer;
    ::sigaction(SIGUSR1, &previous, nullptr);
    ::fclose(stream);
    return opened && count == 0 && interrupted == 1;
}
#endif

static int ipcWorker(const QString &key)
{
    QSharedMemory memory(QNativeIpcKey(key, QNativeIpcKey::Type::PosixRealtime));
    if (!memory.attach()) {
        std::fprintf(stderr, "[FAIL] IPC child attach: %s\n", qPrintable(memory.errorString()));
        return 1;
    }
    for (int i = 0; i < 200; ++i) {
        if (!memory.lock())
            return 2;
        auto *counter = static_cast<int *>(memory.data());
        const int value = *counter;
        QThread::usleep(100);
        *counter = value + 1;
        if (!memory.unlock())
            return 3;
    }
    return 0;
}

static bool longNameIpc()
{
    // 221 bytes is a valid native POSIX name on the target. All characters
    // after '/' are letters, exposing length growth in legacy key conversion.
    QString key = QStringLiteral("/") + QString(220, QLatin1Char('a'));
    const QByteArray unique = QUuid::createUuid().toRfc4122();
    for (int i = 0; i < unique.size(); ++i)
        key[205 + i] = QChar('a' + (static_cast<unsigned char>(unique[i]) & 15));
    const QNativeIpcKey nativeKey(key, QNativeIpcKey::Type::PosixRealtime);
    QSharedMemory memory(nativeKey);
    if (!memory.create(sizeof(int))) {
        std::fprintf(stderr, "[FAIL] IPC parent create: %s\n", qPrintable(memory.errorString()));
        return false;
    }
#ifdef Q_OS_UNIX
    // QSharedMemory intentionally leaves POSIX object removal to its caller.
    const auto cleanup = qScopeGuard([&memory] {
        ::shm_unlink(QFile::encodeName(memory.nativeKey()).constData());
    });
#endif
    if (memory.nativeIpcKey() != nativeKey || !memory.lock()) {
        std::fprintf(stderr, "[FAIL] IPC parent native key/lock: %s\n", qPrintable(memory.errorString()));
        return false;
    }
    *static_cast<int *>(memory.data()) = 0;
    if (!memory.unlock())
        return false;
    QProcess first, second;
    const QStringList arguments{QStringLiteral("--ipc-child"), key};
    first.start(QCoreApplication::applicationFilePath(), arguments);
    second.start(QCoreApplication::applicationFilePath(), arguments);
    const bool firstDone = first.waitForFinished(15000);
    const bool secondDone = second.waitForFinished(15000);
    if (!firstDone || !secondDone || first.exitStatus() != QProcess::NormalExit
            || second.exitStatus() != QProcess::NormalExit
            || first.exitCode() != 0 || second.exitCode() != 0) {
        std::fprintf(stderr, "[FAIL] IPC children: finished=%d/%d exits=%d/%d\n%s%s",
                     firstDone, secondDone, first.exitCode(), second.exitCode(),
                     first.readAllStandardError().constData(), second.readAllStandardError().constData());
        first.kill(); second.kill();
        first.waitForFinished(3000); second.waitForFinished(3000);
        return false;
    }
    if (!memory.lock())
        return false;
    const int value = *static_cast<const int *>(memory.constData());
    const bool unlocked = memory.unlock();
    std::printf("[STEP] IPC native name=%lld bytes; two children count=%d expected=400\n",
                static_cast<long long>(key.size()), value);
    return unlocked && value == 400;
}

int main(int argc, char **argv)
{
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    if (argc == 3 && std::strcmp(argv[1], "--ipc-child") == 0) {
        QCoreApplication application(argc, argv);
        return ipcWorker(QString::fromLocal8Bit(argv[2]));
    }
    if (argc != 2) {
        std::fprintf(
            stderr,
            "[FAIL] usage: test_qtbase --offscreen|--wayland|--fonts|--system|"
            "--negative-control\n"
        );
        return 64;
    }
    if (std::strcmp(argv[1], "--negative-control") == 0) {
        std::fprintf(stderr, "[FAIL] intentional negative control\n");
        return 97;
    }

    const bool wayland_mode = std::strcmp(argv[1], "--wayland") == 0;
    const bool fonts_mode = std::strcmp(argv[1], "--fonts") == 0;
    const bool system_mode = std::strcmp(argv[1], "--system") == 0;
    if (!wayland_mode && !fonts_mode && !system_mode && std::strcmp(argv[1], "--offscreen") != 0) {
        std::fprintf(stderr, "[FAIL] unknown mode: %s\n", argv[1]);
        return 65;
    }

    qputenv("QT_QPA_PLATFORM", wayland_mode ? "wayland" : "offscreen");
    std::printf(
        "[STEP] create QApplication with %s QPA\n",
        wayland_mode ? "wayland" : "offscreen"
    );
    QApplication application(argc, argv);
    if (system_mode) {
        QTemporaryDir directory;
        QTemporaryFile temporary(directory.filePath("roundtrip-XXXXXX"));
        if (!check(directory.isValid() && temporary.open(), "Temporary file creation", "success"))
            return 27;
        if (!check(temporary.write("qt-temp") == 7, "Temporary file write", "7 bytes"))
            return 28;
        temporary.close();
        QFile reopened(temporary.fileName());
        if (!check(!temporary.fileName().isEmpty() && reopened.open(QIODevice::ReadOnly)
                   && reopened.readAll() == "qt-temp", "Temporary file materialization", "reopen and exact content"))
            return 29;
        QSaveFile saved(directory.filePath("saved"));
        if (!check(saved.open(QIODevice::WriteOnly) && saved.write("qt-save") == 7 && saved.commit(),
                   "QSaveFile commit", "atomic save succeeds"))
            return 30;
        QFile persisted(directory.filePath("saved"));
        if (!check(persisted.open(QIODevice::ReadOnly) && persisted.readAll() == "qt-save",
                   "QSaveFile contents", "exact content"))
            return 31;
        const QByteArray machine = QDBusConnection::localMachineId();
        if (!check(machine == QDBusConnection::localMachineId(), "D-Bus machine ID query",
                   "stable result without process termination"))
            return 32;
        const QTimeZone shanghai("Asia/Shanghai");
        const QTimeZone oslo("Europe/Oslo");
        if (!check(shanghai.isValid() && oslo.isValid(), "Named time zones", "Shanghai and Oslo available"))
            return 33;
        const QDateTime utc(QDate(2025, 1, 15), QTime(12, 0), QTimeZone::UTC);
        if (!check(shanghai.offsetFromUtc(utc) == 8 * 3600 && oslo.offsetFromUtc(utc) == 3600,
                   "Timezone offsets", "Shanghai UTC+8 and Oslo UTC+1 in January"))
            return 34;
        if (!check(!QStandardPaths::writableLocation(QStandardPaths::RuntimeLocation).isEmpty(),
                   "Runtime directory", "usable path with a numeric UID fallback"))
            return 35;
#ifdef Q_OS_UNIX
        if (!check(interruptedStdioEof(), "Interrupted stdio EOF", "signal handled and read reaches EOF"))
            return 36;
#endif
        if (!check(longNameIpc(), "Long-name POSIX shared memory",
                   "unchanged 221-byte native key; two locked child writers produce 400"))
            return 37;
        std::printf("[SUMMARY] system_assertions=%d passed=%d machine_id_available=%d\n",
                    assertions, assertions, !machine.isEmpty());
        return 0;
    }
    if (fonts_mode) {
        const QStringList families = QFontDatabase::families();
        if (!check(!families.isEmpty(), "Font database", "at least one registered family"))
            return 25;
        const QFontMetrics metrics(QFont(families.first()));
        if (!check(metrics.horizontalAdvance(QStringLiteral("QtBase")) > 0,
                   "Font metrics", "positive text advance"))
            return 26;
        std::printf("[SUMMARY] font_assertions=%d passed=%d\n", assertions, assertions);
        return 0;
    }
    const QString expected_platform = wayland_mode ? "wayland" : "offscreen";
    if (!application.platformName().startsWith(expected_platform)) {
        std::fprintf(
            stderr,
            "[FAIL] expected QPA %s, got %s\n",
            qPrintable(expected_platform),
            qPrintable(application.platformName())
        );
        return 1;
    }
    std::printf(
        "[PASS] QPA platform is %s\n",
        qPrintable(application.platformName())
    );

    ++assertions;
    QWidget widget;
    widget.setWindowTitle("QtBase Wayland validation");
    widget.resize(240, 120);
    widget.show();
    application.processEvents();
    if (!check(widget.isVisible(), "QWidget visibility", "visible")) {
        return 2;
    }

    QtWaylandClient::QWaylandIntegration *integration =
        QtWaylandClient::QWaylandIntegration::instance();
    if (wayland_mode && integration == nullptr) {
        std::fprintf(stderr, "[FAIL] Wayland integration instance is null\n");
        return 3;
    }
    if (!wayland_mode && integration != nullptr) {
        std::fprintf(stderr, "[FAIL] Wayland integration leaked into offscreen mode\n");
        return 4;
    }
    if (wayland_mode
        && (widget.windowHandle() == nullptr
            || widget.windowHandle()->handle() == nullptr)) {
        std::fprintf(stderr, "[FAIL] Wayland platform window was not created\n");
        return 5;
    }
    std::printf("[PASS] Qt6WaylandClientPrivate symbol and QPA state match\n");
    ++assertions;
    if (wayland_mode) {
        ++assertions;
        QElapsedTimer deadline;
        deadline.start();
        while (!widget.windowHandle()->isExposed() && deadline.elapsed() < 5000) {
            application.processEvents();
            QThread::msleep(10);
        }
        if (!check(widget.windowHandle()->isExposed(), "Wayland compositor exposure",
                   "exposed within 5 seconds"))
            return 17;
    }

    const QColor color("#336699");
    if (!check(color.isValid(), "QColor parse", "valid color"))
        return 6;
    if (!check(color.red() == 0x33 && color.green() == 0x66 && color.blue() == 0x99,
               "QColor channels", "51,102,153"))
        return 7;

    const QHostAddress loopback(QHostAddress::LocalHost);
    if (!check(loopback.isLoopback(), "QHostAddress", "loopback"))
        return 8;
    QHostAddress invalidAddress;
    if (!check(!invalidAddress.setAddress("not-an-ip-address"),
               "QHostAddress invalid input", "parse rejected"))
        return 18;

    const QSizePolicy policy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    if (!check(policy.horizontalPolicy() == QSizePolicy::Preferred,
               "horizontal QSizePolicy", "Preferred"))
        return 9;
    if (!check(policy.verticalPolicy() == QSizePolicy::Expanding,
               "vertical QSizePolicy", "Expanding"))
        return 10;

    QImage image(8, 8, QImage::Format_ARGB32_Premultiplied);
    if (!check(!image.isNull(), "QImage allocation", "8x8 raster"))
        return 11;
    image.fill(Qt::transparent);
    QPainter painter(&image);
    painter.fillRect(image.rect(), color);
    painter.end();
    if (!check(image.pixelColor(4, 4) == color, "QPainter output", "center pixel #336699"))
        return 12;

    QDomDocument document("qtbase-test");
    QDomElement root = document.createElement("root");
    QDomElement value = document.createElement("value");
    value.appendChild(document.createTextNode("42"));
    root.appendChild(value);
    document.appendChild(root);
    if (!check(document.documentElement().tagName() == "root", "DOM root", "root"))
        return 13;
    if (!check(document.documentElement().firstChildElement("value").text() == "42",
               "DOM text", "42"))
        return 14;
    QDomDocument invalidDocument;
    if (!check(!invalidDocument.setContent(QStringLiteral("<root>")),
               "invalid XML", "parse rejected"))
        return 19;

    const QDBusMessage message = QDBusMessage::createMethodCall(
        "org.example.QtbaseTest",
        "/org/example/QtbaseTest",
        "org.example.QtbaseTest",
        "Ping"
    );
    if (!check(message.type() == QDBusMessage::MethodCallMessage,
               "DBus message", "MethodCallMessage"))
        return 15;

    if (!QSslSocket::supportsSsl()) {
        std::fprintf(
            stderr,
            "[FAIL] QtNetwork did not load an OpenSSL backend: %s\n",
            qPrintable(QSslSocket::sslLibraryBuildVersionString())
        );
        return 16;
    }
    ++assertions;
    if (!check(QSslSocket::activeBackend() == "openssl", "TLS backend", "openssl"))
        return 20;
    if (!check(QSslSocket::sslLibraryVersionNumber() > 0, "TLS runtime version", "nonzero"))
        return 21;

    std::printf(
        "[PASS] Qt %s %s QPA, DBus, TLS, raster painting, and XML work\n",
        QT_VERSION_STR,
        wayland_mode ? "wayland" : "offscreen"
    );
    std::printf("[SUMMARY] runtime_assertions=%d passed=%d\n", assertions, assertions);
    return 0;
}
