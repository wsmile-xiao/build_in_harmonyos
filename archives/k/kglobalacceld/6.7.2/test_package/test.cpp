/*
 * test_package for kglobalacceld 6.7.2 — OHOS consumer test.
 *
 * SPDX-License-Identifier: LGPL-2.0-or-later
 *
 * OHOS-specific assertions (real API usage, non-zero exit on failure):
 *  1. The exported KGlobalAccelD CMake package resolves and the daemon
 *     library links (K::KGlobalAccelD + Qt6::DBus).
 *  2. On OHOS the session bus is the TCP+ANONYMOUS shim started by the
 *     test_package driver (no AF_UNIX session bus exists on the device):
 *     KGlobalAccelD::init() must succeed over that bus, i.e. the daemon
 *     registers its /kglobalaccel object and owns org.kde.kglobalaccel.
 *  3. Without any platform grabber plugin (WITH_X11=OFF, no plugin dir) the
 *     daemon must still come up gracefully — registration, config loading
 *     and the D-Bus service are the surviving duties on OHOS.
 *  4. Tear-down must unregister cleanly (second init cycle on a fresh
 *     instance succeeds again).
 */
#include "kglobalacceld.h"

#include <QCoreApplication>
#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QDebug>
#include <QTimer>

static int failures = 0;

#define CHECK(cond)                                                         \
    do {                                                                    \
        if (cond) {                                                         \
            qInfo("PASS: %s", #cond);                                       \
        } else {                                                            \
            qWarning("FAIL: %s", #cond);                                    \
            ++failures;                                                     \
        }                                                                   \
    } while (false)

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QCoreApplication::setApplicationName(QStringLiteral("test_ohos_daemon"));
    QCoreApplication::setOrganizationName(QStringLiteral("kde"));

    // The driver injects the OHOS session bus address (TCP+ANONYMOUS shim).
    CHECK(qEnvironmentVariableIsSet("DBUS_SESSION_BUS_ADDRESS"));

    // No platform grabber plugin exists on OHOS (WITH_X11=OFF); the daemon
    // must select "no interface" gracefully rather than fail.
    qputenv("KGLOBALACCELD_PLATFORM", "ohos-offscreen-consumer");

    {
        KGlobalAccelD daemon;
        CHECK(daemon.init());

        const QDBusConnection bus = QDBusConnection::sessionBus();
        CHECK(bus.isConnected());
        const bool owned =
            bus.interface()->isServiceRegistered(QStringLiteral("org.kde.kglobalaccel"));
        CHECK(owned);

        const bool objectExposed = bus.objectRegisteredAt(QStringLiteral("/kglobalaccel")) != nullptr;
        CHECK(objectExposed);
    } // destructor must unregister the service cleanly

    {
        // Second init cycle proves clean tear-down (no leaked registration).
        KGlobalAccelD second;
        CHECK(second.init());
        CHECK(QDBusConnection::sessionBus().interface()->isServiceRegistered(
            QStringLiteral("org.kde.kglobalaccel")));
    }

    if (failures != 0) {
        qWarning("%d check(s) failed", failures);
        return 1;
    }
    qInfo("test_ohos_daemon: all checks passed");
    return 0;
}
