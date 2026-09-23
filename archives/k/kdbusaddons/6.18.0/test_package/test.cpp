#include <KDBusService>

#include <QByteArray>
#include <QCoreApplication>
#include <QDBusConnection>

#include <iostream>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("kdbusaddons-smoke"));
    app.setOrganizationDomain(QStringLiteral("example.test"));

    const auto options = KDBusService::Multiple | KDBusService::NoExitOnFailure;
    KDBusService service(options);

    if (QByteArray(KDBusService::staticMetaObject.className()) != "KDBusService") {
        std::cerr << "FAIL: unexpected KDBusService meta-object" << std::endl;
        return 1;
    }

    std::cout << "PASS: KDBusAddons meta-object = "
              << KDBusService::staticMetaObject.className() << std::endl;
    std::cout << "PASS: KDBusAddons session bus connected = "
              << (QDBusConnection::sessionBus().isConnected() ? 1 : 0)
              << std::endl;
    std::cout << "PASS: KDBusAddons service registered = "
              << (service.isRegistered() ? 1 : 0) << std::endl;
    return 0;
}
