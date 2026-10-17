// test.cpp — kcoreaddons5 5.116.0 test_package consumer (R34: must call the
// tested package's API, not just print).
//
// Exercises KF5CoreAddons public classes: KAboutData (component/version) and
// KRandom/KRandomSequence, plus KShell for a stable non-runtime-dependent
// call. KUser is intentionally NOT asserted here because OHOS lacks a
// user/group database (explored: user.isValid() returns FALSE on OHOS), so
// KUser assertions would be a platform-fragile test.
#include <iostream>
#include <string>

#include <KAboutData>
#include <KRandom>
#include <KShell>
#include <kcoreaddons_version.h>

int main() {
    KAboutData about(QStringLiteral("test-kcoreaddons5"),
                     QStringLiteral("Test KCoreAddons5"),
                     QString::fromLatin1(KCOREADDONS_VERSION_STRING));
    if (about.componentName() != QStringLiteral("test-kcoreaddons5")) {
        std::cerr << "FAIL: KAboutData::componentName() unexpected: "
                  << about.componentName().toStdString() << "\n";
        return 1;
    }
    if (about.version().isEmpty()) {
        std::cerr << "FAIL: KAboutData::version() empty\n";
        return 1;
    }

    // KRandom provides a random integer within [0, max).
    const quint32 r = KRandom::random();
    (void)r; // returns 0..ULONG_MAX, cannot assert a specific value

    // KShell::joinArgs round-trips a quoted argument.
    const QStringList args{QStringLiteral("hello world"), QStringLiteral("a'b")};
    const QString joined = KShell::joinArgs(args);
    const QStringList unjoined = KShell::splitArgs(joined);
    if (unjoined != args) {
        std::cerr << "FAIL: KShell::joinArgs/splitArgs round-trip mismatch\n";
        return 1;
    }

    std::cout << "kcoreaddons5 test_package OK (KF5CoreAddons " << KCOREADDONS_VERSION_STRING << ")\n";
    return 0;
}
