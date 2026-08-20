// ki18n 6.26.0 consumer test (R34: exercises real API).
// Builds a localized string via KLocalizedString and verifies round-trip.
// Includes a negative case: a missing substitution argument must be
// rejected (the unresolved %1 placeholder must survive in the output).
#include <KLocalizedString>
#include <QString>
#include <cstdio>

int main() {
    // Positive: subs() fills the %1 placeholder correctly.
    const QString s = ki18n("hello %1").subs(QStringLiteral("world"))
                          .toString();
    if (s != QStringLiteral("hello world")) {
        std::printf("FAIL: ki18n output mismatch: %s\n",
                    s.toUtf8().constData());
        return 1;
    }
    std::printf("PASS: ki18n formatted string OK (\"%s\")\n",
                s.toUtf8().constData());

    // Negative: calling toString() without supplying the %1 argument is an
    // invalid use — ki18n must not silently substitute it. The unresolved
    // %1 placeholder must remain in the output (in debug builds ki18n
    // additionally appends an (I18N_ARGUMENT_MISSING) spoof marker, so we
    // assert only that the placeholder survives).
    const QString missing = ki18n("hello %1").toString();
    if (!missing.contains(QStringLiteral("%1"))) {
        std::printf("FAIL: ki18n silently accepted a missing argument\n");
        return 1;
    }
    std::printf("PASS: ki18n rejected missing argument\n");
    return 0;
}
