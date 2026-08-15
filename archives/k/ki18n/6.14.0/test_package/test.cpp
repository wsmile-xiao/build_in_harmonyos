// ki18n 6.14.0 consumer test (R34: exercises real API).
// Builds a localized string via KLocalizedString and verifies round-trip.
#include <KLocalizedString>
#include <QString>
#include <cstdio>

int main() {
    const QString s = ki18n("hello %1").subs(QStringLiteral("world"))
                          .toString();
    if (s != QStringLiteral("hello world")) {
        std::printf("FAIL: ki18n output mismatch: %s\n",
                    s.toUtf8().constData());
        return 1;
    }
    std::printf("PASS: ki18n formatted string OK (\"%s\")\n",
                s.toUtf8().constData());
    return 0;
}
