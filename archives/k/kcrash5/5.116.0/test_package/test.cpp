#include <iostream>

#include <kcrash.h>

#include <QString>

// Consumer-side verification of the packaged libKF5Crash (R34/R51): the test
// drives the real KCrash public API and asserts observable behaviour instead
// of merely printing.  Nothing here crashes on purpose — the crash handling
// itself is covered by the upstream autotests (see reports/test-report.md).
static void saveHandler(int)
{
}

static void customHandler(int)
{
}

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // setFlags(AutoRestart) installs the default handler unless the process
    // was itself auto-restarted; clear it so the assertion below is
    // deterministic (see notes.md knowledge entry 4).
    qunsetenv("KCRASH_AUTO_RESTARTED");

    // 1. DrKonqi is not shipped on HarmonyOS PC: the switch must really flip
    //    (isDrKonqiEnabled() reads the same state the crash handler consults).
    KCrash::setDrKonqiEnabled(false);
    if (KCrash::isDrKonqiEnabled()) {
        std::cerr << "FAIL: KCrash::setDrKonqiEnabled(false) not observed" << std::endl;
        return 1;
    }

    // 2. AutoRestart must install the default crash handler — this is the
    //    entry point of the exec auto-restart chain.
    KCrash::setFlags(KCrash::AutoRestart | KCrash::SaferDialog);
    if (KCrash::crashHandler() == nullptr) {
        std::cerr << "FAIL: setFlags(AutoRestart) did not install a crash handler"
                  << std::endl;
        return 1;
    }

    // 3. Emergency-save callback round trip.
    KCrash::setEmergencySaveFunction(saveHandler);
    if (KCrash::emergencySaveFunction() != saveHandler) {
        std::cerr << "FAIL: emergency save function not stored" << std::endl;
        return 1;
    }
    KCrash::setEmergencySaveFunction(nullptr);
    if (KCrash::emergencySaveFunction() != nullptr) {
        std::cerr << "FAIL: emergency save function not cleared" << std::endl;
        return 1;
    }

    // 4. A custom handler wins over the default one.
    KCrash::setCrashHandler(customHandler);
    if (KCrash::crashHandler() != customHandler) {
        std::cerr << "FAIL: setCrashHandler/custom crashHandler mismatch" << std::endl;
        return 1;
    }

    // 5. Bug-report metadata API (void, exercised for link/run coverage).
    KCrash::setErrorMessage(QStringLiteral("kcrash5 5.116.0 test_package"));

    std::cout << "OK: KCrash public API exercised "
              << "(DrKonqi switch, AutoRestart handler install, emergency-save "
              << "callback, custom handler, error metadata)"
              << std::endl;
    return 0;
}
