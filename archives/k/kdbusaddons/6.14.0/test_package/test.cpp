/*
 * test_package smoke test for kdbusaddons 6.14.0 (KF6DBusAddons).
 *
 * Exercises the KDEDModule API without needing a running D-Bus session bus:
 *  - construct a KDEDModule, set and read back its module name
 *  - exercise the static KDEDModule::moduleForMessage() path parser
 */
#include <QCoreApplication>
#include <QDBusMessage>
#include <QString>

#include <KDEDModule>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);
    app.setApplicationName("test_kdbusaddons");

    // 1. Construct a KDEDModule and set/read back its module name.
    KDEDModule module;
    module.setModuleName(QStringLiteral("testmodule"));
    if (module.moduleName() != QStringLiteral("testmodule")) {
        return 1;
    }

    // 2. moduleForMessage() parses the /modules/<name>/... D-Bus object path.
    QDBusMessage call = QDBusMessage::createMethodCall(
        QStringLiteral("org.kde.test"), QStringLiteral("/modules/foo"),
        QStringLiteral("org.kde.test"), QStringLiteral("bar"));
    if (KDEDModule::moduleForMessage(call) != QStringLiteral("foo")) {
        return 2;
    }

    // A non-method-call message (signal) yields an empty module name.
    QDBusMessage signal = QDBusMessage::createSignal(
        QStringLiteral("/modules/foo"), QStringLiteral("org.kde.Test"),
        QStringLiteral("signal"));
    if (!KDEDModule::moduleForMessage(signal).isEmpty()) {
        return 3;
    }

    return 0;
}
