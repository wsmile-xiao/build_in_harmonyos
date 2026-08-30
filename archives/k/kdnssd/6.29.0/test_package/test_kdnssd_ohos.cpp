#include <KDNSSD/ServiceBrowser>
#include <KDNSSD/RemoteService>
#include <QCoreApplication>
#include <QList>
#include <QString>
#include <cstdio>

// HarmonyOS-specific test of the kdnssd platform adaptation path (R40/R34).
//
// OHOS has no Avahi/D-Bus DNSSD daemon and no mDNS responder published, so
// kdnssd's build selects the "dummy" backend (see src/CMakeLists.txt else
// branch: dummy-servicebrowser.cpp / dummy-remoteservice.cpp / etc.). This
// test asserts the exact observable behavior of that platform adaptation
// path rather than merely linking the library:
//
//   1. ServiceBrowser::isAvailable() == Unsupported   (dummy backend)
//   2. ServiceBrowser::getLocalHostName() is empty     (no responder present)
//   3. startBrowse() emits finished() synchronously    (dummy emits immediately)
//   4. services() returns an empty list after browse   (nothing discovered)
//
// Each assertion calls into real KF6DNSSD API surface; the test returns a
// non-zero exit code on any mismatch, so it is a real gate on the OHOS
// adaptation behavior.
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    bool ok = true;

    // 1) Platform availability must report Unsupported on the dummy backend.
    KDNSSD::ServiceBrowser::State state = KDNSSD::ServiceBrowser::isAvailable();
    std::printf("[ohos] isAvailable()=%d (expect 2=Unsupported)\n",
                static_cast<int>(state));
    if (state != KDNSSD::ServiceBrowser::Unsupported) {
        std::printf("[ohos] FAIL: expected Unsupported, got %d\n",
                    static_cast<int>(state));
        ok = false;
    }

    // 2) Without an mDNS/responder, the local host name must be empty.
    const QString localHost = KDNSSD::ServiceBrowser::getLocalHostName();
    std::printf("[ohos] getLocalHostName()='%s' (expect empty)\n",
                qPrintable(localHost));
    if (!localHost.isEmpty()) {
        std::printf("[ohos] FAIL: expected empty host name, got '%s'\n",
                    qPrintable(localHost));
        ok = false;
    }

    // 3) Browse flow on the dummy backend: finished() fires synchronously.
    KDNSSD::ServiceBrowser *browser =
        new KDNSSD::ServiceBrowser(QStringLiteral("_kdnssd-ohos-test._tcp"));
    bool finishedEmitted = false;
    bool finishedSynchronous = false;
    QObject::connect(browser, &KDNSSD::ServiceBrowser::finished,
                     [&]() {
                         finishedEmitted = true;
                         finishedSynchronous = true;
                     });
    browser->startBrowse();
    std::printf("[ohos] finished emitted=%d (expect 1, synchronous)\n",
                finishedEmitted ? 1 : 0);
    if (!finishedEmitted || !finishedSynchronous) {
        std::printf("[ohos] FAIL: startBrowse() did not emit finished() synchronously\n");
        ok = false;
    }

    // 4) No services can be discovered on the dummy backend.
    QList<KDNSSD::RemoteService::Ptr> services = browser->services();
    std::printf("[ohos] services().size()=%lld (expect 0)\n",
                static_cast<long long>(services.size()));
    if (!services.isEmpty()) {
        std::printf("[ohos] FAIL: expected no services, got %lld\n",
                    static_cast<long long>(services.size()));
        ok = false;
    }

    delete browser;

    std::printf("test_kdnssd_ohos: %s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}