// OHOS adaptation test for MauiKit 4.0.2.
//
// meta:     the installed C++ API is usable (versionString, exported QML
//           singleton meta objects of the library).
// defaults: OHOS-specific behaviour introduced by the adaptation patches:
//           MauiMan preferences are patched out, so Handy keeps the in-class
//           defaults, and HarmonyOS must not match any of the upstream
//           Q_OS_ANDROID/Q_OS_LINUX/... platform guards (CMake
//           UNIX/ANDROID/APPLE are all false on HarmonyOS).
// qml:      the org.mauikit.controls QML plugin loads and a real control is
//           instantiated under the offscreen QPA (headless device run).
// qmltypes: the BaseWindow CSD decoration chain resolves (Maui.WindowShadow
//           and Maui.WindowControls, both from platform-gated CMake sources)
//           and the WindowShadow type instantiates offscreen.
#include <QGuiApplication>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQuickItem>
#include <QDebug>

// Upstream installs the headers flat under include/MauiKit4/Core and sets
// that directory as the target's INTERFACE include dir, so include by
// basename.
#include <moduleinfo.h>
#include <handy.h>

namespace
{
int fail(const QString &message)
{
    qCritical().noquote() << "FAIL:" << message;
    return 1;
}
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    const QString mode = argc > 1 ? QString::fromLocal8Bit(argv[1]) : QStringLiteral("all");
    bool runMeta = (mode == QStringLiteral("meta") || mode == QStringLiteral("all"));
    bool runDefaults = (mode == QStringLiteral("defaults") || mode == QStringLiteral("all"));
    bool runQml = (mode == QStringLiteral("qml") || mode == QStringLiteral("all"));
    bool runQmlTypes = (mode == QStringLiteral("qmltypes") || mode == QStringLiteral("all"));

    if (runMeta) {
        // 4.0.2 = upstream source version baked into moduleinfo; the recipe
        // version is 4.0.2.1 and must not leak into the built library.
        if (MauiKitCore::versionString() != QStringLiteral("4.0.2")) {
            return fail(QStringLiteral("MauiKitCore::versionString() returned %1")
                            .arg(MauiKitCore::versionString()));
        }

        const QMetaObject &handyMeta = Handy::staticMetaObject;
        if (handyMeta.indexOfProperty("formFactor") < 0
            || handyMeta.indexOfProperty("isTouch") < 0
            || handyMeta.indexOfProperty("isMobile") < 0
            || handyMeta.indexOfProperty("singleClick") < 0) {
            return fail(QStringLiteral("Handy meta object properties are not exported"));
        }
        if (handyMeta.indexOfEnumerator("FFactor") < 0) {
            return fail(QStringLiteral("Handy::FFactor enum is not exported"));
        }
        qInfo().noquote() << "PASS: meta objects and version string exported";
    }

    if (runDefaults) {
        auto *handy = Handy::instance();
        if (!handy) {
            return fail(QStringLiteral("Handy instance unavailable"));
        }
        // MauiMan patched out -> in-class defaults (run decision B).
        if (handy->formFactor() != Handy::FFactor::Desktop) {
            return fail(QStringLiteral("formFactor default is not Desktop (MauiMan fallback broken)"));
        }
        if (handy->isMobile()) {
            return fail(QStringLiteral("isMobile default is not false (MauiMan fallback broken)"));
        }
        if (handy->isTouch()) {
            return fail(QStringLiteral("isTouch default is not false (MauiMan fallback broken)"));
        }
        if (!handy->property("singleClick").toBool()) {
            return fail(QStringLiteral("singleClick default is not true (MauiMan fallback broken)"));
        }
        // HarmonyOS is none of the upstream desktop/mobile platforms. Note
        // that the OHOS clang toolchain defines __linux__, so Q_OS_LINUX
        // (and therefore Handy::isLinux(), delegated to FMH::isLinux()) is
        // legitimately true on HarmonyOS - assert exactly that.
        if (handy->isAndroid() || handy->isWindows() || handy->isMac() || handy->isIOS()) {
            return fail(QStringLiteral("HarmonyOS must not match the Android/iOS/Windows/Mac guards"));
        }
        if (!handy->isLinux()) {
            return fail(QStringLiteral("isLinux must be true: the OHOS toolchain defines __linux__"));
        }
        // The OHOS in-file platform backend keeps desktop input defaults and
        // a non-pure platform instance (no crash on the attached property).
        if (!handy->hasKeyboard() || !handy->hasMouse()) {
            return fail(QStringLiteral("desktop input defaults are not set"));
        }
        // The QT_QUICK_CONTROLS_MOBILE override must stay functional: this is
        // the only mobile-mode switch that survives the MauiMan removal.
        qputenv("QT_QUICK_CONTROLS_MOBILE", "1");
        auto *mobileHandy = new Handy(&app);
        if (!mobileHandy->isMobile()) {
            return fail(QStringLiteral("QT_QUICK_CONTROLS_MOBILE=1 did not enable mobile mode"));
        }
        delete mobileHandy;
        qInfo().noquote() << "PASS: OHOS patched defaults and platform guards";
    }

