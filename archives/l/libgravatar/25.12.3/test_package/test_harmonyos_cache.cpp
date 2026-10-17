// SPDX-License-Identifier: LGPL-2.0-or-later

#include <Gravatar/GravatarCache>

#include <QByteArray>
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QGuiApplication>
#include <QStandardPaths>
#include <QTemporaryFile>

#include <sys/utsname.h>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}
}

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    QGuiApplication app(argc, argv);

    struct utsname systemInfo {};
    if (uname(&systemInfo) != 0 || QByteArray(systemInfo.sysname) != QByteArrayLiteral("HarmonyOS")) {
        return fail("test must run on a HarmonyOS device");
    }

    if (!Gravatar::GravatarCache::self()) {
        return fail("GravatarCache singleton was not created");
    }

    const QString dataRoot = QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation);
    if (dataRoot.isEmpty()) {
        return fail("HarmonyOS returned no generic data directory");
    }

    const QString cachePath = QDir(dataRoot).filePath(QStringLiteral("gravatar"));
    if (!QFileInfo(cachePath).isDir()) {
        return fail("GravatarCache did not create its HarmonyOS data directory");
    }

    QTemporaryFile probe(QDir(cachePath).filePath(QStringLiteral("libgravatar-ohos-XXXXXX")));
    if (!probe.open()) {
        return fail("GravatarCache data directory is not writable on HarmonyOS");
    }

    const QByteArray payload = QByteArrayLiteral("libgravatar HarmonyOS cache probe\n");
    if (probe.write(payload) != payload.size() || !probe.flush() || !probe.seek(0) || probe.readAll() != payload) {
        return fail("HarmonyOS cache file did not survive a write and read");
    }

    probe.close();
    if (!probe.remove()) {
        return fail("HarmonyOS cache probe file could not be removed");
    }

    qInfo().noquote() << "PASS: HarmonyOS GravatarCache directory create/write/read/remove";
    return 0;
}
