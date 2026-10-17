// Conan test_package for kidletime 6.26.0.
// Real API usage (R34): links against libKF6IdleTime, instantiates the
// KIdleTime singleton, probes the poller backend and queries idle time.
#include <QCoreApplication>
#include <KIdleTime>
#include <kidletime_version.h>

#include <cstdio>
#include <cstdlib>

int main(int argc, char *argv[])
{
    QCoreApplication app(argc, argv);

    // Real API usage: obtain the KIdleTime singleton.
    KIdleTime *idleTime = KIdleTime::instance();
    if (!idleTime) {
        std::fprintf(stderr, "FAIL: KIdleTime::instance() returned nullptr\n");
        return 1;
    }

    // Explicit poller backend probe (R40): when no system poller plugin is
    // loaded, KIdleTime::addIdleTimeout() returns 0 (see kidletime.cpp:
    // "if (Q_UNLIKELY(!d->poller)) return 0;"). A positive id proves a
    // backend is present and functional.
    const int probeId = idleTime->addIdleTimeout(60000); // 60s, never fires
    const bool hasPoller = (probeId != 0);
    if (hasPoller) {
        idleTime->removeIdleTimeout(probeId);
    } else {
        std::fprintf(stderr,
                     "WARNING: no idle-time poller backend available on OHOS "
                     "(KIdleTime::addIdleTimeout() returned 0). The X11/Wayland "
                     "poller plugins are not shipped; idleTime() always reports 0. "
                     "R40: adaptation completeness requires manual confirmation - "
                     "this PASS covers link/API availability only.\n");
    }

    // Query idle time. Without a poller idleTime() is 0; the value is
    // informational only and MUST NOT be used as the pass criterion (R40).
    const int idleMsec = idleTime->idleTime();
    std::printf("KIdleTime %s: instance OK, poller-backend=%s, idleTime()=%d msec\n",
                KIDLETIME_VERSION_STRING, hasPoller ? "present" : "ABSENT", idleMsec);

    // Verify the installed version header reports the packaged version.
    if (KIDLETIME_VERSION_MAJOR != 6 || KIDLETIME_VERSION_MINOR != 26
        || KIDLETIME_VERSION_PATCH != 0) {
        std::fprintf(stderr, "FAIL: unexpected KIDLETIME_VERSION %d.%d.%d\n",
                     KIDLETIME_VERSION_MAJOR, KIDLETIME_VERSION_MINOR,
                     KIDLETIME_VERSION_PATCH);
        return 1;
    }

    std::printf("kidletime test_package: PASS\n");
    return 0;
}
