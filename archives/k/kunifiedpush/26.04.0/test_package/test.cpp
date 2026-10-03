// kunifiedpush 26.04.0 consumer test (R34: exercises real API).
//
// Instantiates a real KUnifiedPush::Connector with an empty service name:
// that constructor path stops right after ConnectorPrivate::init() (D-Bus
// adaptor registration on the session bus, which degrades to a warning on
// bus-less hosts), so the library APIs are exercised without requiring a
// running session dbus-daemon (ConnectorUtils::selectDistributor() would
// dereference a null QDBusConnectionInterface on a bus-less host).
//
// Verified APIs: construction, initial state (Unregistered), empty endpoint,
// VAPID public-key setter/getter round-trip, vapidPublicKeyRequired toggle.
#include <KUnifiedPush/Connector>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    // Empty service name via a named variable: the constructor returns early
    // before the bus-dependent distributor discovery (and avoids the C++
    // most-vexing parse of "Connector connector(QString())").
    const QString serviceName;
    KUnifiedPush::Connector connector(serviceName);
    if (connector.state() != KUnifiedPush::Connector::Unregistered) {
        std::printf("FAIL: initial state is not Unregistered\n");
        return 1;
    }
    if (!connector.endpoint().isEmpty()) {
        std::printf("FAIL: unexpected endpoint\n");
        return 1;
    }
    if (connector.vapidPublicKeyRequired()) {
        std::printf("FAIL: vapidPublicKeyRequired should default to false\n");
        return 1;
    }
    connector.setVapidPublicKey(
        QStringLiteral("BNH1upJppSLEASpoPmGDaeafgJ6KjZjxbDA3LbHG5yE1cAiKQ5qm_K08nVgibtxqm245l0BlaaMsu4iBGzV1wEU"));
    if (!connector.vapidPublicKey().startsWith(QLatin1String("BNH1upJp"))) {
        std::printf("FAIL: vapidPublicKey round-trip\n");
        return 1;
    }
    connector.setVapidPublicKeyRequired(true);
    if (!connector.vapidPublicKeyRequired()) {
        std::printf("FAIL: vapidPublicKeyRequired toggle\n");
        return 1;
    }
    std::printf("PASS: KUnifiedPush Connector API smoke OK\n");
    return 0;
}
