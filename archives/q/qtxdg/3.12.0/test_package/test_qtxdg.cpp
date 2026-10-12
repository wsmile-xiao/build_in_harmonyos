/*
 * test_package/test_qtxdg.cpp
 *
 * Consumer-side verification of the qtxdg (libqtxdg) package.  It genuinely
 * depends on the tested package (R34): it compiles against the installed
 * Qt5Xdg public headers and links the installed Qt5Xdg / Qt5XdgIconLoader
 * archives, then exercises the real API.
 *
 * Exit code 0 = every check passed, 1 = at least one check failed.
 */
#include <XdgDesktopFile>
#include <XdgDirs>

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QTemporaryDir>

#include <QDebug>

static int g_failures = 0;

static void check(bool condition, const char *what)
{
    if (condition) {
        qInfo("ok   : %s", what);
    } else {
        qCritical("FAIL : %s", what);
        ++g_failures;
    }
}

static bool writeDesktopFile(const QString &path)
{
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        return false;
    }
    QTextStream out(&file);
    out << "[Desktop Entry]\n"
           "Type=Application\n"
           "Name=Conan Qt5Xdg Test\n"
           "Exec=/bin/true\n"
           "MimeType=text/plain;\n";
    return true;
}

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // --- XdgDirs API -----------------------------------------------------
    check(!XdgDirs::dataHome(false).isEmpty(), "XdgDirs::dataHome() returns a path");
    check(!XdgDirs::configHome(false).isEmpty(), "XdgDirs::configHome() returns a path");
    check(!XdgDirs::dataDirs().isEmpty(), "XdgDirs::dataDirs() returns at least one entry");
    check(!XdgDirs::configDirs().isEmpty(), "XdgDirs::configDirs() returns at least one entry");

    // --- XdgDesktopFile API ---------------------------------------------
    QTemporaryDir tmp;
    check(tmp.isValid(), "temporary directory is available");
    if (!tmp.isValid()) {
        qCritical("no writable temporary directory (TMPDIR) available");
        return 1;
    }

    // XdgDesktopFile::id() only resolves ids for files below an
    // "applications" directory of an XDG data dir, so point XDG_DATA_HOME at
    // the temporary tree and place the file there.
    qputenv("XDG_DATA_HOME", tmp.path().toLocal8Bit());
    const QString appsDir = tmp.filePath(QStringLiteral("applications"));
    QDir().mkpath(appsDir);
    const QString desktopPath = appsDir + QStringLiteral("/qtxdg-conan-test.desktop");
    check(writeDesktopFile(desktopPath), "wrote a test .desktop file");

    XdgDesktopFile desktop;
    check(desktop.load(desktopPath), "XdgDesktopFile::load()");
    check(desktop.isValid(), "XdgDesktopFile::isValid()");
    check(desktop.type() == XdgDesktopFile::ApplicationType, "XdgDesktopFile::type()");
    check(desktop.name() == QStringLiteral("Conan Qt5Xdg Test"),
          "XdgDesktopFile::name() reads the Name entry");
    check(desktop.value(QStringLiteral("Exec")).toString() == QStringLiteral("/bin/true"),
          "XdgDesktopFile::value(\"Exec\")");
    check(desktop.mimeTypes().contains(QStringLiteral("text/plain")),
          "XdgDesktopFile::mimeTypes()");
    check(XdgDesktopFile::id(desktopPath, true) == QStringLiteral("qtxdg-conan-test.desktop"),
          "XdgDesktopFile::id()");

    // Constructor + value accessors: (Type, Name, Exec).
    XdgDesktopFile manualEntry(XdgDesktopFile::ApplicationType,
                               QStringLiteral("Manual Entry"), QStringLiteral("/bin/echo"));
    check(manualEntry.value(QStringLiteral("Name")).toString() == QStringLiteral("Manual Entry"),
          "XdgDesktopFile constructor sets Name");
    check(manualEntry.value(QStringLiteral("Exec")).toString() == QStringLiteral("/bin/echo"),
          "XdgDesktopFile constructor sets Exec");

    if (g_failures != 0) {
        qCritical("%d check(s) failed", g_failures);
        return 1;
    }
    qInfo("all Qt5Xdg API checks passed");
    return 0;
}
