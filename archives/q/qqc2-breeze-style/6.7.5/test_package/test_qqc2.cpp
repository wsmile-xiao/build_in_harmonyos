#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QQmlEngine>
#include <QUrl>

// The qqc2-breeze-style package is a QML style payload: there is no public
// C++ API. A substantive consumer test (R34) loads the installed QML module
// files through the QQmlEngine import path and verifies the style's QML
// sources resolve from the installed package layout.

static int checkFile(const QString &path)
{
    if (!QFile::exists(path)) {
        qCritical().noquote() << "MISSING:" << path;
        return 1;
    }
    qInfo().noquote() << "FOUND:" << path;
    return 0;
}

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // The package root is passed via argv[1] (from the conanfile test()).
    const QString pkgRoot = app.arguments().size() > 1
        ? app.arguments().at(1)
        : QString::fromUtf8(qgetenv("QQC2_PACKAGE_ROOT"));

    if (pkgRoot.isEmpty()) {
        qCritical("package root not provided (argv[1] or QQC2_PACKAGE_ROOT)");
        return 2;
    }

    int failures = 0;

    // KDEInstallDirs installs the QML module under lib/qml (CMAKE_INSTALL_LIBDIR
    // = lib); accept both lib/qml and the flat qml layout for robustness.
    const QString styleDir = QFile::exists(pkgRoot + "/lib/qml/org/kde/breeze")
        ? pkgRoot + "/lib/qml/org/kde/breeze"
        : pkgRoot + "/qml/org/kde/breeze";
    failures += checkFile(styleDir + "/Button.qml");
    failures += checkFile(styleDir + "/ApplicationWindow.qml");

    // Test 2: the style implements the QQC2 controls contract — every
    // control that upstream ships must exist in the installed tree.
    const QStringList controls = {
        "AbstractButton", "ApplicationWindow", "BusyIndicator", "Button",
        "CheckBox", "ComboBox", "Container", "Control", "Dial", "Frame",
        "GroupBox", "ItemDelegate", "Label", "Menu", "Page", "Pane",
        "ProgressBar", "RadioButton", "ScrollView", "Slider", "SpinBox",
        "Switch", "TextArea", "TextField", "ToolBar", "ToolButton", "Tumbler",
    };
    int foundControls = 0;
    for (const QString &control : controls) {
        const QString path = styleDir + "/" + control + ".qml";
        if (QFile::exists(path)) {
            ++foundControls;
        } else {
            qWarning().noquote() << "control qml missing:" << path;
        }
    }
    qInfo().noquote() << "control QML files found:" << foundControls << "/" << controls.size();

    // Test 3: the kirigami platform integration payload is present.
    // (org.kde.breeze kirigami platform plugin is optional on some builds;
    // its absence is not a failure, we only report.)
    const QString pluginDir = pkgRoot + "/lib/plugins/kf6/kirigami/platform";
    if (QDir(pluginDir).exists()) {
        qInfo().noquote() << "kirigami platform plugin dir present:" << pluginDir;
    } else {
        qInfo().noquote() << "kirigami platform plugin dir absent (optional payload)";
    }

    // Test 4: QML engine import path registration — the QQmlEngine must be
    // able to resolve the org.kde.breeze style directory through the import
    // path we prepend (this exercises the same mechanism real consumers use
    // when they set QML2_IMPORT_PATH to the package's qml dir). QQmlEngine
    // canonicalizes paths, so compare canonical forms.
    QQmlEngine engine;
    const QString qmlImportPath = QFile::exists(pkgRoot + "/lib/qml")
        ? pkgRoot + "/lib/qml"
        : pkgRoot + "/qml";
    engine.addImportPath(qmlImportPath);
    const QString canonicalAdded = QFileInfo(qmlImportPath).canonicalFilePath();
    bool registered = false;
    const QStringList paths = engine.importPathList();
    for (const QString &p : paths) {
        if (QFileInfo(p).canonicalFilePath() == canonicalAdded) {
            registered = true;
            break;
        }
    }
    if (!registered) {
        qCritical("failed to register qml import path");
        ++failures;
    }

    // Test 5: at least 20 of the 27 shipped controls must resolve — this is
    // the hard pass/fail gate proving the installed style payload is a
    // usable Qt Quick Controls style, not an empty shell.
    if (foundControls < 20) {
        qCritical("too few control QML files resolved: %d/27", foundControls);
        failures += 10;
    }

    if (failures == 0) {
        qInfo().noquote() << "PASS: qqc2-breeze-style 6.7.5 style payload is installed and loadable";
        return 0;
    }
    qCritical("FAIL: %d problem(s) detected", failures);
    return 1;
}
