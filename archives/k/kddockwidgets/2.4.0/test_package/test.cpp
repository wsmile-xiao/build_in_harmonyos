// Consumer test for kddockwidgets 2.4.0 (R34: real API usage, no stub test).
//
// Runs a real QtWidgets docking scenario against the installed library with
// the offscreen QPA platform (qt5-qtbase/5.15.2.2 ships the offscreen plugin;
// xcb is unavailable on OHOS). The scenario is a single ordered flow of
// twelve test cases executed by the small runner below (runCase): each case
// reports TEST PASS / TEST FAIL, a SUMMARY line is printed at the end, and
// the process exits non-zero if any case failed. Every case exercises the
// public controller/view API, the dock registry and the layout
// save/close/restore round-trip, and is deterministic on headless devices.
// Each asserted behavior was verified against the upstream 2.4.0 sources:
//   - DockWidget ctor registers with DockRegistry (core/DockWidget.cpp:60)
//   - title() defaults to the uniqueName (Private ctor: title(dockName))
//   - isFloating() is true only for root views / single-dock floating windows
//   - LayoutSaver restores into existing widgets matched by uniqueName
#include <kddockwidgets/Config.h>
#include <kddockwidgets/DockWidget.h>
#include <kddockwidgets/KDDockWidgets.h>
#include <kddockwidgets/LayoutSaver.h>
#include <kddockwidgets/MainWindow.h>
#include <kddockwidgets/core/DockRegistry.h>

#include <QApplication>
#include <QDir>
#include <QFile>
#include <QTimer>

#include <cstdio>
#include <functional>

using namespace KDDockWidgets;

// ---- shared scenario state (fixture) -------------------------------------
static QtWidgets::MainWindow *g_main = nullptr;
static QtWidgets::DockWidget *g_dock1 = nullptr;
static QtWidgets::DockWidget *g_dock2 = nullptr;
static QString g_layoutFile;

// ---- ordered test cases (one per asserted behavior) ----------------------

// 1. MainWindow::uniqueName() round-trips the construction name.
static bool case01_uniqueNameRoundtrip()
{
    return g_main->uniqueName() == QStringLiteral("test-main-window");
}

// 2. DockRegistry counts both dock widgets (ctor registration,
//    DockRegistry::registerDockWidget runs in the DockWidget ctor).
static bool case02_registryCountsBoth()
{
    return DockRegistry::self()->dockwidgets().size() == 2;
}

// 3. DockWidget::title() defaults to the construction uniqueName.
static bool case03_titleDefaultsToUniqueName()
{
    return g_dock1->title() == QStringLiteral("dock-1");
}

// 4. setTitle() updates title().
static bool case04_setTitleRoundtrip()
{
    g_dock1->setTitle(QStringLiteral("dock-1-renamed"));
    return g_dock1->title() == QStringLiteral("dock-1-renamed");
}

// 5. The second dock widget's title is intact.
static bool case05_secondTitleIntact()
{
    return g_dock2->title() == QStringLiteral("dock-2");
}

// 6. dock1 is docked into the main window (not floating).
static bool case06_dock1DockedNotFloating()
{
    return !g_dock1->isFloating();
}

// 7. dock2 is docked into the main window (not floating).
static bool case07_dock2DockedNotFloating()
{
    return !g_dock2->isFloating();
}

// 8. LayoutSaver::saveToFile() succeeds.
static bool case08_saveLayoutToFile()
{
    static LayoutSaver saver;
    return saver.saveToFile(g_layoutFile);
}

// 9. Closing a docked dock widget hides it (KDDockWidgets closeEvent removes
//    it from the layout); it stays alive and registered.
static bool case09_closeHidesDockWidget()
{
    g_dock1->close();
    QCoreApplication::processEvents();
    return !g_dock1->isVisible();
}

// 10. LayoutSaver::restoreFromFile() succeeds.
static bool case10_restoreLayoutFromFile()
{
    static LayoutSaver saver;
    return saver.restoreFromFile(g_layoutFile);
}

// 11. Restoring re-docks the closed dock widget (visible again, matched by
//     uniqueName).
static bool case11_restoreRedocksClosedDockWidget()
{
    QCoreApplication::processEvents();
    return g_dock1->isVisible();
}

// 12. The restored dock widget is docked, not floating.
static bool case12_restoredNotFloating()
{
    return !g_dock1->isFloating();
}

// ---- runner --------------------------------------------------------------

static int g_failures = 0;
static int g_run = 0;

static void runCase(const char *name, const std::function<bool()> &fn)
{
    ++g_run;
    const bool ok = fn();
    if (ok) {
        std::printf("TEST PASS: %s\n", name);
    } else {
        ++g_failures;
        std::printf("TEST FAIL: %s\n", name);
    }
}

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QApplication app(argc, argv);
    initFrontend(FrontendType::QtWidgets);

    // Scenario fixture: a main window with two dock widgets docked into it.
    g_main = new QtWidgets::MainWindow(QStringLiteral("test-main-window"),
                                       MainWindowOption_None);
    g_dock1 = new QtWidgets::DockWidget(QStringLiteral("dock-1"));
    g_dock2 = new QtWidgets::DockWidget(QStringLiteral("dock-2"));

    g_main->addDockWidget(g_dock1, Location_OnTop);
    g_main->addDockWidget(g_dock2, Location_OnRight);
    g_main->resize(800, 600);
    g_main->show();
    QCoreApplication::processEvents();

    g_layoutFile = QDir::tempPath()
        + QStringLiteral("/kddockwidgets-consumer-layout.json");

    runCase("uniqueName-roundtrip", case01_uniqueNameRoundtrip);
    runCase("registry-counts-both-docks", case02_registryCountsBoth);
    runCase("title-defaults-to-uniquename", case03_titleDefaultsToUniqueName);
    runCase("setTitle-roundtrip", case04_setTitleRoundtrip);
    runCase("second-title-intact", case05_secondTitleIntact);
    runCase("dock1-docked-not-floating", case06_dock1DockedNotFloating);
    runCase("dock2-docked-not-floating", case07_dock2DockedNotFloating);
    runCase("save-layout-to-file", case08_saveLayoutToFile);
    runCase("close-hides-dockwidget", case09_closeHidesDockWidget);
    runCase("restore-layout-from-file", case10_restoreLayoutFromFile);
    runCase("restore-redocks-closed-dockwidget",
            case11_restoreRedocksClosedDockWidget);
    runCase("restored-not-floating", case12_restoredNotFloating);

    QFile::remove(g_layoutFile);

    // Drain the event loop so pending timers/events are processed.
    QTimer::singleShot(200, &app, &QCoreApplication::quit);
    app.exec();

    std::printf("SUMMARY: %d/%d passed, %d failed\n", g_run - g_failures,
                g_run, g_failures);
    std::fflush(stdout);
    return g_failures ? 1 : 0;
}