    if (runQml) {
        QQmlEngine engine;
        QObject::connect(&engine, &QQmlEngine::warnings, [](const QList<QQmlError> &warnings) {
            for (const QQmlError &warning : warnings) {
                qWarning().noquote() << warning.toString();
            }
        });
        QQmlComponent component(&engine);
        component.setData("import QtQuick\n"
                          "import org.mauikit.controls as Maui\n"
                          "Maui.FloatingButton {}\n",
                          QUrl(QStringLiteral("qrc:///test")));
        QObject *object = component.create();
        if (!object) {
            qWarning().noquote() << component.errorString();
            return fail(QStringLiteral("org.mauikit.controls QML instantiation failed"));
        }
        if (!qobject_cast<QQuickItem *>(object)) {
            delete object;
            return fail(QStringLiteral("instantiated object is not a QQuickItem"));
        }
        delete object;
        qInfo().noquote() << "PASS: org.mauikit.controls QML module loads and instantiates offscreen";
    }

    if (runQmlTypes) {
        // The BaseWindow CSD decoration chain: private/BaseWindow.qml loads
        // Maui.WindowShadow through a Loader sourceComponent and ToolBar /
        // TabBar load Maui.WindowControls the same way. Both types come from
        // platform-gated CMake sources (UNIX/LINUX are all false on
        // HarmonyOS), so a regression re-opens as a whole-unit QML compile
        // failure even for inactive Loaders.
        QQmlEngine engine;
        QQmlComponent declarations(&engine);
        declarations.setData("import QtQuick\n"
                             "import org.mauikit.controls as Maui\n"
                             "Item {\n"
                             "    Loader { active: false; sourceComponent: Maui.WindowShadow { view: null; radius: 4.0; strength: 7.8 } }\n"
                             "    Loader { active: false; sourceComponent: Maui.WindowControls {} }\n"
                             "}\n",
                             QUrl(QStringLiteral("qrc:///test-window-types")));
        QObject *declared = declarations.create();
        if (!declared) {
            qWarning().noquote() << declarations.errorString();
            return fail(QStringLiteral("Maui.WindowShadow / Maui.WindowControls do not resolve in the BaseWindow decoration chain"));
        }
        delete declared;

        // Instantiate the real private BaseWindow unit (the file whose Loader
        // references Maui.WindowShadow) offscreen.
        QQmlComponent baseWindow(&engine);
        baseWindow.setData("import QtQuick\n"
                           "import org.mauikit.controls as Maui\n"
                           "Maui.BaseWindow {}\n",
                           QUrl(QStringLiteral("qrc:///test-base-window")));
        QObject *window = baseWindow.create();
        if (!window) {
            qWarning().noquote() << baseWindow.errorString();
            return fail(QStringLiteral("Maui.BaseWindow instantiation failed"));
        }
        delete window;

        // Instantiate Maui.WindowShadow itself: the compiled implementation is
        // upstream's pure-Qt mobile one (BoxShadowRenderer painted tiles, no
        // windowing-system calls), so it must construct cleanly offscreen.
        QQmlComponent shadowComponent(&engine);
        shadowComponent.setData("import QtQuick\n"
                                "import org.mauikit.controls as Maui\n"
                                "Window {\n"
                                "    id: host\n"
                                "    Maui.WindowShadow { view: host; radius: 4.0; strength: 7.8 }\n"
                                "}\n",
                                QUrl(QStringLiteral("qrc:///test-window-shadow")));
        QObject *shadow = shadowComponent.create();
        if (!shadow) {
            qWarning().noquote() << shadowComponent.errorString();
            return fail(QStringLiteral("Maui.WindowShadow instantiation failed"));
        }
        delete shadow;
        qInfo().noquote() << "PASS: BaseWindow decoration types resolve and WindowShadow instantiates offscreen";
    }

    qInfo().noquote() << "PASS: mauikit OHOS test_package";
    return 0;
}
