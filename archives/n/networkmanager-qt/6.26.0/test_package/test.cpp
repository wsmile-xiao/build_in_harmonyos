// networkmanager-qt 6.26.0 consumer test (R34: exercises the real library API).
//
// Uses exactly the public classes the downstream openKylin kylin-nm-base chain
// consumes: NetworkManager::ConnectionSettings, NetworkManager::WirelessSetting
// and (header only) NetworkManager::SecretAgent.
//
// Only value objects / serialisation are exercised, so no running
// NetworkManager daemon or D-Bus connection is required.
#include <NetworkManagerQt/ConnectionSettings>
#include <NetworkManagerQt/Manager>
#include <NetworkManagerQt/SecretAgent>
#include <NetworkManagerQt/WirelessSetting>

#include <QByteArray>
#include <QString>
#include <QVariantMap>

#include <cstdio>

int main()
{
    using namespace NetworkManager;

    // 1. Standalone WirelessSetting round-trip through the NM key map.
    //    Setting::toMap()/fromMap() operate on a single-setting QVariantMap.
    WirelessSetting::Ptr wireless(new WirelessSetting);
    wireless->setInitialized(true);
    wireless->setSsid(QByteArrayLiteral("nmq-ssid"));
    wireless->setMode(WirelessSetting::Infrastructure);
    const QVariantMap wirelessMap = wireless->toMap();
    if (!wirelessMap.contains(QStringLiteral("ssid"))) {
        std::printf("FAIL: WirelessSetting::toMap() lost the ssid\n");
        return 1;
    }
    WirelessSetting::Ptr wirelessCopy(new WirelessSetting);
    wirelessCopy->fromMap(wirelessMap);
    if (wirelessCopy->ssid() != QByteArrayLiteral("nmq-ssid")) {
        std::printf("FAIL: WirelessSetting round-trip mismatch\n");
        return 1;
    }

    // 2. A full wireless ConnectionSettings, as a NetworkManager client builds it.
    ConnectionSettings::Ptr settings(new ConnectionSettings(ConnectionSettings::Wireless));
    settings->setId(QStringLiteral("nmq-consumer-test"));
    settings->setUuid(QStringLiteral("11111111-2222-3333-4444-555555555555"));
    WirelessSetting::Ptr wifi = settings->setting(Setting::Wireless).dynamicCast<WirelessSetting>();
    if (!wifi) {
        std::printf("FAIL: ConnectionSettings(Wireless) has no WirelessSetting\n");
        return 1;
    }
    wifi->setInitialized(true);
    wifi->setSsid(QByteArrayLiteral("nmq-ssid"));

    const NMVariantMapMap map = settings->toMap();
    if (!map.contains(QStringLiteral("connection")) || !map.contains(QStringLiteral("802-11-wireless"))) {
        std::printf("FAIL: ConnectionSettings::toMap() is missing connection/802-11-wireless\n");
        return 1;
    }

    // 3. Reload from the serialised map and verify the values survived.
    ConnectionSettings::Ptr reloaded(new ConnectionSettings(map));
    if (reloaded->id() != QStringLiteral("nmq-consumer-test")) {
        std::printf("FAIL: ConnectionSettings round-trip lost the id\n");
        return 1;
    }
    WirelessSetting::Ptr reloadedWifi = reloaded->setting(Setting::Wireless).dynamicCast<WirelessSetting>();
    if (!reloadedWifi || reloadedWifi->ssid() != QByteArrayLiteral("nmq-ssid")) {
        std::printf("FAIL: ConnectionSettings round-trip lost the wireless ssid\n");
        return 1;
    }

    // 4. libnm-backed static helpers exposed by the binding.
    if (ConnectionSettings::typeFromString(QStringLiteral("802-11-wireless")) != ConnectionSettings::Wireless) {
        std::printf("FAIL: ConnectionSettings::typeFromString mismatch\n");
        return 1;
    }

    std::printf("PASS: KF6NetworkManagerQt ConnectionSettings/WirelessSetting round-trip OK\n");
    return 0;
}
