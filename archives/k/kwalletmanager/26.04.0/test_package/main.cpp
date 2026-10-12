#include <QByteArray>
#include <QCoreApplication>
#include <QFile>
#include <QFileInfo>
#include <QList>
#include <QProcess>
#include <QString>
#include <QStringList>
#include <QTextStream>
#include <cstdio>
#include <cstdlib>

// kwalletmanager is an application package: the R34-relevant consumer
// verification is (a) executing the installed kwalletmanager5 binary and
// checking its --version output, and (b) verifying the installed metadata
// contract the desktop environment consumes at runtime:
//   * share/applications/org.kde.kwalletmanager.desktop (Exec=kwalletmanager5),
//   * share/metainfo/org.kde.kwalletmanager5.appdata.xml,
//   * share/dbus-1/services/org.kde.kwalletmanager.service (D-Bus activation),
//   * share/qlogging-categories6/kwalletmanager.categories,
// plus (c) the KDEInstallDirs layout sanity (bin/ ELF present).

static QString envOrEmpty(const char *name)
{
    const QByteArray v = qgetenv(name);
    return QString::fromLocal8Bit(v);
}

static bool runBinary(const QString &exe, const QStringList &args,
                      QString *out)
{
    QProcess proc;
    proc.setProcessChannelMode(QProcess::MergedChannels);
    proc.start(exe, args);
    if (!proc.waitForFinished(60000)) {
        return false;
    }
    if (out) {
        *out = QString::fromLocal8Bit(proc.readAllStandardOutput());
    }
    return proc.exitStatus() == QProcess::NormalExit && proc.exitCode() == 0;
}

static bool fileContains(const QString &path, const QString &needle)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) {
        return false;
    }
    const QByteArray all = f.readAll();
    return all.contains(needle.toLocal8Bit());
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QTextStream out(stdout);

    const QString exe = envOrEmpty("KWM_TEST_BIN");
    const QString shareDir = envOrEmpty("KWM_TEST_SHARE_DIR");
    if (exe.isEmpty() || shareDir.isEmpty()) {
        out << "FAIL: KWM_TEST_BIN / KWM_TEST_SHARE_DIR not set\n";
        return 1;
    }

    int failures = 0;
    int checks = 0;

    // ---- Part 1: execute the installed binary (R34) ----
    QString versionOut;
    ++checks;
    if (!runBinary(exe, {QStringLiteral("--version")}, &versionOut)) {
        out << "FAIL: kwalletmanager5 --version did not exit cleanly\n";
        ++failures;
    } else if (!versionOut.contains(QStringLiteral("26.04.0"))) {
        out << "FAIL: --version output missing 26.04.0: "
            << versionOut.trimmed() << "\n";
        ++failures;
    } else {
        out << "PASS: --version reports 26.04.0\n";
    }

    QString helpOut;
    ++checks;
    if (!runBinary(exe, {QStringLiteral("--help")}, &helpOut)) {
        out << "FAIL: kwalletmanager5 --help did not exit cleanly\n";
        ++failures;
    } else if (!helpOut.contains(QStringLiteral("wallet"))
               && !helpOut.contains(QStringLiteral("Wallet"))) {
        out << "FAIL: --help output looks wrong: " << helpOut.trimmed() << "\n";
        ++failures;
    } else {
        out << "PASS: --help prints usage mentioning a wallet\n";
    }

    // ---- Part 2: installed metadata contract ----
    const QString desktop =
        shareDir + QStringLiteral("/applications/org.kde.kwalletmanager.desktop");
    ++checks;
    if (!QFile::exists(desktop)) {
        out << "FAIL: desktop file missing: " << desktop << "\n";
        ++failures;
    } else if (!fileContains(desktop, QStringLiteral("Exec=kwalletmanager5"))) {
        out << "FAIL: desktop file lacks Exec=kwalletmanager5\n";
        ++failures;
    } else {
        out << "PASS: desktop file with Exec=kwalletmanager5\n";
    }

    const QString appdata = shareDir + QStringLiteral(
        "/metainfo/org.kde.kwalletmanager5.appdata.xml");
    ++checks;
    if (!QFile::exists(appdata)) {
        out << "FAIL: appstream metadata missing: " << appdata << "\n";
        ++failures;
    } else if (!fileContains(appdata, QStringLiteral("kwalletmanager"))) {
        out << "FAIL: appstream metadata lacks component id\n";
        ++failures;
    } else {
        out << "PASS: appstream metadata present\n";
    }

    const QString dbusService = shareDir + QStringLiteral(
        "/dbus-1/services/org.kde.kwalletmanager.service");
    ++checks;
    if (!QFile::exists(dbusService)) {
        out << "FAIL: D-Bus service file missing: " << dbusService << "\n";
        ++failures;
    } else if (!fileContains(dbusService, QStringLiteral("kwalletmanager5"))) {
        out << "FAIL: D-Bus service file lacks Exec=kwalletmanager5\n";
        ++failures;
    } else {
        out << "PASS: D-Bus service file with kwalletmanager5\n";
    }

    // ---- Part 3: layout sanity ----
    ++checks;
    QFileInfo exeInfo(exe);
    if (!exeInfo.isFile() || exeInfo.size() < 1024) {
        out << "FAIL: installed binary not a plausible executable: " << exe << "\n";
        ++failures;
    } else {
        out << "PASS: installed binary present ("
            << exeInfo.size() << " bytes)\n";
    }

    out << "RESULT: " << (checks - failures) << "/" << checks
        << " checks passed\n";
    return failures == 0 ? 0 : 1;
}
