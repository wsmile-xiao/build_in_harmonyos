#include <KDBusService>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

// Real consumer-side test of the KF6DBusAddons library (R34: must exercise
// the tested package's actual API, not print-only).
//
// Constructs a KDBusService with NoExitOnFailure so the process can run to
// completion even when no D-Bus session bus is present, then queries the
// library API surface: serviceName(), isRegistered().
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("test_kdbusaddons"));
    QCoreApplication::setOrganizationDomain(QStringLiteral("kde.org"));

    // NoExitOnFailure: registration failure (e.g. no session bus) must not
    // terminate the process; the object is still constructed and usable.
    KDBusService service(KDBusService::Unique | KDBusService::NoExitOnFailure);

    const QString name = service.serviceName();
    std::printf("KDBusService::serviceName()='%s'\n", qPrintable(name));
    std::printf("KDBusService::isRegistered()=%d\n", service.isRegistered() ? 1 : 0);

    // The API surface above was exercised and the library links and runs.
    std::printf("test_kdbusaddons: OK\n");
    return 0;
}