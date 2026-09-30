// kparts 6.18.0 consumer end-to-end test (R34: real API usage; rule12:
// complete consumer scenario).
//
// This drives the documented KParts embedding pattern through the whole
// ReadOnlyPart local-file lifecycle against a real file on disk:
//   construct custom part -> setArguments(OpenUrlArguments) -> openUrl()
//   -> urlChanged/started signals -> openFile() callback reading the real
//   file through localFilePath() -> completed() signal -> closeUrl()
//   state reset
// The ReadOnlyPart local-file path is synchronous in-library dispatch (no
// widgets, no KIO worker processes), so the same binary runs under
// qemu (CI / local validation) and on the DAYU200 device.
#include <KParts/OpenUrlArguments>
#include <KParts/ReadOnlyPart>

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QString>
#include <QUrl>

#include <cstdio>

static int g_failures = 0;
static int g_checks = 0;

static void check(bool ok, const char *what)
{
    ++g_checks;
    std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok) {
        ++g_failures;
    }
}

// The consumer-side part: a read-only view over a plain text file, the
// same shape as an application-embedded KParts document view.
class TextFilePart : public KParts::ReadOnlyPart
{
public:
    explicit TextFilePart(QObject *parent = nullptr)
        : KParts::ReadOnlyPart(parent)
    {
        connect(this, &KParts::ReadOnlyPart::urlChanged, this, [this](const QUrl &url) {
            ++m_urlChangedCount;
            m_lastUrlChanged = url;
        });
        connect(this, &KParts::ReadOnlyPart::started, this, [this]() {
            ++m_startedCount;
        });
        connect(this, &KParts::ReadOnlyPart::completed, this, [this]() {
            ++m_completedCount;
        });
    }

    bool openFileCalled() const { return m_openFileCalled; }
    int openFileCount() const { return m_openFileCount; }
    int lastOpenResult() const { return m_lastOpenResult; }
    const QByteArray &fileContent() const { return m_fileContent; }
    int urlChangedCount() const { return m_urlChangedCount; }
    int startedCount() const { return m_startedCount; }
    int completedCount() const { return m_completedCount; }
    const QUrl &lastUrlChanged() const { return m_lastUrlChanged; }
    // localFilePath() is protected in KParts::ReadOnlyPart, so the part
    // exposes what its own openFile() implementation resolved.
    QString resolvedLocalFilePath() const { return localFilePath(); }

protected:
    // The consumer implementation of the documented openFile() contract:
    // open localFilePath() and load its content.
    bool openFile() override
    {
        ++m_openFileCount;
        m_openFileCalled = true;
        QFile f(localFilePath());
        if (!f.open(QIODevice::ReadOnly)) {
            m_lastOpenResult = -1;
            return false;
        }
        m_fileContent = f.readAll();
        m_lastOpenResult = 0;
        return true;
    }

private:
    bool m_openFileCalled = false;
    int m_openFileCount = 0;
    int m_lastOpenResult = -1;
    QByteArray m_fileContent;
    int m_urlChangedCount = 0;
    int m_startedCount = 0;
    int m_completedCount = 0;
    QUrl m_lastUrlChanged;
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Work directory: optional argv[1] (device runs pass a scratch dir).
    const QString workDir = argc > 1 ? QString::fromLocal8Bit(argv[1])
                                     : QDir::currentPath();
    const QString filePath = workDir + QStringLiteral("/kparts_e2e_input.txt");
    const QByteArray expected("kparts-6.18.0 consumer e2e payload\nline2\n");

    // 1. Consumer writes a real input file (the data an app hands to a part).
    {
        QFile f(filePath);
        if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            std::printf("FAIL: cannot create input file %s\n", qPrintable(filePath));
            return 1;
        }
        f.write(expected);
        f.close();
    }
    QFile verifyFile(filePath);
    check(verifyFile.open(QIODevice::ReadOnly) && verifyFile.readAll() == expected,
          "1 input file created with expected content");
    verifyFile.close();

    TextFilePart part;

    // 2. Fresh part has no URL.
    check(part.url().isEmpty(), "2 new part has empty url()");

    // 3. OpenUrlArguments value round-trip (documented consumer API).
    KParts::OpenUrlArguments args;
    args.setMimeType(QStringLiteral("text/plain"));
    args.setXOffset(50);
    args.setYOffset(10);
    args.setReload(true);
    part.setArguments(args);
    const KParts::OpenUrlArguments back = part.arguments();
    check(back.mimeType() == QLatin1String("text/plain")
              && back.xOffset() == 50 && back.yOffset() == 10 && back.reload(),
          "3 OpenUrlArguments round-trip (mimeType/xOffset/yOffset/reload)");

    // 4-10. Full openUrl lifecycle on a real local file.
    const QUrl fileUrl = QUrl::fromLocalFile(filePath);
    check(part.openUrl(fileUrl), "4 openUrl(local file) returns true");
    check(part.openFileCalled(), "5 openFile() callback dispatched");
    check(part.openFileCount() == 1, "6 openFile() dispatched exactly once");
    check(part.fileContent() == expected,
          "7 openFile() read the real file content via localFilePath()");
    check(part.url() == fileUrl, "8 url() reports the opened URL");
    check(part.resolvedLocalFilePath() == filePath,
          "9 localFilePath() reports the real file path");
    check(part.urlChangedCount() == 1 && part.lastUrlChanged() == fileUrl,
          "10 urlChanged signal fired once with the opened URL");
    check(part.startedCount() == 1 && part.completedCount() == 1,
          "11 started()/completed() signals fired once each");

    // 12. Re-open with a consumer-forced mimetype; the forced value must
    // survive the lifecycle (no silent overwrite).
    part.openUrl(fileUrl);
    check(part.openFileCount() == 2 && part.arguments().mimeType() == QLatin1String("text/plain"),
          "12 second openUrl dispatches openFile() again, forced mimeType kept");

    // 13. closeUrl() resets consumer-visible state.
    check(part.closeUrl(), "13 closeUrl() returns true");
    check(part.url().isEmpty(), "14 url() empty after closeUrl()");
    check(part.arguments().mimeType().isEmpty(),
          "15 arguments cleared after closeUrl()");

    std::printf("RESULT: kparts 6.18.0 consumer end-to-end: %d/%d checks passed\n",
                g_checks - g_failures, g_checks);
    return g_failures == 0 ? 0 : 1;
}
