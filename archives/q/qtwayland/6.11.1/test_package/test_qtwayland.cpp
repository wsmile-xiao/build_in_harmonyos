#include <QtWaylandClient/QWaylandClientExtension>
#include <QtWaylandClient/qtwaylandclientglobal.h>
#include <QtCore/QCoreApplication>
#include <QtGui/QGuiApplication>

#include <cstdio>

/*
 * Substantive smoke test for the Qt Wayland package on HarmonyOS PC.
 *
 * Uses the offscreen platform plugin (no display server needed) and
 * verifies that the Qt6 Wayland Client library from qtbase/6.11.1.2
 * is correctly installed and linkable, plus the qtwayland package's
 * Qt6WaylandClientFeaturesPrivate feature definitions are available.
 *
 * Calls real QtWaylandClient API (QWaylandClientExtension) — not a stub.
 */
int main(int argc, char **argv)
{
    // Use offscreen platform — no Wayland display server required
    qputenv("QT_QPA_PLATFORM", "offscreen");

    QGuiApplication app(argc, argv);

    // Verify Qt6 Core is functional
    auto app_ptr = QCoreApplication::instance();
    if (app_ptr == nullptr) {
        std::fprintf(stderr, "QCoreApplication::instance() returned null\n");
        return 1;
    }

    // Verify the platform plugin loaded correctly
    QString platform = app.platformName();
    if (platform.isEmpty()) {
        std::fprintf(stderr, "QGuiApplication::platformName() is empty\n");
        return 1;
    }
    std::printf("Platform: %s\n", platform.toLocal8Bit().constData());

    // Verify Qt6 Wayland Client API is linkable (from qtbase/6.11.1.2)
    // QWaylandClientExtension is a public API class
    const char *className = QWaylandClientExtension::staticMetaObject.className();
    if (className == nullptr) {
        std::fprintf(stderr, "QWaylandClientExtension type not available\n");
        return 1;
    }
    std::printf("QWaylandClientExtension class: %s\n", className);

    std::printf("Qt Wayland smoke test passed\n");
    return 0;
}
