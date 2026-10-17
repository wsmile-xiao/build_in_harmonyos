#include <qt6keychain/keychain.h>

#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QEventLoop>
#include <QSettings>
#include <QStandardPaths>

static int waitForJob(QKeychain::Job &job)
{
    QEventLoop loop;
    QObject::connect(&job, &QKeychain::Job::finished, &loop, &QEventLoop::quit);
    job.start();
    loop.exec();
    if (job.error() != QKeychain::NoError) {
        qCritical() << "QKeychain job failed" << job.error() << job.errorString();
        return 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    qputenv("XDG_CURRENT_DESKTOP", "KDE");
    qputenv("KDE_SESSION_VERSION", "6");
    qunsetenv("DBUS_SESSION_BUS_ADDRESS");

    const QString root = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
        + QLatin1String("/qtkeychain-conan-test");
    QDir().mkpath(root);
    QSettings settings(root + QLatin1String("/secrets.ini"), QSettings::IniFormat);

    QKeychain::WritePasswordJob write(QStringLiteral("qtkeychain-conan-test"));
    write.setAutoDelete(false);
    write.setInsecureFallback(true);
    write.setSettings(&settings);
    write.setKey(QStringLiteral("smtp-password"));
    write.setTextData(QStringLiteral("open-harmony-secret"));
    if (waitForJob(write) != 0) {
        return 1;
    }

    QKeychain::ReadPasswordJob read(QStringLiteral("qtkeychain-conan-test"));
    read.setAutoDelete(false);
    read.setInsecureFallback(true);
    read.setSettings(&settings);
    read.setKey(QStringLiteral("smtp-password"));
    if (waitForJob(read) != 0) {
        return 1;
    }
    if (read.textData() != QLatin1StringView("open-harmony-secret")) {
        qCritical() << "Unexpected QKeychain value" << read.textData();
        return 1;
    }

    QKeychain::DeletePasswordJob remove(QStringLiteral("qtkeychain-conan-test"));
    remove.setAutoDelete(false);
    remove.setInsecureFallback(true);
    remove.setSettings(&settings);
    remove.setKey(QStringLiteral("smtp-password"));
    if (waitForJob(remove) != 0) {
        return 1;
    }

    qDebug().noquote() << "PASS: Qt6Keychain fallback store/read/delete";
    return 0;
}
