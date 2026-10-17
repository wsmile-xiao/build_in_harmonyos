#include <KDBusService>
#include <QCoreApplication>
#include <QString>
#include <cstdio>

// HarmonyOS-specific test of the kdbusaddons platform adaptation path
// (R40/R34).
//
// OHOS has no X11 (the upstream Qt6Gui/Qt6GuiPrivate dependency is X11-only,
// so kdbusaddons is built with WITH_X11=OFF) and no D-Bus session daemon is
// running on the OHOS build host. This test asserts the exact observable
// behavior of that platform adaptation path rather than merely linking the
// library:
//
//   1. KDBusService construction with NoExitOnFailure must not terminate
//      the process when no session bus is available (graceful degradation;
//      without NoExitOnFailure upstream would exit(1)).
//   2. isRegistered() must report false when no session bus is connected.
//   3. serviceName() stays empty when no session bus is connected: upstream
//      Registration::generateServiceName() is only reached after the
//      isConnected() check, so without a bus no service name is generated.
//
// Each assertion calls into real KF6DBusAddons API surface; the test returns
// a non-zero exit code on any mismatch, so it is a real gate on the OHOS
// adaptation behavior.
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("test_kdbusaddons_ohos"));
    QCoreApplication::setOrganizationDomain(QStringLiteral("kde.org"));

    bool ok = true;

    // 1+2) NoExitOnFailure + no session bus: object constructs, no exit,
    //      and registration reports false.
    KDBusService service(KDBusService::Unique | KDBusService::NoExitOnFailure);
    const bool registered = service.isRegistered();
    std::printf("[ohos] isRegistered()=%d (expect 0 without session bus)\n",
                registered ? 1 : 0);
    if (registered) {
        std::printf("[ohos] FAIL: expected not registered without session bus\n");
        ok = false;
    }

    // 3) Without a session bus, generateServiceName() is not reached, so the
    //    service name is empty (exact OHOS-platform observable behavior).
    const QString name = service.serviceName();
    std::printf("[ohos] serviceName()='%s' (expect empty without session bus)\n",
                qPrintable(name));
    if (!name.isEmpty()) {
        std::printf("[ohos] FAIL: expected empty service name without session bus, got '%s'\n",
                    qPrintable(name));
        ok = false;
    }

    std::printf("test_kdbusaddons_ohos: %s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}