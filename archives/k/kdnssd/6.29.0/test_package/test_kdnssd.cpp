#include <KDNSSD/ServiceBrowser>
#include <QCoreApplication>
#include <QTimer>
#include <cstdio>

// Real consumer-side test of the KF6DNSSD library (R34: must exercise the
// tested package's actual API, not print-only).
//
// On OHOS the platform DNSSD backend is the "dummy" implementation, so
// ServiceBrowser::isAvailable() reports Unsupported and startBrowse() emits
// finished() immediately. The test verifies the real KDNSSD namespace APIs
// (isAvailable, getLocalHostName, ServiceBrowser construction and
// startBrowse()/finished() signal flow) rather than only linking the library.
int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Exercise the static platform-status API exported by libKF6DNSSD.
    KDNSSD::ServiceBrowser::State state = KDNSSD::ServiceBrowser::isAvailable();
    std::printf("KDNSSD::ServiceBrowser::isAvailable()=%d (0=Working,1=Stopped,2=Unsupported)\n",
                static_cast<int>(state));

    // Exercise getLocalHostName() (goes through the platform/backend path).
    const QString localHost = KDNSSD::ServiceBrowser::getLocalHostName();
    std::printf("KDNSSD::ServiceBrowser::getLocalHostName()='%s'\n",
                qPrintable(localHost));

    // Construct and start a real ServiceBrowser for a pseudo service type;
    // the dummy backend emits finished() immediately after startBrowse().
    KDNSSD::ServiceBrowser *browser = new KDNSSD::ServiceBrowser(QStringLiteral("_kdnssd-test._tcp"));
    bool finishedEmitted = false;
    QObject::connect(browser, &KDNSSD::ServiceBrowser::finished,
                     [&]() { finishedEmitted = true; });
    browser->startBrowse();

    QTimer timeout;
    timeout.setSingleShot(true);
    timeout.setInterval(5000);
    QObject::connect(&timeout, &QTimer::timeout, &app, &QCoreApplication::quit);
    timeout.start();
    QTimer::singleShot(0, [&]() { if (finishedEmitted) app.quit(); });

    QObject::connect(browser, &KDNSSD::ServiceBrowser::finished,
                     &app, &QCoreApplication::quit);
    app.exec();

    std::printf("ServiceBrowser finished signal emitted=%d\n", finishedEmitted ? 1 : 0);

    // The API surface above was exercised and the library links and runs.
    // Assert: isAvailable() returned a defined enum value, the browser
    // object was constructible, its startBrowse() path ran, AND the
    // finished() signal was actually emitted (so a broken signal flow
    // makes the test fail rather than silently passing).
    bool ok = ((state == KDNSSD::ServiceBrowser::Working
                || state == KDNSSD::ServiceBrowser::Stopped
                || state == KDNSSD::ServiceBrowser::Unsupported)
               && finishedEmitted);
    std::printf("test_kdnssd: %s\n", ok ? "OK" : "FAIL");
    delete browser;
    return ok ? 0 : 1;
}
