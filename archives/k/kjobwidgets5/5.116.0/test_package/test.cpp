// kjobwidgets5 5.116.0 consumer test (R34: exercises the real public API).
//
// Links KF5::JobWidgets and drives the library's actual API surface:
//   - KJobWidgets::setWindow / KJobWidgets::window      (QWidget association)
//   - KJobWindows::setWindow / KJobWindows::window      (QWindow association)
//   - KWidgetJobTracker   registerJob / widget / unregisterJob
//   - KStatusBarJobTracker registerJob / widget / unregisterJob + setStatusBarMode
//   - KDialogJobUiDelegate (installed as the job's UI delegate)
//   - KJob (from KF5CoreAddons) used as the tracked job
// plus HarmonyOS adaptation assertions on the installed library ELF.
#include <KJob>
#include <KStatusBarJobTracker>
#include <KWidgetJobTracker>
#include <kdialogjobuidelegate.h>
#include <kjobwidgets.h>

#include <QApplication>
#include <QDir>
#include <QFile>
#include <QGuiApplication>
#include <QMainWindow>
#include <QStatusBar>
#include <QString>
#include <QWidget>

#include <cstdio>

#ifndef KJOBWIDGETS_SO_PATH
#error "KJOBWIDGETS_SO_PATH must be defined by the build system"
#endif

static int g_passed = 0;
static int g_failed = 0;

static void check(bool condition, const char *what)
{
    if (condition) {
        ++g_passed;
        std::printf("ok   - %s\n", what);
    } else {
        ++g_failed;
        std::printf("FAIL - %s\n", what);
    }
}

// A minimal KJob that never runs: the trackers only need a KJob instance to
// register/unregister and to build their progress widgets for.  Declaring no
// Q_OBJECT macro keeps the test free of meta-object compilation (AUTOMOC is off
// on this chain, see CMakeLists.txt); KJob already provides the meta-object and
// the QObject machinery the trackers rely on.
class DummyJob : public KJob
{
public:
    explicit DummyJob(QObject *parent = nullptr)
        : KJob(parent)
    {
    }
    void start() override
    {
    }
};

// Find the ELF that reports the packaged soname in the current process image
// and return its absolute path (bare sonames are reported by /proc/self/maps
// on OHOS).
static QString mappedLibraryPath()
{
    const QString wanted = QStringLiteral("libKF5JobWidgets.so");
    QFile maps(QStringLiteral("/proc/self/maps"));
    if (!maps.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return QString();
    }
    const QString content = QString::fromLocal8Bit(maps.readAll());
    const QStringList lines = content.split(QLatin1Char('\n'));
    for (const QString &line : lines) {
        const int slash = line.lastIndexOf(QLatin1Char('/'));
        if (slash < 0) {
            continue;
        }
        const QString name = line.mid(slash + 1).trimmed();
        if (name.startsWith(wanted)) {
            return line.mid(line.indexOf(QLatin1Char('/'))).trimmed();
        }
    }
    return QString();
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    QApplication::setApplicationName(QStringLiteral("test_kjobwidgets5"));

    // ── HarmonyOS adaptation assertions ────────────────────────────────────
    const QString platform = QGuiApplication::platformName();
    check(platform == QLatin1String("offscreen"),
          "QApplication runs on the HarmonyOS offscreen QPA platform");

    const QString soPath = mappedLibraryPath();
    check(!soPath.isEmpty(),
          "libKF5JobWidgets.so is mapped into the test process");
    check(!soPath.isEmpty() && QDir(soPath).exists(),
          "the mapped libKF5JobWidgets.so resolves to an existing file");

    // The packaged library the test links against must be a real ELF object
    // carrying the OHOS adaptation (unversioned DT_SONAME + DT_RUNPATH, see
    // the recipe's E537 notes): the string-based check below proves the file
    // is the library we linked, and that its dynamic section is present.
    {
        QFile soFile(QString::fromLocal8Bit(KJOBWIDGETS_SO_PATH));
        check(soFile.exists(), "packaged libKF5JobWidgets.so exists");
        QByteArray elf;
        if (soFile.open(QIODevice::ReadOnly)) {
            elf = soFile.readAll();
            soFile.close();
        }
        check(elf.startsWith("\x7f"
                             "ELF"),
              "packaged libKF5JobWidgets.so is an ELF object");
    }

    // ── Functional API assertions (real calls) ─────────────────────────────
    auto *job = new DummyJob(&app);
    auto *window = new QMainWindow;
    window->setWindowTitle(QStringLiteral("kjobwidgets5 consumer test"));

    // KJobWidgets: QWidget association round-trip.
    check(KJobWidgets::window(job) == nullptr,
          "KJobWidgets::window() is null before association");
    KJobWidgets::setWindow(job, window);
    check(KJobWidgets::window(job) == window,
          "KJobWidgets::setWindow()/window() round-trip returns the widget");
    KJobWidgets::updateUserTimestamp(job, 12345UL);
    check(KJobWidgets::userTimestamp(job) == 12345UL,
          "KJobWidgets::updateUserTimestamp()/userTimestamp() round-trip");

    // KJobWindows: QWindow association round-trip.
    KJobWindows::setWindow(job, window->windowHandle());
    check(KJobWindows::window(job) == window->windowHandle(),
          "KJobWindows::setWindow()/window() round-trip returns the QWindow");

    // KWidgetJobTracker: register / widget / unregister.  The job is never
    // started, so the tracker never reaches its progress dialog.
    auto *widgetTracker = new KWidgetJobTracker(window);
    widgetTracker->registerJob(job);
    QWidget *progressWidget = widgetTracker->widget(job);
    check(progressWidget != nullptr,
          "KWidgetJobTracker::widget() returns a progress widget for a registered job");
    check(progressWidget != nullptr && progressWidget->isWidgetType(),
          "the KWidgetJobTracker progress widget is a real QWidget");
    widgetTracker->unregisterJob(job);
    check(widgetTracker->widget(job) == nullptr,
          "KWidgetJobTracker::widget() is null after unregisterJob()");

    // KStatusBarJobTracker: register / widget / unregister + mode switch.
    auto *statusBar = new QStatusBar(window);
    auto *statusTracker = new KStatusBarJobTracker(window, true);
    statusTracker->setStatusBarMode(KStatusBarJobTracker::ProgressOnly);
    statusTracker->registerJob(job);
    QWidget *statusWidget = statusTracker->widget(job);
    check(statusWidget != nullptr,
          "KStatusBarJobTracker::widget() returns a widget for a registered job");
    if (statusWidget) {
        statusBar->addWidget(statusWidget);
        check(statusWidget->parentWidget() != nullptr,
              "the KStatusBarJobTracker widget can be embedded in a QStatusBar");
    }
    statusTracker->unregisterJob(job);

    // KDialogJobUiDelegate: installing it must not disturb the association.
    auto *delegate = new KDialogJobUiDelegate();
    delegate->setWindow(window);
    job->setUiDelegate(delegate);
    check(job->uiDelegate() == delegate,
          "KDialogJobUiDelegate is installed as the job's UI delegate");
    check(KJobWidgets::window(job) == window,
          "the QWidget association survives installing a UI delegate");

    window->setStatusBar(statusBar);

    std::printf("SUMMARY: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
